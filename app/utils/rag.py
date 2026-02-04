"""RAG Engine - Retrieval Augmented Generation"""
import os
import time
from anthropic import Anthropic
from pinecone import Pinecone
from app.utils.embeddings import generate_query_embedding

# Initialize clients
anthropic_client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
pinecone_client = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
index = pinecone_client.Index(os.environ.get('PINECONE_INDEX_NAME', 'machinegpt'))

class RAGEngine:
    def query(self, question, producer_id, machine_id=None):
        """
        Execute RAG query
        
        Args:
            question: User's question
            producer_id: Producer ID for namespace isolation
            machine_id: Optional machine filter
        
        Returns:
            dict with answer, sources, metadata
        """
        start_time = time.time()
        
        try:
            # 1. Generate query embedding
            query_embedding = generate_query_embedding(question)
            if not query_embedding:
                raise Exception("Failed to generate embedding")
            
            # 2. Search Pinecone
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
            
            # 3. Build context from results
            context_chunks = []
            for match in results.matches:
                if match.score > 0.7:  # Only high-quality matches
                    context_chunks.append({
                        'text': match.metadata.get('text', ''),
                        'doc_name': match.metadata.get('doc_name', 'Unknown'),
                        'page': match.metadata.get('page', 0),
                        'score': match.score
                    })
            
            if not context_chunks:
                return {
                    'answer': "I don't have information about that in the documentation. Please contact technical support.",
                    'sources': [],
                    'response_time_ms': int((time.time() - start_time) * 1000),
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
            
            # 5. Call Claude
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": question}]
            )
            
            answer = message.content[0].text
            
            # 6. Extract sources mentioned in answer
            sources = []
            for chunk in context_chunks:
                if chunk['doc_name'] in answer or str(chunk['page']) in answer:
                    sources.append({
                        'doc_name': chunk['doc_name'],
                        'page': chunk['page'],
                        'similarity_score': round(chunk['score'], 2)
                    })
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'answer': answer,
                'sources': sources[:3],  # Top 3 sources
                'response_time_ms': response_time_ms,
                'tokens_input': message.usage.input_tokens,
                'tokens_output': message.usage.output_tokens
            }
            
        except Exception as e:
            raise Exception(f"RAG query failed: {str(e)}")
