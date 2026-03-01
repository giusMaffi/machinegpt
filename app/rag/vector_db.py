"""PostgreSQL-based vector search with cached embeddings"""
from app import db
from app.models.document import DocumentChunk, Document
from app.rag.embeddings import generate_query_embedding
import numpy as np
import json

def search_similar(query_embedding, producer_id, model_id=None, top_k=5):
    print(f"🔍 Searching: producer={producer_id}, model={model_id}")
    
    # Get all chunks for producer/model
    query = db.session.query(DocumentChunk, Document).join(
        Document, DocumentChunk.document_id == Document.id
    ).filter(Document.producer_id == producer_id)
    
    if model_id:
        query = query.filter(Document.model_id == model_id)
    
    all_chunks = query.all()
    print(f"📦 Found {len(all_chunks)} chunks in DB")
    
    if not all_chunks:
        print("⚠️  No chunks found!")
        return []
    
    # Use CACHED embeddings from DB
    print(f"🔮 Using cached embeddings...")
    
    scores = []
    for chunk, doc in all_chunks:
        if not chunk.embedding:
            print(f"⚠️  Chunk {chunk.id} missing embedding, skipping")
            continue
        
        # Parse stored embedding
        chunk_embedding = json.loads(chunk.embedding)
        
        # Calculate cosine similarity
        similarity = cosine_similarity(query_embedding, chunk_embedding)
        scores.append({
            'text': chunk.chunk_text,
            'doc_id': doc.id,
            'page': chunk.chunk_metadata.get('page') if chunk.chunk_metadata else None,
            'source_reference': chunk.source_reference,
            'score': similarity
        })
    
    # Sort by similarity
    scores.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"🎯 Returning top {min(top_k, len(scores))} results")
    for i, s in enumerate(scores[:top_k]):
        print(f"  {i+1}. Score: {s['score']:.3f}, Page: {s['page']}")
    
    return scores[:top_k]

def cosine_similarity(a, b):
    """Calculate cosine similarity"""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def upsert_chunks(*args, **kwargs):
    """Dummy for compatibility"""
    pass
