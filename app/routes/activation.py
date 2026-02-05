"""Machine activation and user registration"""
from flask import Blueprint, request, jsonify, render_template_string
from app import db
from app.models.machine import MachineInstance
from app.models.customer import EndCustomer, User, UserMachineAccess
from app.utils.auth import generate_access_token, generate_refresh_token
import bcrypt
from datetime import datetime

bp = Blueprint('activation', __name__)


@bp.route('/activate', methods=['GET'])
def show_activation_form():
    """
    Show activation form with machine details
    
    GET /activate?code=ABC123
    
    Returns HTML form or JSON with machine info
    """
    activation_code = request.args.get('code')
    
    if not activation_code:
        return jsonify({'error': 'Activation code required'}), 400
    
    # Find machine
    machine = MachineInstance.query.filter_by(
        activation_code=activation_code,
        is_activated=False
    ).first()
    
    if not machine:
        return jsonify({
            'error': 'Invalid or already activated code'
        }), 400
    
    # Return machine info (for now JSON, later HTML form)
    return jsonify({
        'machine': {
            'serial_number': machine.serial_number,
            'model_name': machine.model.model_name,
            'model_code': machine.model.model_code,
            'producer_name': machine.model.producer.company_name
        },
        'activation_code': activation_code,
        'instructions': 'POST to /activate with registration data'
    }), 200


@bp.route('/activate', methods=['POST'])
def activate_machine():
    """
    Activate machine and register user
    
    First-time activation: Creates EndCustomer + User + grants access
    
    Request:
    {
        "activation_code": "ABC123",
        "company_name": "Ferrero SpA",
        "country_code": "IT",
        "industry": "food",
        "installation_site": "Alba Plant",
        "user": {
            "full_name": "Mario Rossi",
            "email": "mario.rossi@ferrero.com",
            "password": "SecurePass123!",
            "phone": "+39 334 123 4567",
            "role": "operator",
            "language": "it"
        }
    }
    
    Response:
    {
        "success": true,
        "user_id": 1,
        "access_token": "...",
        "refresh_token": "...",
        "machine": {...}
    }
    """
    try:
        data = request.get_json()
        
        activation_code = data.get('activation_code')
        
        # Validate
        if not activation_code:
            return jsonify({'error': 'activation_code required'}), 400
        
        # Find machine (with lock to prevent race conditions)
        machine = MachineInstance.query.filter_by(
            activation_code=activation_code,
            is_activated=False
        ).with_for_update().first()
        
        if not machine:
            return jsonify({
                'error': 'Invalid activation code or already activated'
            }), 400
        
        # Get or create EndCustomer
        company_name = data.get('company_name')
        if not company_name:
            return jsonify({'error': 'company_name required'}), 400
        
        end_customer = EndCustomer.query.filter_by(
            producer_id=machine.producer_id,
            company_name=company_name
        ).first()
        
        if not end_customer:
            # Create new customer
            end_customer = EndCustomer(
                producer_id=machine.producer_id,
                company_name=company_name,
                country_code=data.get('country_code', 'IT'),
                industry=data.get('industry'),
                status='active',
                service_tier='premium'
            )
            db.session.add(end_customer)
            db.session.flush()
        
        # Create User
        user_data = data.get('user', {})
        
        email = user_data.get('email')
        password = user_data.get('password')
        full_name = user_data.get('full_name')
        
        if not email or not password or not full_name:
            return jsonify({
                'error': 'user.email, user.password, and user.full_name required'
            }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'error': 'Email already registered. Please login instead.'
            }), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Create user
        user = User(
            end_customer_id=end_customer.id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone=user_data.get('phone'),
            role=user_data.get('role', 'operator'),
            language_preference=user_data.get('language', 'en'),
            is_active=True,
            email_verified=True  # Auto-verify for activation flow
        )
        db.session.add(user)
        db.session.flush()
        
        # Link machine to customer
        machine.end_customer_id = end_customer.id
        machine.is_activated = True
        machine.activated_at = datetime.utcnow()
        machine.activated_by = user.id
        machine.installation_site = data.get('installation_site')
        machine.status = 'active'
        
        # Grant user access to this machine
        access = UserMachineAccess(
            user_id=user.id,
            machine_instance_id=machine.id,
            access_level='read',
            is_active=True
        )
        db.session.add(access)
        
        db.session.commit()
        
        # Generate JWT tokens for auto-login
        access_token = generate_access_token(user, user_type='end_customer')
        refresh_token = generate_refresh_token(user, user_type='end_customer')
        
        return jsonify({
            'success': True,
            'message': 'Machine activated and account created successfully',
            'user_id': user.id,
            'user_email': user.email,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'machine': {
                'id': machine.id,
                'serial_number': machine.serial_number,
                'model_name': machine.model.model_name,
                'status': machine.status
            },
            'end_customer': {
                'id': end_customer.id,
                'company_name': end_customer.company_name
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/machines/<int:machine_id>/users', methods=['GET'])
def get_machine_users(machine_id):
    """
    Get list of users with access to a machine
    
    Public endpoint (no auth) - for customer admins to see who has access
    """
    try:
        machine = MachineInstance.query.get(machine_id)
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Get all active accesses
        accesses = UserMachineAccess.query.filter_by(
            machine_instance_id=machine_id,
            is_active=True
        ).all()
        
        users_list = []
        for access in accesses:
            user = User.query.get(access.user_id)
            if user:
                users_list.append({
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'access_level': access.access_level,
                    'granted_at': access.granted_at.isoformat()
                })
        
        return jsonify({
            'machine_serial': machine.serial_number,
            'users': users_list,
            'total': len(users_list)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
