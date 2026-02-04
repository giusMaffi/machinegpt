"""Embeddings generation using Voyage AI"""
import os
import voyageai

def get_client():
    """Get Voyage AI client with API key from environment"""
    api_key = os.environ.get('VOYAGE_API_KEY')
    if not api_key:
        raise Exception("VOYAGE_API_KEY not found in environment")
    return voyageai.Client(api_key=api_key)

def generate_embeddings(texts, input_type="document"):
    """
    Generate embeddings for a list of texts
    
    Args:
        texts: List of strings to embed
        input_type: "document" for docs, "query" for queries
    
    Returns:
        List of embedding vectors (1024-dimensional)
    """
    if not texts:
        return []
    
    try:
        client = get_client()
        response = client.embed(
            texts=texts,
            model="voyage-3",
            input_type=input_type
        )
        return response.embeddings
    except Exception as e:
        raise Exception(f"Embedding generation failed: {str(e)}")

def generate_query_embedding(text):
    """Generate embedding for a single query"""
    embeddings = generate_embeddings([text], input_type="query")
    return embeddings[0] if embeddings else None
