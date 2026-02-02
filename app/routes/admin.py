"""Admin Routes"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.document import Document, DocumentChunk
from app.utils.auth import token_required
from app.utils.storage import save_uploaded_file
from app.ingestion.processors import DocumentProcessor
from app.rag.embeddings import generate_embeddings
from app.rag.vector_db import upsert_chunks
import hashlib

bp = Blueprint('admin', __name__)

@bp.route('/documents/upload', methods=['POST'])
@token_required
def upload_document():
    """Upload and process document"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    title = request.form.get('title', file.filename)
    doc_type = request.form.get('doc_type', 'manual')
    
    # Save file
    file_path = save_uploaded_file(file, g.producer_id)
    
    # Calculate hash
    file.seek(0)
    file_hash = hashlib.sha256(file.read()).hexdigest()
    
    # Create document record
    doc = Document(
        producer_id=g.producer_id,
        title=title,
        doc_type=doc_type,
        file_type='pdf',
        mime_type=file.content_type,
        file_extension='.pdf',
        original_filename=file.filename,
        file_hash=file_hash,
        file_path=file_path,
        source_type='admin_upload',
        processing_status='processing'
    )
    db.session.add(doc)
    db.session.commit()
    
    # Process PDF
    try:
        processor = DocumentProcessor()
        chunks, total_pages = processor.process_pdf(file_path)
        
        doc.total_pages = total_pages
        
        # Generate embeddings
        texts = [chunk['text'] for chunk in chunks]
        embeddings = generate_embeddings(texts)
        
        if not embeddings:
            doc.processing_status = 'failed'
            doc.processing_error = 'Failed to generate embeddings'
            db.session.commit()
            return jsonify({'error': 'Embedding failed'}), 500
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        
        # Upsert to Pinecone
        upsert_chunks(chunks, doc.id, g.producer_id)
        
        # Save chunks to DB
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk['chunk_index'],
                chunk_text=chunk['text'],
                source_reference=chunk['source_reference'],
                chunk_metadata={'page': chunk['page']},
                vector_id=f"doc_{doc.id}_chunk_{chunk['chunk_index']}"
            )
            db.session.add(db_chunk)
        
        doc.total_chunks = len(chunks)
        doc.processing_status = 'completed'
        db.session.commit()
        
        return jsonify({
            'document_id': doc.id,
            'status': 'completed',
            'total_pages': total_pages,
            'total_chunks': len(chunks)
        }), 201
        
    except Exception as e:
        doc.processing_status = 'failed'
        doc.processing_error = str(e)
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@bp.route('/documents', methods=['GET'])
@token_required
def list_documents():
    """List documents"""
    docs = Document.query.filter_by(producer_id=g.producer_id).all()
    
    return jsonify({
        'documents': [doc.to_dict() for doc in docs]
    }), 200