"""Query and Auth Models"""
from datetime import datetime
from app import db


class Query(db.Model):
    """Query = User question + AI response"""
    __tablename__ = 'queries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    machine_instance_id = db.Column(db.Integer, db.ForeignKey('machine_instances.id'))
    
    # Question
    question = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10))
    
    # Answer
    answer = db.Column(db.Text)
    sources = db.Column(db.JSON)
    
    # Performance
    response_time_ms = db.Column(db.Integer)
    tokens_input = db.Column(db.Integer)
    tokens_output = db.Column(db.Integer)
    cost_usd = db.Column(db.Numeric(10, 6))
    
    # Quality
    confidence = db.Column(db.String(20))
    
    # Feedback
    feedback = db.Column(db.Integer)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_queries_user', 'user_id'),
    )
    
    def __repr__(self):
        return f'<Query {self.id}>'


class RefreshToken(db.Model):
    """Refresh Token for JWT"""
    __tablename__ = 'refresh_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_valid(self):
        if self.revoked:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True


class Invitation(db.Model):
    """User Invitation"""
    __tablename__ = 'invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    end_customer_id = db.Column(db.Integer, db.ForeignKey('end_customers.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    
    accepted = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    """Audit Log"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    action = db.Column(db.String(100), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(50))
    details = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)