"""Producer Model - Machinery manufacturers"""
from datetime import datetime
from app import db


class Producer(db.Model):
    """Producer = Machinery manufacturer (Amotek, IMA, etc.)"""
    __tablename__ = 'producers'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identity
    company_name = db.Column(db.String(255), nullable=False, unique=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    
    # Status
    status = db.Column(db.String(50), default='active')
    
    # Branding
    logo_url = db.Column(db.Text)
    primary_color = db.Column(db.String(7), default='#1a56db')
    secondary_color = db.Column(db.String(7), default='#f59e0b')
    
    # Custom domains
    custom_domain = db.Column(db.String(255))
    admin_domain = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    end_customers = db.relationship('EndCustomer', backref='producer', lazy='dynamic', cascade='all, delete-orphan')
    machine_models = db.relationship('MachineModel', backref='producer', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='producer', lazy='dynamic', cascade='all, delete-orphan')
    producer_admins = db.relationship('ProducerAdmin', backref='producer', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Producer {self.company_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'slug': self.slug,
            'status': self.status,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ProducerAdmin(db.Model):
    """Producer Admin Users - Staff who manage producer account"""
    __tablename__ = 'producer_admins'
    
    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    
    # Identity
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    role = db.Column(db.String(50), default='admin')
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Activity
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProducerAdmin {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active
        }