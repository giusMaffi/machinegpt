"""Simple seed script usando i VERI modelli di Peppe"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.producer import Producer, ProducerAdmin
from app.models.customer import EndCustomer, User
from app.models.machine import MachineModel, MachineInstance
import bcrypt
from datetime import datetime

app = create_app()

with app.app_context():
    print("🌱 Seeding simple demo...")
    
    # Producer Amotek
    amotek = Producer(
        company_name="Amotek",
        slug="amotek",
        logo_url="https://via.placeholder.com/200x80/e63946/ffffff?text=AMOTEK",
        primary_color="#e63946",
        secondary_color="#457b9d",
        support_email="support@amotek.com",
        support_phone="+39 0521 123456",
        status="active"
    )
    db.session.add(amotek)
    db.session.flush()
    print(f"✅ Amotek (ID: {amotek.id})")
    
    # Amotek Admin
    admin = ProducerAdmin(
        producer_id=amotek.id,
        email="admin@amotek.com",
        password_hash=bcrypt.hashpw("amotek123".encode(), bcrypt.gensalt()).decode(),
        full_name="Admin Amotek",
        role="super_admin",
        is_active=True,
        email_verified=True
    )
    db.session.add(admin)
    print("✅ Admin: admin@amotek.com / amotek123")
    
    # Machine Model (solo campi che esistono!)
    x500 = MachineModel(
        producer_id=amotek.id,
        model_name="X500",
        model_code="AMK-X500",
        full_name="X500 Packaging Machine",
        category="packaging",
        specifications={"max_speed": "120 packages/min", "power": "5.5 kW"}
    )
    db.session.add(x500)
    db.session.flush()
    print(f"✅ Model: X500 (ID: {x500.id})")
    
    # End Customer
    ferrero = EndCustomer(
        producer_id=amotek.id,
        company_name="Ferrero SpA",
        country_code="IT",
        industry="food",
        status="active"
    )
    db.session.add(ferrero)
    db.session.flush()
    print(f"✅ Customer: Ferrero (ID: {ferrero.id})")
    
    # End Customer User (operator)
    operator = User(
        end_customer_id=ferrero.id,
        email="operator@ferrero.com",
        password_hash=bcrypt.hashpw("demo123".encode(), bcrypt.gensalt()).decode(),
        full_name="Operator Ferrero",
        role="operator",
        language_preference="it",
        is_active=True,
        email_verified=True
    )
    db.session.add(operator)
    db.session.flush()
    print(f"✅ User: operator@ferrero.com / demo123")
    
    # Machine Instance
    machine = MachineInstance(
        producer_id=amotek.id,
        model_id=x500.id,
        end_customer_id=ferrero.id,
        serial_number="AMK-X500-2024-001",
        activation_code="TEST123",
        is_activated=True,
        activated_at=datetime.utcnow(),
        activated_by=operator.id
    )
    db.session.add(machine)
    print("✅ Machine: AMK-X500-2024-001")
    
    db.session.commit()
    
    print("\n✅ Seed complete!")
    print("\n🔐 LOGIN:")
    print("   Admin: admin@amotek.com / amotek123")
    print("   User:  operator@ferrero.com / demo123")
