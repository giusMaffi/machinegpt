"""Document processing - chunking and embedding"""
import time
from app.utils.embeddings import generate_embeddings
from app.utils.rag import get_pinecone_index
from app.models.document import DocumentChunk
from app import db

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
                'index': chunk_index,
                'text': chunk_text.strip(),
                'start': start,
                'end': end
            })
            chunk_index += 1
        
        start += (chunk_size - overlap)
    
    return chunks

def process_document(file_path, document_id, producer_id, doc_name):
    """Process document: chunk, embed, store"""
    start_time = time.time()
    
    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into pages (simple: every ========== PAGE N ==========)
    pages = content.split('================== PAGE')
    
    all_chunks = []
    for page_num, page_content in enumerate(pages):
        if not page_content.strip():
            continue
        
        # Extract page number from header if exists
        page_number = page_num + 1
        
        # Chunk this page
        chunks = chunk_text(page_content, chunk_size=800, overlap=150)
        
        for chunk in chunks:
            all_chunks.append({
                'text': chunk['text'],
                'page': page_number,
                'index': len(all_chunks)
            })
    
    if not all_chunks:
        raise Exception("No content to process")
    
    # Generate embeddings (batch)
    texts = [c['text'] for c in all_chunks]
    embeddings = generate_embeddings(texts, input_type="document")
    
    if len(embeddings) != len(all_chunks):
        raise Exception(f"Embedding count mismatch: {len(embeddings)} vs {len(all_chunks)}")
    
    # Prepare vectors for Pinecone
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
                'model_id': 1.0  # Default for now
            }
        })
        
        # Save chunk to DB
        db_chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=i,
            source_reference=f"Page {chunk['page']}",
            chunk_metadata={'page': chunk['page']},
            chunk_text=chunk['text'],
            vector_id=vector_id
        )
        db.session.add(db_chunk)
    
    # Upsert to Pinecone
    index = get_pinecone_index()
    namespace = f"producer_{producer_id}"
    
    # Batch upsert (100 at a time)
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch, namespace=namespace)
    
    db.session.commit()
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    return {
        'total_chunks': len(all_chunks),
        'processing_time_ms': processing_time_ms
    }
