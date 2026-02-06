"""RAG Engine - Retrieval Augmented Generation with Multimodal Support"""
import os
import time
import ast
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

def check_image_relevance(question, image_caption):
    """
    Check if image caption is relevant to question
    Simple keyword matching (fast, good enough for MVP)
    """
    question_words = set(question.lower().split())
    caption_words = set(image_caption.lower().split())
    
    # Remove common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were'}
    question_words -= stop_words
    caption_words -= stop_words
    
    # Count overlapping keywords
    overlap = len(question_words & caption_words)
    
    if overlap >= 2:
        return "high"
    elif overlap >= 1:
        return "medium"
    else:
        return "low"

class RAGEngine:
    def query(self, question, producer_id, machine_id=None):
        """Execute RAG query with multimodal support"""
        start_time = time.time()
        
        try:
            query_embedding = generate_query_embedding(question)
            if not query_embedding:
                raise Exception("Failed to generate embedding")
            
            retrieval_start = time.time()
            
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
            
            context_chunks = []
            all_images = []
            
            for match in results.matches:
                if match.score > 0.5:
                    chunk_data = {
                        'text': match.metadata.get('text', ''),
                        'doc_name': match.metadata.get('doc_name', 'Unknown'),
                        'page': match.metadata.get('page', 0),
                        'doc_id': match.metadata.get('doc_id', 0),
                        'score': match.score
                    }
                    context_chunks.append(chunk_data)
                    
                    # Extract images if present
                    if match.metadata.get('has_images'):
                        images_str = match.metadata.get('images', '[]')
                        try:
                            # Parse images metadata (stored as string)
                            images_list = ast.literal_eval(images_str)
                            if isinstance(images_list, list):
                                all_images.extend(images_list)
                        except:
                            pass
            
            if not context_chunks:
                return {
                    'answer': "I don't have information about that in the documentation.",
                    'sources': [],
                    'images': [],
                    'has_images': False,
                    'response_time_ms': int((time.time() - start_time) * 1000),
                    'retrieval_time_ms': retrieval_time_ms,
                    'generation_time_ms': 0,
                    'tokens_input': 0,
                    'tokens_output': 0
                }
            
            # Filter images by relevance
            relevant_images = []
            for img in all_images:
                relevance = check_image_relevance(question, img.get('caption', ''))
                
                # Only include high/medium relevance images
                if relevance in ['high', 'medium']:
                    relevant_images.append({
                        'url': img['url'],
                        'caption': img['caption'],
                        'relevance': relevance,
                        'filename': img.get('filename', '')
                    })
            
            # Deduplicate images by URL
            seen_urls = set()
            unique_images = []
            for img in relevant_images:
                if img['url'] not in seen_urls:
                    seen_urls.add(img['url'])
                    unique_images.append(img)
            
            # Build system prompt
            system_prompt = "You are a technical support assistant.\n\n"
            system_prompt += "Answer ONLY from documentation below.\n"
            system_prompt += "Always cite source and page.\n\n"
            system_prompt += "DOCUMENTATION:\n\n"
            
            for i, chunk in enumerate(context_chunks):
                system_prompt += f"[DOC {i+1}]\n"
                system_prompt += f"Source: {chunk['doc_name']}, Page {chunk['page']}\n"
                system_prompt += f"{chunk['text']}\n\n"
            
            generation_start = time.time()
            
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
            
            sources = []
            for chunk in context_chunks:
                sources.append({
                    'doc_id': chunk['doc_id'],
                    'page': chunk['page'],
                    'similarity_score': round(chunk['score'], 2),
                    'source_reference': f"Page {chunk['page']}"
                })
            
            return {
                'answer': answer,
                'sources': sources[:3],
                'images': unique_images[:3],  # Max 3 images
                'has_images': len(unique_images) > 0,
                'response_time_ms': int((time.time() - start_time) * 1000),
                'retrieval_time_ms': retrieval_time_ms,
                'generation_time_ms': generation_time_ms,
                'tokens_input': message.usage.input_tokens,
                'tokens_output': message.usage.output_tokens
            }
            
        except Exception as e:
            return {
                'answer': f"Error: {str(e)}",
                'sources': [],
                'images': [],
                'has_images': False,
                'response_time_ms': int((time.time() - start_time) * 1000),
                'retrieval_time_ms': 0,
                'generation_time_ms': 0,
                'tokens_input': None,
                'tokens_output': None
            }
