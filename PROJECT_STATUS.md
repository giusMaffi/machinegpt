# 🚦 MACHINEGPT - CURRENT STATUS

**Last Update:** 2026-02-14 19:45
**Session:** Chat UI + Document Upload Debug

---

## ✅ WHAT'S WORKING

### Backend (100%)
- ✅ Flask server running on http://127.0.0.1:5001
- ✅ PostgreSQL database with all tables
- ✅ Authentication (login/logout/refresh tokens)
- ✅ Multi-tenant isolation (RLS policies)

### Document Upload (100%)
- ✅ Upload endpoint `/api/admin/documents/upload`
- ✅ PDF processing with chunking
- ✅ Document ID 10 successfully uploaded (2 chunks, 2 pages)
- ✅ Chunks stored in `document_chunks` table

### Chat UI (100%)
- ✅ Login page working
- ✅ Chat interface rendering
- ✅ Machine selection working
- ✅ Message sending working
- ✅ User: paolo.bianchi@barilla.com / demo123

---

## ❌ WHAT'S BROKEN

### RAG Query (CRITICAL)
- ❌ Query returns "I don't have information" 
- ❌ NOT using Pinecone (we removed it!)
- ❌ Code still references Pinecone in:
  - `app/rag/vector_db.py`
  - `app/rag/engine.py`
  - `app/utils/document_processor.py`

**ROOT CAUSE:** We use **Voyage AI embeddings + PostgreSQL storage ONLY**
- No external vector DB
- Embeddings stored as JSON in `document_chunks.chunk_metadata` or separate column
- Need semantic search WITHIN PostgreSQL

---

## 🔧 WHAT NEEDS FIXING NOW

1. **Replace Pinecone with PostgreSQL vector search**
   - Use pgvector extension OR
   - Use simple cosine similarity in Python
   - Query directly from `document_chunks` table

2. **Fix RAG pipeline:**
```python
   # Current (WRONG):
   chunks = search_pinecone(...)  # ← Doesn't exist!
   
   # Should be:
   chunks = search_postgres(query_embedding, producer_id, model_id)
```

---

## 📊 DATABASE STATE
```sql
-- Documents uploaded
SELECT id, title, model_id, total_chunks FROM documents WHERE id=10;
-- Result: id=10, model_id=1, total_chunks=2

-- Machine info
SELECT id, model_id, serial_number FROM machine_instances WHERE id=2;
-- Result: id=2, model_id=1, serial='AMO-AMK-X500-2024-000001'

-- Chunks stored
SELECT COUNT(*) FROM document_chunks WHERE document_id=10;
-- Result: 2 chunks exist
```

---

## 🎯 NEXT IMMEDIATE ACTION

**Fix `app/rag/vector_db.py` to search PostgreSQL instead of Pinecone:**
```python
def search_similar(query_embedding, producer_id, model_id=None, top_k=5):
    """Search PostgreSQL document_chunks"""
    from app import db
    from app.models.document import DocumentChunk, Document
    
    # Get chunks for this producer + model
    query = db.session.query(DocumentChunk, Document).join(
        Document, DocumentChunk.document_id == Document.id
    ).filter(
        Document.producer_id == producer_id
    )
    
    if model_id:
        query = query.filter(Document.model_id == model_id)
    
    chunks = query.all()
    
    # Calculate cosine similarity in Python
    # Return top_k most similar
```

---

## 📝 ARCHITECTURE REMINDER

**Our RAG Stack:**
- Voyage AI for embeddings (NOT OpenAI)
- PostgreSQL for storage (NOT Pinecone)
- Claude Sonnet 4.5 for generation
- Flask for API

**NO EXTERNAL VECTOR DB!**

---

## 🚨 CRITICAL NOTES

- Chat UI uses vanilla JavaScript (NOT Alpine.js - CSP issues)
- Auth tokens expire after 15 min
- Document chunks have `chunk_index` that MUST increment (was buggy, now fixed)
- admin.py uses `process_pdf_document()` NOT old `DocumentProcessor()`

---

