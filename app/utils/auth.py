"""JWT Authentication Utils"""
import jwt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, jsonify, current_app
from app.models.query import RefreshToken


def generate_access_token(user, user_type='end_customer'):
    """Generate JWT access token"""
    from app import db
    from app.models.customer import User
    
    # Get authorized machines
    machine_ids = user.get_authorized_machine_ids() if hasattr(user, 'get_authorized_machine_ids') else []
    
    # Get producer_id
    if user_type == 'end_customer':
        producer_id = user.end_customer.producer_id
        end_customer_id = user.end_customer_id
    else:
        producer_id = user.producer_id
        end_customer_id = None
    
    payload = {
        'user_id': user.id,
        'email': user.email,
        'user_type': user_type,
        'producer_id': producer_id,
        'end_customer_id': end_customer_id,
        'role': user.role,
        'machine_ids': machine_ids,
        'language': getattr(user, 'language_preference', 'en'),
        'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }
    
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')


def generate_refresh_token(user, user_type='end_customer'):
    """Generate JWT refresh token"""
    from app import db
    
    payload = {
        'user_id': user.id,
        'user_type': user_type,
        'type': 'refresh',
        'exp': datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    }
    
    token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
    
    # Store hash in database
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    )
    db.session.add(refresh_token)
    db.session.commit()
    
    return token


def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Extract token from header
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid authorization header'}), 401
        
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Attach to request context
        g.current_user_id = payload['user_id']
        g.user_type = payload['user_type']
        g.producer_id = payload['producer_id']
        g.machine_ids = payload.get('machine_ids', [])
        g.role = payload['role']
        
        return f(*args, **kwargs)
    
    return decorated


def machine_access_required(f):
    """Decorator to verify machine access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        machine_id = request.json.get('machine_id') if request.json else None
        
        if not machine_id:
            return jsonify({'error': 'machine_id required'}), 400
        
        if machine_id not in g.machine_ids:
            return jsonify({'error': 'Access denied to this machine'}), 403
        
        g.current_machine_id = machine_id
        return f(*args, **kwargs)
    
    return decorated


def hash_password(password):
    """Hash password with bcrypt"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, password_hash):
    """Verify password"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))