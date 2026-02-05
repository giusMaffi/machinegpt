"""Authentication Routes"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.customer import User
from app.models.producer import ProducerAdmin
from app.models.query import RefreshToken
from app.utils.auth import (
    generate_access_token, 
    generate_refresh_token,
    verify_password,
    verify_token
)
from datetime import datetime
import hashlib

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['POST'])
def login():
    """
    Universal login for both ProducerAdmin and EndCustomer Users
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Try ProducerAdmin first
    producer_admin = ProducerAdmin.query.filter_by(email=email).first()
    if producer_admin:
        # Verify password
        if not verify_password(password, producer_admin.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check active
        if not producer_admin.is_active:
            return jsonify({'error': 'Account inactive'}), 403
        
        # Update last login
        producer_admin.last_login = datetime.utcnow()
        producer_admin.login_count += 1
        db.session.commit()
        
        # Generate tokens
        access_token = generate_access_token(producer_admin, user_type='producer_admin')
        refresh_token = generate_refresh_token(producer_admin, user_type='producer_admin')
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': producer_admin.id,
                'email': producer_admin.email,
                'full_name': producer_admin.full_name,
                'role': producer_admin.role,
                'user_type': 'producer_admin',
                'is_active': producer_admin.is_active
            }
        }), 200
    
    # Try EndCustomer User
    user = User.query.filter_by(email=email).first()
    if user:
        # Verify password
        if not verify_password(password, user.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check active
        if not user.is_active:
            return jsonify({'error': 'Account inactive'}), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.login_count += 1
        db.session.commit()
        
        # Generate tokens
        access_token = generate_access_token(user, user_type='end_customer')
        refresh_token = generate_refresh_token(user, user_type='end_customer')
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'user_type': 'end_customer',
                'language_preference': user.language_preference,
                'is_active': user.is_active
            }
        }), 200
    
    # Not found
    return jsonify({'error': 'Invalid credentials'}), 401


@bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token"""
    data = request.json
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 400
    
    try:
        # Verify token
        payload = verify_token(refresh_token)
        
        # Check if revoked
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        token_record = RefreshToken.query.filter_by(
            token_hash=token_hash,
            revoked=False
        ).first()
        
        if not token_record:
            return jsonify({'error': 'Token invalid or revoked'}), 401
        
        # Get user
        user_type = payload.get('user_type')
        user_id = payload.get('user_id')
        
        if user_type == 'producer_admin':
            user = ProducerAdmin.query.get(user_id)
        else:
            user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate new access token
        new_access_token = generate_access_token(user, user_type=user_type)
        
        return jsonify({
            'access_token': new_access_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 401


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout and revoke refresh token"""
    data = request.json
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'success': True}), 200
    
    try:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        token_record = RefreshToken.query.filter_by(token_hash=token_hash).first()
        
        if token_record:
            token_record.revoked = True
            db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
