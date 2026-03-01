"""Authentication Routes"""
from flask import Blueprint, request, jsonify, render_template, session
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


@bp.route('/login', methods=['GET'])
def login_page():
    """Render login page"""
    return render_template('login.html')


@bp.route('/login', methods=['POST'])
def login():
    """Universal login - sets session and returns success"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Try ProducerAdmin first
    producer_admin = ProducerAdmin.query.filter_by(email=email).first()
    if producer_admin:
        if not verify_password(password, producer_admin.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not producer_admin.is_active:
            return jsonify({'error': 'Account inactive'}), 403
        
        producer_admin.last_login = datetime.utcnow()
        producer_admin.login_count += 1
        db.session.commit()
        
        access_token = generate_access_token(producer_admin, user_type='producer_admin')
        refresh_token = generate_refresh_token(producer_admin, user_type='producer_admin')
        
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session['user_type'] = 'producer_admin'
        session.permanent = True
        
        return jsonify({'success': True, 'redirect': '/chat'}), 200
    
    # Try EndCustomer User
    user = User.query.filter_by(email=email).first()
    if user:
        if not verify_password(password, user.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account inactive'}), 403
        
        user.last_login = datetime.utcnow()
        user.login_count += 1
        db.session.commit()
        
        access_token = generate_access_token(user, user_type='end_customer')
        refresh_token = generate_refresh_token(user, user_type='end_customer')
        
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session['user_type'] = 'end_customer'
        session.permanent = True
        
        return jsonify({'success': True, 'redirect': '/chat'}), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout and clear session"""
    session.clear()
    return jsonify({'success': True}), 200
