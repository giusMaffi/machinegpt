"""Document upload and management routes"""
import os
import hashlib
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from app import db
from app.models import Document
from app.utils.auth import token_required
from app.utils.document_processor import process_document

bp = Blueprint('documents', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_file_hash(file_path):
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

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
    model_id = request.form.get('model_id', 1)
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = f'/tmp/{filename}'
        file.save(temp_path)
        
        # Extract file info
        file_extension = os.path.splitext(filename)[1].lower()
        mime_type = file.content_type or 'application/octet-stream'
        file_size = os.path.getsize(temp_path)
        file_hash = calculate_file_hash(temp_path)
        
        # Determine file type
        file_type_map = {
            '.pdf': 'pdf',
            '.txt': 'text',
            '.doc': 'document',
            '.docx': 'document'
        }
        file_type = file_type_map.get(file_extension, 'unknown')
        
        # Create document record
        document = Document(
            producer_id=g.producer_id,
            model_id=int(model_id),
            title=doc_name,
            original_filename=filename,
            file_type=file_type,
            mime_type=mime_type,
            file_extension=file_extension,
            file_hash=file_hash,
            file_size_bytes=file_size,
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
            'message': 'Document uploaded and processed successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500
