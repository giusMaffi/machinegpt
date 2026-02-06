"""Query AI endpoint with multimodal support"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.query import Query
from app.utils.auth import token_required
from app.utils.rag import RAGEngine

bp = Blueprint('query', __name__)

@bp.route('/', methods=['POST'])
@token_required
def query_ai():
    """Query the AI with a question"""
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': 'Question required'}), 400
        
        question = data['question']
        machine_id = data.get('machine_id')
        
        # SECURITY CHECK
        if machine_id:
            if not hasattr(g, 'machine_ids') or machine_id not in g.machine_ids:
                return jsonify({'error': 'Access denied to this machine'}), 403
        
        rag = RAGEngine()
        result = rag.query(
            question=question,
            producer_id=g.producer_id,
            machine_id=machine_id
        )
        
        query_record = Query(
            producer_id=g.producer_id,
            user_id=g.current_user_id,
            machine_instance_id=machine_id,
            question=question,
            answer=result['answer'],
            sources=result.get('sources', []),
            response_time_ms=result['response_time_ms'],
            tokens_input=result.get('tokens_input'),
            tokens_output=result.get('tokens_output')
        )
        db.session.add(query_record)
        db.session.commit()
        
        return jsonify({
            'query_id': query_record.id,
            'answer': result['answer'],
            'sources': result['sources'],
            'images': result.get('images', []),  # NEW: Images array
            'has_images': result.get('has_images', False),  # NEW: Boolean flag
            'metadata': {
                'response_time_ms': result['response_time_ms'],
                'retrieval_time_ms': result.get('retrieval_time_ms', 0),
                'generation_time_ms': result.get('generation_time_ms', 0),
                'tokens_input': result.get('tokens_input'),
                'tokens_output': result.get('tokens_output')
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/feedback', methods=['POST'])
@token_required
def submit_feedback():
    """Submit feedback for a query"""
    try:
        data = request.get_json()
        query_id = data.get('query_id')
        feedback = data.get('feedback')
        
        if not query_id or feedback not in [1, -1]:
            return jsonify({'error': 'Invalid input'}), 400
        
        query = Query.query.get(query_id)
        if not query:
            return jsonify({'error': 'Query not found'}), 404
        
        if query.user_id != g.current_user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        query.feedback = feedback
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
