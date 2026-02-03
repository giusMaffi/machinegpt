"""Machine Models"""
from datetime import datetime
from app import db
import secrets


class MachineModel(db.Model):
    """Machine Model = Product catalog (X500, A300, etc.)"""
    __tablename__ = 'machine_models'
    
    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    
    # Identity
    model_name = db.Column(db.String(255), nullable=False)
    model_code = db.Column(db.String(100))
    full_name = db.Column(db.String(255))
    category = db.Column(db.String(100))
    
    # Specifications
    specifications = db.Column(db.JSON)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instances = db.relationship('MachineInstance', backref='model', lazy='dynamic')
    documents = db.relationship('Document', backref='machine_model', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('producer_id', 'model_code', name='_producer_model_uc'),
    )
    
    def __repr__(self):
        return f'<MachineModel {self.model_name}>'


class MachineInstance(db.Model):
    """Machine Instance = Physical machine with serial number"""
    __tablename__ = 'machine_instances'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('machine_models.id'), nullable=False)
    end_customer_id = db.Column(db.Integer, db.ForeignKey('end_customers.id'))
    
    # Identity
    serial_number = db.Column(db.String(255), unique=True, nullable=False)
    
    # Activation
    activation_code = db.Column(db.String(255), unique=True, nullable=False)
    is_activated = db.Column(db.Boolean, default=False)
    activated_at = db.Column(db.DateTime)
    activated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Installation
    installation_site = db.Column(db.String(255))
    installation_date = db.Column(db.Date)
    
    # Service
    service_tier = db.Column(db.String(50), default='premium')
    status = db.Column(db.String(50), default='pending')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_accesses = db.relationship('UserMachineAccess', backref='machine_instance', lazy='dynamic')
    queries = db.relationship('Query', backref='machine', lazy='dynamic')
    
    __table_args__ = (
        db.Index('idx_machines_serial', 'serial_number'),
        db.Index('idx_machines_activation', 'activation_code'),
    )
    
    def __repr__(self):
        return f'<MachineInstance {self.serial_number}>'
    
    @staticmethod
    def generate_activation_code():
        """Generate secure activation code"""
        return secrets.token_urlsafe(32)
    
    def get_qr_url(self, base_url='https://support.machinegpt.com'):
        """Generate QR code URL"""
        return f"{base_url}/activate?code={self.activation_code}"