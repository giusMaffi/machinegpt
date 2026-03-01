"""Document Processing Utilities"""
import os
import hashlib
from datetime import datetime
from PyPDF2 import PdfReader
from app import db
from app.models.document import Document, DocumentChunk
from app.utils.embeddings import generate_embeddings

def process_pdf_document(file_path, producer_id, model_id, doc_type='manual', language='en', title=None):
    """Process PDF"""
    print(f"📄 Extracting {file_path}")
    reader = PdfReader(file_path)
    
    pages_text = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text.strip():
            pages_text.append({'page': page_num, 'text': text})
    
    with open(file_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    filename = os.path.basename(file_path)
    doc_title = title or filename
    
    doc = Document(
        producer_id=producer_id,
        model_id=model_id,
        title=doc_title,
        doc_type=doc_type,
        language=language,
        file_path=file_path,
        file_hash=file_hash,
        file_type='pdf',
        mime_type='application/pdf',
        file_extension='.pdf',
        original_filename=filename,
        source_type='manual_upload',
        total_pages=len(pages_text),
        processing_status='processing'
    )
    db.session.add(doc)
    db.session.flush()
    
    print(f"📝 Doc ID: {doc.id}")
    
    all_chunks = []
    global_chunk_index = 0
    
    for page_data in pages_text:
        page_chunks = chunk_content(page_data['text'], page_number=page_data['page'])
        for chunk in page_chunks:
            chunk['chunk_index'] = global_chunk_index
            global_chunk_index += 1
            all_chunks.append(chunk)
    
    print(f"✂️  {len(all_chunks)} chunks")
    
    # Save chunks to DB (no Pinecone!)
    for chunk in all_chunks:
        db_chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=chunk['chunk_index'],
            chunk_text=chunk['text'],
            source_reference=f"Page {chunk['page']}",
            chunk_metadata={'page': chunk['page']}
        )
        db.session.add(db_chunk)
    
    doc.total_chunks = len(all_chunks)
    doc.processing_status = 'completed'
    
    print(f"✅ Complete!")
    return doc

def chunk_content(text, chunk_size=800, overlap=150, page_number=None):
    """Split text"""
    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 < chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append({'text': current_chunk.strip(), 'page': page_number})
            if overlap > 0 and len(current_chunk) >= overlap:
                current_chunk = current_chunk[-overlap:] + para + "\n\n"
            else:
                current_chunk = para + "\n\n"
    
    if current_chunk.strip():
        chunks.append({'text': current_chunk.strip(), 'page': page_number})
    
    return chunks
