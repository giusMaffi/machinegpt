"""Embeddings generation using Voyage AI"""
import os
import voyageai

# Initialize client with API key from environment
client = voyageai.Client(api_key=os.environ.get('VOYAGE_API_KEY'))

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
