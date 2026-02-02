"""Document Processors"""
from PyPDF2 import PdfReader
from app.utils.helpers import chunk_text

class DocumentProcessor:
    
    def process_pdf(self, file_path):
        """Process PDF to chunks"""
        reader = PdfReader(file_path)
        chunks = []
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            
            if text.strip():
                page_chunks = chunk_text(text)
                
                for idx, chunk in enumerate(page_chunks):
                    chunks.append({
                        'text': chunk['text'],
                        'page': page_num,
                        'chunk_index': idx,
                        'source_reference': f'Page {page_num}'
                    })
        
        return chunks, len(reader.pages)