"""Seed demo data"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.producer import Producer
from app.models.machine import MachineModel, MachineInstance
from app.models.customer import EndCustomer, User, UserMachineAccess
from app.utils.auth import hash_password

app = create_app()

with app.app_context():
    # Producer
    producer = Producer(
        company_name='Amotek Demo',
        slug='amotek',
        status='active'
    )
    db.session.add(producer)
    db.session.flush()
    
    # Model
    model = MachineModel(
        producer_id=producer.id,
        model_name='X500',
        model_code='AMK-X500-2024',
        category='packaging'
    )
    db.session.add(model)
    db.session.flush()
    
    # Machine
    machine = MachineInstance(
        producer_id=producer.id,
        model_id=model.id,
        serial_number='AMK-X500-2024-001234',
        activation_code='DEMO123',
        is_activated=True,
        status='active'
    )
    db.session.add(machine)
    db.session.flush()
    
    # Customer
    customer = EndCustomer(
        producer_id=producer.id,
        company_name='Ferrero SpA',
        country_code='IT',
        industry='food'
    )
    db.session.add(customer)
    db.session.flush()
    
    machine.end_customer_id = customer.id
    
    # User
    user = User(
        end_customer_id=customer.id,
        email='mario.rossi@ferrero.com',
        password_hash=hash_password('password123'),
        full_name='Mario Rossi',
        role='operator',
        is_active=True,
        email_verified=True
    )
    db.session.add(user)
    db.session.flush()
    
    # Access
    access = UserMachineAccess(
        user_id=user.id,
        machine_instance_id=machine.id
    )
    db.session.add(access)
    
    db.session.commit()
    
    print("✅ Demo data seeded!")
    print(f"Email: mario.rossi@ferrero.com")
    print(f"Password: password123")