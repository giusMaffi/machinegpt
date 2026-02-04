"""Document management routes"""
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from app import db
from app.models.document import Document
from app.utils.auth import token_required
from app.utils.document_processor import process_document
import os

bp = Blueprint('documents', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload', methods=['POST'])
@token_required
def upload_document():
    """Upload and process document"""
    
    # Check file
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Get metadata
    doc_name = request.form.get('doc_name', file.filename)
    model_id = request.form.get('model_id', 1)  # Default to model 1
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = f"/tmp/{filename}"
        file.save(temp_path)
        
        # Create document record
        document = Document(
            producer_id=g.producer_id,
            model_id=int(model_id),
            title=doc_name,
            original_filename=filename,
            doc_type='manual',
            processing_status='processing'
        )
        db.session.add(document)
        db.session.flush()
        
        # Process document (chunking + embeddings + pinecone)
        result = process_document(
            file_path=temp_path,
            document_id=document.id,
            producer_id=g.producer_id,
            doc_name=doc_name
        )
        
        # Update document
        document.processing_status = 'completed'
        document.total_chunks = result['total_chunks']
        db.session.commit()
        
        # Cleanup
        os.remove(temp_path)
        
        return jsonify({
            'document_id': document.id,
            'status': 'completed',
            'chunks_created': result['total_chunks'],
            'processing_time_ms': result['processing_time_ms']
        }), 201
        
    except Exception as e:
        if document:
            document.processing_status = 'failed'
            db.session.commit()
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500
