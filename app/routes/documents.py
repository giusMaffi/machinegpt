"""
Document Management Routes
Handles document upload, processing status, and retrieval
"""

from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
import os
from app import db
from app.models.document import Document
from app.utils.auth import token_required
from app.utils.document_processor import process_pdf_document

bp = Blueprint('documents', __name__, url_prefix='/api/documents')

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
@token_required
def upload_document():
    """Upload and process a document"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PDF, DOCX, TXT'}), 400
    
    # Get parameters
    producer_id = g.producer_id
    model_id = request.form.get('model_id', type=int)
    doc_type = request.form.get('doc_type', 'manual')
    language = request.form.get('language', 'en')
    title = request.form.get('title')
    
    if not model_id:
        return jsonify({'error': 'model_id required'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    upload_dir = f'data/raw/producer_{producer_id}'
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    try:
        # Process document
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
            'title': doc.title,
            'status': doc.processing_status,
            'total_chunks': doc.total_chunks
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:document_id>', methods=['GET'])
@token_required
def get_document(document_id):
    """Get document details"""
    
    doc = Document.query.filter_by(
        id=document_id,
        producer_id=g.producer_id
    ).first()
    
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    
    return jsonify({
        'id': doc.id,
        'title': doc.title,
        'doc_type': doc.doc_type,
        'language': doc.language,
        'total_pages': doc.total_pages,
        'total_chunks': doc.total_chunks,
        'processing_status': doc.processing_status,
        'created_at': doc.created_at.isoformat() if doc.created_at else None
    })


@bp.route('', methods=['GET'])
@token_required
def list_documents():
    """List all documents for producer"""
    
    docs = Document.query.filter_by(
        producer_id=g.producer_id
    ).order_by(Document.created_at.desc()).all()
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'title': doc.title,
            'doc_type': doc.doc_type,
            'total_chunks': doc.total_chunks,
            'status': doc.processing_status,
            'created_at': doc.created_at.isoformat() if doc.created_at else None
        } for doc in docs]
    })
