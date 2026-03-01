from app import create_app
from app.rag.engine import RAGEngine

app = create_app()
with app.app_context():
    rag = RAGEngine()
    result = rag.query(
        question="What is error E42?",
        producer_id=2,
        machine_id=2
    )
    
    print("=== RESULT ===")
    print(f"Answer: {result['answer']}")
    print(f"Sources: {result['sources']}")
    print(f"Response time: {result['response_time_ms']}ms")
