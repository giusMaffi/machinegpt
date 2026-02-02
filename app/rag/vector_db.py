"""Pinecone Vector DB"""
from flask import current_app

def get_pinecone_index():
    """Get Pinecone index"""
    try:
        from pinecone import Pinecone
        
        pc = Pinecone(api_key=current_app.config['PINECONE_API_KEY'])
        index = pc.Index(current_app.config['PINECONE_INDEX_NAME'])
        
        return index
    except Exception as e:
        print(f"Pinecone error: {e}")
        return None


def upsert_chunks(chunks, document_id, producer_id):
    """Upsert chunks to Pinecone"""
    index = get_pinecone_index()
    if not index:
        return False
    
    namespace = f"producer_{producer_id}"
    vectors = []
    
    for chunk in chunks:
        vector_id = f"doc_{document_id}_chunk_{chunk['chunk_index']}"
        
        vectors.append({
            'id': vector_id,
            'values': chunk['embedding'],
            'metadata': {
                'text': chunk['text'],
                'doc_id': document_id,
                'page': chunk.get('page'),
                'source_reference': chunk.get('source_reference')
            }
        })
    
    index.upsert(vectors=vectors, namespace=namespace)
    return True


def search_similar(query_embedding, producer_id, top_k=5):
    """Search similar chunks"""
    index = get_pinecone_index()
    if not index:
        return []
    
    namespace = f"producer_{producer_id}"
    
    results = index.query(
        vector=query_embedding,
        namespace=namespace,
        top_k=top_k,
        include_metadata=True
    )
    
    chunks = []
    for match in results.matches:
        chunks.append({
            'text': match.metadata.get('text'),
            'doc_id': match.metadata.get('doc_id'),
            'page': match.metadata.get('page'),
            'source_reference': match.metadata.get('source_reference'),
            'score': match.score
        })
    
    return chunks