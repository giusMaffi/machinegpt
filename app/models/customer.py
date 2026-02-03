"""End Customer and User Models"""
from datetime import datetime
from app import db


class EndCustomer(db.Model):
    """End Customer = Company that bought machines (Ferrero, Barilla, etc.)"""
    __tablename__ = 'end_customers'
    
    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    
    # Identity
    company_name = db.Column(db.String(255), nullable=False)
    country_code = db.Column(db.String(2))
    industry = db.Column(db.String(100))
    
    # Status
    status = db.Column(db.String(50), default='active')
    service_tier = db.Column(db.String(50), default='premium')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('producer_id', 'company_name', name='_producer_customer_uc'),
    )
    
    # Relationships
    users = db.relationship('User', backref='end_customer', lazy='dynamic', cascade='all, delete-orphan')
    machines = db.relationship('MachineInstance', backref='end_customer', lazy='dynamic')
    
    def __repr__(self):
        return f'<EndCustomer {self.company_name}>'


class User(db.Model):
    """User = Operator/Technician at end customer (Mario Rossi at Ferrero)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    end_customer_id = db.Column(db.Integer, db.ForeignKey('end_customers.id'), nullable=False)
    
    # Authentication
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Identity
    full_name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    role = db.Column(db.String(50), default='operator')
    
    # Preferences
    language_preference = db.Column(db.String(10), default='en')
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Activity
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    machine_accesses = db.relationship('UserMachineAccess', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    queries = db.relationship('Query', backref='user', lazy='dynamic')
    refresh_tokens = db.relationship('RefreshToken', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_users_email', 'email'),
    )
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'language_preference': self.language_preference,
            'is_active': self.is_active
        }
    
    def get_authorized_machine_ids(self):
        """Get list of machine IDs this user can access"""
        return [access.machine_instance_id for access in self.machine_accesses.all()]


class UserMachineAccess(db.Model):
    """Which users can access which machines"""
    __tablename__ = 'user_machine_access'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    machine_instance_id = db.Column(db.Integer, db.ForeignKey('machine_instances.id'), nullable=False)
    
    access_level = db.Column(db.String(50), default='read')
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'machine_instance_id', name='_user_machine_uc'),
    )