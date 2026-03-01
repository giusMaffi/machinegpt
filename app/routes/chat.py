"""Chat routes"""
from flask import Blueprint, render_template, request, jsonify, g
from app.models.query import Query
from app.utils.auth import token_required

bp = Blueprint('chat', __name__)

@bp.route('/chat')
@token_required
def chat_interface():
    """Render chat interface"""
    return render_template('chat.html')

@bp.route('/api/chat/history')
@token_required
def chat_history():
    """Get chat history for a machine"""
    machine_id = request.args.get('machine_id', type=int)
    
    if not machine_id:
        return jsonify({'error': 'machine_id required'}), 400
    
    # Security check
    if not hasattr(g, 'machine_ids') or machine_id not in g.machine_ids:
        return jsonify({'error': 'Access denied'}), 403
    
    queries = Query.query.filter_by(
        machine_instance_id=machine_id
    ).order_by(Query.created_at.desc()).limit(50).all()
    
    history = []
    for q in queries:
        history.append({
            'id': q.id,
            'question': q.question,
            'answer': q.answer,
            'sources': q.sources or [],
            'feedback': q.feedback,
            'metadata': {
                'response_time_ms': q.response_time_ms or 0,
                'tokens_used': (q.tokens_input or 0) + (q.tokens_output or 0)
            },
            'created_at': q.created_at.isoformat()
        })
    
    return jsonify({'history': history})
