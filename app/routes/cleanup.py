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

@bp.route('/inspect-vectors', methods=['GET'])
def inspect_vectors():
    """Inspect what's actually in Pinecone"""
    try:
        from app.utils.embeddings import generate_query_embedding
        
        # Query with "error" embedding
        query_emb = generate_query_embedding("error code E-1 overheat")
        
        index = get_pinecone_index()
        results = index.query(
            vector=query_emb,
            namespace="producer_1",
            top_k=3,
            include_metadata=True
        )
        
        chunks_data = []
        for match in results.matches:
            chunks_data.append({
                'id': match.id,
                'score': match.score,
                'text_preview': match.metadata.get('text', '')[:200],
                'doc_id': match.metadata.get('doc_id'),
                'page': match.metadata.get('page')
            })
        
        return jsonify({
            'chunks': chunks_data,
            'count': len(chunks_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
