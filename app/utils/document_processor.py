"""Document processing - chunking, embedding, and image extraction"""
import time
import os
import base64
from PyPDF2 import PdfReader
from anthropic import Anthropic
from app.utils.embeddings import generate_embeddings
from app.utils.rag import get_pinecone_index
from app.models.document import DocumentChunk
from app import db

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def extract_images_from_pdf(pdf_path, document_id):
    """Extract images from PDF and save locally"""
    images_data = []
    pdf = PdfReader(pdf_path)
    
    # Create directory for images
    images_dir = f"data/processed/images/doc_{document_id}"
    os.makedirs(images_dir, exist_ok=True)
    
    for page_num, page in enumerate(pdf.pages):
        if "/XObject" not in page["/Resources"]:
            continue
        
        xObject = page["/Resources"]["/XObject"].get_object()
        
        for obj_name in xObject:
            obj = xObject[obj_name]
            
            if obj["/Subtype"] == "/Image":
                try:
                    size = (obj["/Width"], obj["/Height"])
                    data = obj.get_data()
                    
                    img_filename = f"page_{page_num}_img_{len(images_data)}.jpg"
                    img_path = os.path.join(images_dir, img_filename)
                    
                    with open(img_path, "wb") as img_file:
                        img_file.write(data)
                    
                    description = describe_image_with_claude(img_path)
                    
                    images_data.append({
                        "page": page_num,
                        "path": img_path,
                        "filename": img_filename,
                        "url": f"/static/images/doc_{document_id}/{img_filename}",
                        "caption": description,
                        "size": size
                    })
                    
                    print(f"  📸 Extracted image from page {page_num}: {description[:50]}...")
                
                except Exception as e:
                    print(f"  ⚠️  Could not extract image: {e}")
                    continue
    
    return images_data

def describe_image_with_claude(image_path):
    """Use Claude Vision to describe technical diagram/photo"""
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": """Describe this technical diagram or photo in 1-2 concise sentences.
                        Focus on: what component is shown, what action/procedure, or what problem it illustrates.
                        Be precise and technical."""
                    }
                ]
            }]
        )
        
        return response.content[0].text.strip()
    
    except Exception as e:
        print(f"  ⚠️  Could not describe image: {e}")
        return "Technical diagram (description unavailable)"

def chunk_text(text, chunk_size=800, overlap=150):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    chunk_index = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        
        if chunk_text.strip():
            chunks.append({
                "index": chunk_index,
                "text": chunk_text.strip(),
                "start": start,
                "end": end
            })
            chunk_index += 1
        
        start += (chunk_size - overlap)
    
    return chunks

def process_pdf_document(file_path, document_id, producer_id, doc_name):
    """Process PDF: extract text, images, chunk, embed, store"""
    start_time = time.time()
    print(f"\n📄 Processing PDF: {doc_name}")
    
    # 1. Extract text
    print("  📖 Extracting text...")
    pdf = PdfReader(file_path)
    pages_text = []
    
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text.strip():
            pages_text.append({
                'page_number': page_num,
                'text': text
            })
    
    print(f"  ✅ Extracted {len(pages_text)} pages")
    
    # 2. Extract images
    print("  📸 Extracting images...")
    images_data = extract_images_from_pdf(file_path, document_id)
    print(f"  ✅ Extracted {len(images_data)} images")
    
    # 3. Create chunks with images
    print("  ✂️  Chunking text...")
    all_chunks = []
    
    for page_data in pages_text:
        page_num = page_data['page_number']
        page_text = page_data['text']
        
        page_images = [img for img in images_data if img['page'] == page_num]
        chunks = chunk_text(page_text, chunk_size=800, overlap=150)
        
        for chunk in chunks:
            all_chunks.append({
                'text': chunk['text'],
                'page': page_num,
                'index': len(all_chunks),
                'images': page_images
            })
    
    if not all_chunks:
        raise Exception("No content to process")
    
    print(f"  ✅ Created {len(all_chunks)} chunks")
    
    # 4. Generate embeddings
    print("  🧮 Generating embeddings...")
    texts = [c['text'] for c in all_chunks]
    embeddings = generate_embeddings(texts, input_type="document")
    
    if len(embeddings) != len(all_chunks):
        raise Exception(f"Embedding mismatch: {len(embeddings)} vs {len(all_chunks)}")
    
    print(f"  ✅ Generated {len(embeddings)} embeddings")
    
    # 5. Prepare vectors
    print("  📊 Preparing vectors...")
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
        vector_id = f"doc_{document_id}_chunk_{i}"
        
        images_metadata = []
        if chunk['images']:
            images_metadata = [{
                'url': img['url'],
                'caption': img['caption'],
                'filename': img['filename']
            } for img in chunk['images']]
        
        vectors.append({
            'id': vector_id,
            'values': embedding,
            'metadata': {
                'text': chunk['text'],
                'doc_id': float(document_id),
                'doc_name': doc_name,
                'page': float(chunk['page']),
                'producer_id': float(producer_id),
                'model_id': 1.0,
                'has_images': len(images_metadata) > 0,
                'images': str(images_metadata)
            }
        })
        
        db_chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=i,
            source_reference=f"Page {chunk['page']}",
            chunk_metadata={
                'page': chunk['page'],
                'images': images_metadata
            },
            chunk_text=chunk['text'],
            vector_id=vector_id
        )
        db.session.add(db_chunk)
    
    # 6. Upsert to Pinecone
    print("  🔍 Upserting to Pinecone...")
    index = get_pinecone_index()
    namespace = f"producer_{producer_id}"
    
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch, namespace=namespace)
        print(f"    ✅ Batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1}")
    
    db.session.commit()
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    print(f"  ✅ Complete in {processing_time_ms}ms")
    
    return {
        'total_chunks': len(all_chunks),
        'total_images': len(images_data),
        'processing_time_ms': processing_time_ms
    }

def process_document(file_path, document_id, producer_id, doc_name):
    """Legacy wrapper - detects PDF vs text"""
    if file_path.endswith('.pdf'):
        return process_pdf_document(file_path, document_id, producer_id, doc_name)
    
    # Original text processing (unchanged)
    start_time = time.time()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pages = content.split('================== PAGE')
    all_chunks = []
    
    for page_num, page_content in enumerate(pages):
        if not page_content.strip():
            continue
        
        page_number = page_num + 1
        chunks = chunk_text(page_content, chunk_size=800, overlap=150)
        
        for chunk in chunks:
            all_chunks.append({
                'text': chunk['text'],
                'page': page_number,
                'index': len(all_chunks),
                'images': []
            })
    
    if not all_chunks:
        raise Exception("No content")
    
    texts = [c['text'] for c in all_chunks]
    embeddings = generate_embeddings(texts, input_type="document")
    
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
        vector_id = f"doc_{document_id}_chunk_{i}"
        
        vectors.append({
            'id': vector_id,
            'values': embedding,
            'metadata': {
                'text': chunk['text'],
                'doc_id': float(document_id),
                'doc_name': doc_name,
                'page': float(chunk['page']),
                'producer_id': float(producer_id),
                'model_id': 1.0,
                'has_images': False
            }
        })
        
        db_chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=i,
            source_reference=f"Page {chunk['page']}",
            chunk_metadata={'page': chunk['page']},
            chunk_text=chunk['text'],
            vector_id=vector_id
        )
        db.session.add(db_chunk)
    
    index = get_pinecone_index()
    namespace = f"producer_{producer_id}"
    
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch, namespace=namespace)
    
    db.session.commit()
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    return {
        'total_chunks': len(all_chunks),
        'total_images': 0,
        'processing_time_ms': processing_time_ms
    }
