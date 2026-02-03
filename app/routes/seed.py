"""Seed endpoint - REMOVE IN PRODUCTION"""
from flask import Blueprint, jsonify
from app import db
from app.models.producer import Producer
from app.models.machine import MachineModel, MachineInstance
from app.models.customer import EndCustomer, User, UserMachineAccess
from app.utils.auth import hash_password

bp = Blueprint('seed', __name__)

@bp.route('/seed-demo', methods=['POST'])
def seed_demo():
    producer = Producer(
        company_name='Demo Corp',
        slug='demo',
        status='active'
    )
    db.session.add(producer)
    db.session.flush()
    
    model = MachineModel(
        producer_id=producer.id,
        model_name='X500',
        model_code='DEMO-X500',
        category='test'
    )
    db.session.add(model)
    db.session.flush()
    
    machine = MachineInstance(
        producer_id=producer.id,
        model_id=model.id,
        serial_number='DEMO-001',
        activation_code='DEMO123',
        is_activated=True,
        status='active'
    )
    db.session.add(machine)
    db.session.flush()
    
    customer = EndCustomer(
        producer_id=producer.id,
        company_name='Test Company',
        country_code='US'
    )
    db.session.add(customer)
    db.session.flush()
    
    machine.end_customer_id = customer.id
    
    user = User(
        end_customer_id=customer.id,
        email='test@test.com',
        password_hash=hash_password('test123'),
        full_name='Test User',
        role='operator',
        is_active=True,
        email_verified=True
    )
    db.session.add(user)
    db.session.flush()
    
    access = UserMachineAccess(
        user_id=user.id,
        machine_instance_id=machine.id
    )
    db.session.add(access)
    db.session.commit()
    
    return jsonify({"status": "seeded"})
