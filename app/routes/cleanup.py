"""Cleanup endpoint for removing old data"""
from flask import Blueprint, jsonify
from app.utils.rag import get_pinecone_index

bp = Blueprint('cleanup', __name__)

@bp.route('/cleanup-dummy-docs', methods=['POST'])
def cleanup_dummy_docs():
    """Delete dummy document vectors from Pinecone"""
    try:
        index = get_pinecone_index()
        namespace = "producer_1"
        
        # Delete all with doc_id = 2
        index.delete(filter={"doc_id": 2.0}, namespace=namespace)
        
        return jsonify({
            'message': 'Dummy documents cleaned from Pinecone',
            'namespace': namespace
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
