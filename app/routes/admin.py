"""Admin Routes"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.document import Document
from app.utils.auth import token_required
from app.utils.document_processor import process_pdf_document
import os

bp = Blueprint('admin', __name__)

@bp.route('/documents/upload', methods=['POST'])
@token_required
def upload_document():
    """Upload and process document"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    producer_id = g.producer_id
    model_id = request.form.get('model_id', type=int)
    title = request.form.get('title', file.filename)
    doc_type = request.form.get('doc_type', 'manual')
    language = request.form.get('language', 'en')
    
    if not model_id:
        return jsonify({'error': 'model_id required'}), 400
    
    # Save file
    upload_dir = f'data/raw/producer_{producer_id}'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)
    
    try:
        # Process using CORRECT function
        doc = process_pdf_document(
            file_path=file_path,
            producer_id=producer_id,
            model_id=model_id,
            doc_type=doc_type,
            language=language,
            title=title
        )
        
        db.session.commit()
        
        return jsonify({
            'document_id': doc.id,
            'status': 'completed',
            'total_pages': doc.total_pages,
            'total_chunks': doc.total_chunks
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/documents', methods=['GET'])
@token_required
def list_documents():
    """List documents"""
    docs = Document.query.filter_by(producer_id=g.producer_id).all()
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'title': doc.title,
            'doc_type': doc.doc_type,
            'total_chunks': doc.total_chunks,
            'status': doc.processing_status
        } for doc in docs]
    }), 200
