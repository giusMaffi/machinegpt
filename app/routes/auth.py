"""Authentication Routes"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app import db
from app.models.customer import User, EndCustomer, UserMachineAccess
from app.models.machine import MachineInstance
from app.utils.auth import generate_access_token, generate_refresh_token, hash_password, verify_password

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Find user
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
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
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@bp.route('/activate', methods=['POST'])
def activate_machine():
    """Activate machine and create first user"""
    data = request.json
    
    activation_code = data.get('activation_code')
    company_name = data.get('company_name')
    user_data = data.get('user')
    
    if not all([activation_code, company_name, user_data]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Find machine
    machine = MachineInstance.query.filter_by(
        activation_code=activation_code,
        is_activated=False
    ).first()
    
    if not machine:
        return jsonify({'error': 'Invalid or already activated'}), 400
    
    # Create end customer
    end_customer = EndCustomer.query.filter_by(
        producer_id=machine.producer_id,
        company_name=company_name
    ).first()
    
    if not end_customer:
        end_customer = EndCustomer(
            producer_id=machine.producer_id,
            company_name=company_name,
            country_code=data.get('country_code', 'IT'),
            industry=data.get('industry')
        )
        db.session.add(end_customer)
        db.session.flush()
    
    # Create user
    user = User(
        end_customer_id=end_customer.id,
        email=user_data['email'],
        password_hash=hash_password(user_data['password']),
        full_name=user_data.get('full_name'),
        phone=user_data.get('phone'),
        role=user_data.get('role', 'operator'),
        language_preference=user_data.get('language', 'en')
    )
    db.session.add(user)
    db.session.flush()
    
    # Activate machine
    machine.end_customer_id = end_customer.id
    machine.is_activated = True
    machine.activated_at = datetime.utcnow()
    machine.activated_by = user.id
    machine.installation_site = data.get('installation_site')
    machine.status = 'active'
    
    # Grant access
    access = UserMachineAccess(
        user_id=user.id,
        machine_instance_id=machine.id
    )
    db.session.add(access)
    
    db.session.commit()
    
    # Auto-login
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)
    
    return jsonify({
        'message': 'Machine activated successfully',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 201


@bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token"""
    data = request.json
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 400
    
    # Verify token (implementation simplified)
    from app.utils.auth import verify_token
    payload = verify_token(refresh_token)
    
    if not payload:
        return jsonify({'error': 'Invalid refresh token'}), 401
    
    # Get user
    user = User.query.get(payload['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Generate new access token
    access_token = generate_access_token(user)
    
    return jsonify({'access_token': access_token}), 200