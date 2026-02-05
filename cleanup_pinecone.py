"""Cleanup old dummy documents from Pinecone"""
import os
from pinecone import Pinecone

# Init Pinecone
pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
index = pc.Index(os.environ.get('PINECONE_INDEX_NAME', 'machinegpt'))

namespace = "producer_1"

# Delete vectors with doc_id = 2 (dummy document)
print(f"Deleting vectors from namespace: {namespace}")

# Query all vectors with doc_id = 2
results = index.query(
    vector=[0.0] * 1024,  # Dummy vector
    namespace=namespace,
    filter={"doc_id": 2.0},
    top_k=10000,
    include_metadata=False
)

vector_ids = [match.id for match in results.matches]
print(f"Found {len(vector_ids)} vectors to delete")

if vector_ids:
    index.delete(ids=vector_ids, namespace=namespace)
    print("✅ Deleted successfully!")
else:
    print("No vectors found to delete")
