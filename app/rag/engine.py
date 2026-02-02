"""RAG Engine"""
import time
import os
from app.rag.embeddings import generate_query_embedding
from app.rag.vector_db import search_similar

class RAGEngine:
    
    def query(self, question, producer_id, machine_id=None):
        """Execute RAG query"""
        start_time = time.time()
        
        # 1. Generate query embedding
        query_embedding = generate_query_embedding(question)
        if not query_embedding:
            return {'error': 'Failed to generate embedding'}
        
        retrieval_time = int((time.time() - start_time) * 1000)
        
        # 2. Search similar chunks
        chunks = search_similar(query_embedding, producer_id)
        
        if not chunks:
            return {
                'answer': 'No relevant information found.',
                'sources': [],
                'response_time_ms': int((time.time() - start_time) * 1000)
            }
        
        # 3. Generate response with Claude
        gen_start = time.time()
        answer = self._generate_response(question, chunks)
        generation_time = int((time.time() - gen_start) * 1000)
        
        total_time = int((time.time() - start_time) * 1000)
        
        return {
            'answer': answer['text'],
            'sources': self._format_sources(chunks),
            'response_time_ms': total_time,
            'retrieval_time_ms': retrieval_time,
            'generation_time_ms': generation_time,
            'tokens_input': answer.get('tokens_input'),
            'tokens_output': answer.get('tokens_output')
        }
    
    def _generate_response(self, question, chunks):
        """Generate response with Claude"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            
            # Build context
            context = "You are a technical support assistant. Answer ONLY using the provided documentation.\n\n"
            
            for i, chunk in enumerate(chunks[:3], 1):
                context += f"[DOCUMENT {i}]\n"
                context += f"Source: {chunk.get('source_reference', 'Unknown')}\n"
                context += f"Text: {chunk['text']}\n\n"
            
            # Call Claude
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.3,
                system=context,
                messages=[
                    {"role": "user", "content": question}
                ]
            )
            
            return {
                'text': message.content[0].text,
                'tokens_input': message.usage.input_tokens,
                'tokens_output': message.usage.output_tokens
            }
            
        except Exception as e:
            print(f"Claude error: {e}")
            return {'text': f'Error generating response: {str(e)}'}
    
    def _format_sources(self, chunks):
        """Format sources for response"""
        sources = []
        for chunk in chunks[:3]:
            sources.append({
                'doc_id': chunk.get('doc_id'),
                'page': chunk.get('page'),
                'source_reference': chunk.get('source_reference'),
                'similarity_score': round(chunk.get('score', 0), 2)
            })
        return sources
