"""Embeddings with Voyage AI"""
import os
from flask import current_app

def generate_embeddings(texts):
    """Generate embeddings with Voyage AI"""
    try:
        import voyageai
        client = voyageai.Client(api_key=current_app.config['VOYAGE_API_KEY'])
        
        result = client.embed(
            texts=texts,
            model="voyage-2",
            input_type="document"
        )
        
        return result.embeddings
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def generate_query_embedding(text):
    """Generate query embedding"""
    try:
        import voyageai
        client = voyageai.Client(api_key=current_app.config['VOYAGE_API_KEY'])
        
        result = client.embed(
            texts=[text],
            model="voyage-2",
            input_type="query"
        )
        
        return result.embeddings[0]
    except Exception as e:
        print(f"Query embedding error: {e}")
        return None