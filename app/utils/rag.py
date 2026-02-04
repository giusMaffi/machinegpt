"""RAG Engine - Retrieval Augmented Generation"""
import os
import time
from anthropic import Anthropic
from pinecone import Pinecone
from app.utils.embeddings import generate_query_embedding

def get_anthropic_client():
    """Get Anthropic client"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise Exception("ANTHROPIC_API_KEY not found")
    return Anthropic(api_key=api_key)

def get_pinecone_index():
    """Get Pinecone index"""
    api_key = os.environ.get('PINECONE_API_KEY')
    index_name = os.environ.get('PINECONE_INDEX_NAME', 'machinegpt')
    if not api_key:
        raise Exception("PINECONE_API_KEY not found")
    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name)

class RAGEngine:
    def query(self, question, producer_id, machine_id=None):
        """Execute RAG query"""
        start_time = time.time()
        
        try:
            # 1. Generate query embedding
            query_embedding = generate_query_embedding(question)
            if not query_embedding:
                raise Exception("Failed to generate embedding")
            
            retrieval_start = time.time()
            
            # 2. Search Pinecone
            index = get_pinecone_index()
            namespace = f"producer_{producer_id}"
            filter_dict = {"producer_id": producer_id}
            if machine_id:
                filter_dict["model_id"] = machine_id
            
            results = index.query(
                vector=query_embedding,
                namespace=namespace,
                filter=filter_dict,
                top_k=5,
                include_metadata=True
            )
            
            retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
            
            # 3. Build context from results
            context_chunks = []
            for match in results.matches:
                if match.score > 0.5:  # Lower threshold for testing
                    context_chunks.append({
                        'text': match.metadata.get('text', ''),
                        'doc_name': match.metadata.get('doc_name', 'Unknown'),
                        'page': match.metadata.get('page', 0),
                        'doc_id': match.metadata.get('doc_id', 0),
                        'score': match.score
                    })
            
            if not context_chunks:
                return {
                    'answer': "I don't have information about that in the documentation. Please contact technical support.",
                    'sources': [],
                    'response_time_ms': int((time.time() - start_time) * 1000),
                    'retrieval_time_ms': retrieval_time_ms,
                    'generation_time_ms': 0,
                    'tokens_input': 0,
                    'tokens_output': 0
                }
            
            # 4. Build system prompt
            system_prompt = "You are a technical support assistant for industrial machinery.\n\n"
            system_prompt += "Answer ONLY using the provided documentation below.\n"
            system_prompt += "Always cite the source (document name and page number).\n"
            system_prompt += "If the answer is not in the docs, say so clearly.\n\n"
            system_prompt += "DOCUMENTATION:\n\n"
            
            for i, chunk in enumerate(context_chunks):
                system_prompt += f"[DOCUMENT {i+1}]\n"
                system_prompt += f"Source: {chunk['doc_name']}, Page {chunk['page']}\n"
                system_prompt += f"Text: {chunk['text']}\n\n"
            
            generation_start = time.time()
            
            # 5. Call Claude
            client = get_anthropic_client()
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": question}]
            )
            
            generation_time_ms = int((time.time() - generation_start) * 1000)
            
            answer = message.content[0].text
            
            # 6. Extract sources mentioned in answer
            sources = []
            for chunk in context_chunks:
                sources.append({
                    'doc_id': chunk['doc_id'],
                    'page': chunk['page'],
                    'similarity_score': round(chunk['score'], 2),
                    'source_reference': f"Page {chunk['page']}"
                })
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'answer': answer,
                'sources': sources[:3],
                'response_time_ms': response_time_ms,
                'retrieval_time_ms': retrieval_time_ms,
                'generation_time_ms': generation_time_ms,
                'tokens_input': message.usage.input_tokens,
                'tokens_output': message.usage.output_tokens
            }
            
        except Exception as e:
            return {
                'answer': f"Error generating response: {str(e)}",
                'sources': [],
                'response_time_ms': int((time.time() - start_time) * 1000),
                'retrieval_time_ms': 0,
                'generation_time_ms': 0,
                'tokens_input': None,
                'tokens_output': None
            }
