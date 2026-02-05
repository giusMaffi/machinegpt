"""Admin routes for machine management"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.machine import MachineModel, MachineInstance
from app.models.customer import User, UserMachineAccess
from app.models.producer import Producer
from app.utils.auth import token_required
from app.utils.activation import generate_serial_number, get_qr_code_url

bp = Blueprint('admin_machines', __name__)


@bp.route('/machines', methods=['POST'])
@token_required
def create_machine():
    """
    Create new machine instance with activation code
    
    Admin only - creates machine ready for activation
    
    Request:
    {
        "model_id": 1,
        "installation_notes": "For Ferrero Alba plant"
    }
    
    Response:
    {
        "machine_id": 101,
        "serial_number": "AMK-X500-2024-000001",
        "activation_code": "Kx7jQ2m_pZ5nW8vR...",
        "qr_url": "https://support.amotek.com/activate?code=...",
        "status": "pending_activation"
    }
    """
    try:
        data = request.get_json()
        
        # Validate
        model_id = data.get('model_id')
        if not model_id:
            return jsonify({'error': 'model_id required'}), 400
        
        # Get model
        model = MachineModel.query.get(model_id)
        if not model:
            return jsonify({'error': 'Model not found'}), 404
        
        # Verify tenant (model must belong to this producer)
        if model.producer_id != g.producer_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get producer for serial generation
        producer = Producer.query.get(g.producer_id)
        producer_code = producer.company_name[:3].upper()  # AMK from Amotek
        
        # Generate serial number
        serial = generate_serial_number(
            producer_code=producer_code,
            model_code=model.model_code or model.model_name,
            year=2024
        )
        
        # Generate activation code
        activation_code = MachineInstance.generate_activation_code()
        
        # Create machine
        machine = MachineInstance(
            producer_id=g.producer_id,
            model_id=model_id,
            serial_number=serial,
            activation_code=activation_code,
            is_activated=False,
            status='pending_activation'
        )
        db.session.add(machine)
        db.session.commit()
        
        # Generate QR URL
        qr_url = get_qr_code_url(activation_code, producer.slug)
        
        return jsonify({
            'machine_id': machine.id,
            'serial_number': machine.serial_number,
            'activation_code': machine.activation_code,
            'qr_url': qr_url,
            'model_name': model.model_name,
            'status': 'pending_activation',
            'message': 'Machine created. Print QR code and attach to physical machine.'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/machines', methods=['GET'])
@token_required
def list_machines():
    """
    List all machines for this producer
    
    Query params:
    - status: filter by status (pending_activation, activated, etc)
    - model_id: filter by model
    """
    try:
        # Filters
        query = MachineInstance.query.filter_by(producer_id=g.producer_id)
        
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)
        
        model_id = request.args.get('model_id')
        if model_id:
            query = query.filter_by(model_id=int(model_id))
        
        machines = query.all()
        
        result = []
        for m in machines:
            result.append({
                'id': m.id,
                'serial_number': m.serial_number,
                'model_name': m.model.model_name,
                'status': m.status,
                'is_activated': m.is_activated,
                'activation_code': m.activation_code if not m.is_activated else None,
                'end_customer': m.end_customer.company_name if m.end_customer else None,
                'installation_site': m.installation_site,
                'created_at': m.created_at.isoformat()
            })
        
        return jsonify({
            'machines': result,
            'total': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/machines/<int:machine_id>', methods=['GET'])
@token_required
def get_machine(machine_id):
    """Get machine details"""
    try:
        machine = MachineInstance.query.get(machine_id)
        
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        if machine.producer_id != g.producer_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get authorized users
        accesses = UserMachineAccess.query.filter_by(
            machine_instance_id=machine_id
        ).all()
        
        authorized_users = []
        for access in accesses:
            user = User.query.get(access.user_id)
            if user:
                authorized_users.append({
                    'user_id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'access_level': access.access_level,
                    'granted_at': access.granted_at.isoformat()
                })
        
        return jsonify({
            'id': machine.id,
            'serial_number': machine.serial_number,
            'model': {
                'id': machine.model.id,
                'name': machine.model.model_name,
                'code': machine.model.model_code
            },
            'status': machine.status,
            'is_activated': machine.is_activated,
            'activation_code': machine.activation_code if not machine.is_activated else None,
            'end_customer': {
                'id': machine.end_customer.id,
                'name': machine.end_customer.company_name
            } if machine.end_customer else None,
            'installation_site': machine.installation_site,
            'installation_date': machine.installation_date.isoformat() if machine.installation_date else None,
            'authorized_users': authorized_users,
            'created_at': machine.created_at.isoformat(),
            'activated_at': machine.activated_at.isoformat() if machine.activated_at else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/access/grant', methods=['POST'])
@token_required
def grant_access():
    """
    Grant user access to machines
    
    Admin can assign specific machines to specific users
    
    Request:
    {
        "user_id": 1,
        "machine_ids": [101, 102],
        "access_level": "read"  // optional, default "read"
    }
    
    Response:
    {
        "user_id": 1,
        "machines_granted": 2,
        "message": "Access granted successfully"
    }
    """
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        machine_ids = data.get('machine_ids', [])
        access_level = data.get('access_level', 'read')
        
        if not user_id or not machine_ids:
            return jsonify({'error': 'user_id and machine_ids required'}), 400
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify user belongs to this producer's customers
        if user.end_customer.producer_id != g.producer_id:
            return jsonify({'error': 'User not in your tenant'}), 403
        
        granted_count = 0
        
        for machine_id in machine_ids:
            # Get machine
            machine = MachineInstance.query.get(machine_id)
            
            if not machine:
                continue
            
            # Verify machine belongs to this producer
            if machine.producer_id != g.producer_id:
                continue
            
            # Check if access already exists
            existing = UserMachineAccess.query.filter_by(
                user_id=user_id,
                machine_instance_id=machine_id
            ).first()
            
            if existing:
                # Update access level
                existing.access_level = access_level
                existing.is_active = True
            else:
                # Create new access
                access = UserMachineAccess(
                    user_id=user_id,
                    machine_instance_id=machine_id,
                    access_level=access_level
                )
                db.session.add(access)
            
            granted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'user_id': user_id,
            'user_email': user.email,
            'machines_granted': granted_count,
            'access_level': access_level,
            'message': f'Access granted to {granted_count} machine(s)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/access/revoke', methods=['POST'])
@token_required
def revoke_access():
    """
    Revoke user access to machines
    
    Request:
    {
        "user_id": 1,
        "machine_ids": [101]
    }
    """
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        machine_ids = data.get('machine_ids', [])
        
        if not user_id or not machine_ids:
            return jsonify({'error': 'user_id and machine_ids required'}), 400
        
        revoked_count = 0
        
        for machine_id in machine_ids:
            access = UserMachineAccess.query.filter_by(
                user_id=user_id,
                machine_instance_id=machine_id
            ).first()
            
            if access:
                access.is_active = False
                revoked_count += 1
        
        db.session.commit()
        
        return jsonify({
            'user_id': user_id,
            'machines_revoked': revoked_count,
            'message': f'Access revoked from {revoked_count} machine(s)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
