"""Chat Routes"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.query import Query
from app.utils.auth import token_required, machine_access_required
from app.rag.engine import RAGEngine

bp = Blueprint('chat', __name__)

@bp.route('/query', methods=['POST'])
@token_required
@machine_access_required
def query():
    """Query AI"""
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    # Execute RAG
    rag = RAGEngine()
    result = rag.query(
        question=question,
        producer_id=g.producer_id,
        machine_id=g.current_machine_id
    )
    
    # Save query to DB
    query_record = Query(
        producer_id=g.producer_id,
        user_id=g.current_user_id,
        machine_instance_id=g.current_machine_id,
        question=question,
        answer=result.get('answer'),
        sources=result.get('sources'),
        response_time_ms=result.get('response_time_ms'),
        tokens_input=result.get('tokens_input'),
        tokens_output=result.get('tokens_output')
    )
    db.session.add(query_record)
    db.session.commit()
    
    return jsonify(result), 200