"""Document Models - Multi-format support"""
from datetime import datetime
from app import db
import hashlib


class Document(db.Model):
    """Document = Any file (PDF, Video, Audio, etc.)"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    producer_id = db.Column(db.Integer, db.ForeignKey('producers.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('machine_models.id'))
    
    # Identity
    title = db.Column(db.String(255), nullable=False)
    doc_type = db.Column(db.String(50))
    language = db.Column(db.String(10), default='en')
    
    # File Info
    file_type = db.Column(db.String(50), nullable=False)
    mime_type = db.Column(db.String(100))
    file_extension = db.Column(db.String(10))
    original_filename = db.Column(db.String(255))
    
    # Versioning
    file_hash = db.Column(db.String(64), nullable=False)
    version = db.Column(db.String(20), nullable=False, default='1.0')
    is_latest = db.Column(db.Boolean, default=True)
    
    # Storage
    file_path = db.Column(db.Text, nullable=False)
    file_size_bytes = db.Column(db.BigInteger)
    
    # Content metadata
    total_pages = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)
    total_chunks = db.Column(db.Integer)
    
    # Processing
    processing_status = db.Column(db.String(50), default='pending')
    processed_at = db.Column(db.DateTime)
    processing_error = db.Column(db.Text)
    processing_metadata = db.Column(db.JSON)
    
    # Ingestion
    source_type = db.Column(db.String(50), nullable=False)
    ingestion_metadata = db.Column(db.JSON)
    
    # Vector DB
    vector_namespace = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chunks = db.relationship('DocumentChunk', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_docs_producer', 'producer_id'),
        db.Index('idx_docs_hash', 'file_hash'),
    )
    
    def __repr__(self):
        return f'<Document {self.title}>'
    
    @staticmethod
    def calculate_file_hash(file_data):
        """Calculate SHA256 hash"""
        return hashlib.sha256(file_data).hexdigest()


class DocumentChunk(db.Model):
    """Document Chunk = Text segment for RAG"""
    __tablename__ = 'document_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    
    # Content
    chunk_index = db.Column(db.Integer, nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
    
    # Source reference
    source_reference = db.Column(db.String(255))
    
    # Metadata
    chunk_metadata = db.Column(db.JSON)
    
    # Vector DB
    vector_id = db.Column(db.String(255), nullable=False)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('document_id', 'chunk_index', name='_doc_chunk_uc'),
    )


class DocumentVersion(db.Model):
    """Document Version History"""
    __tablename__ = 'document_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    
    version = db.Column(db.String(20), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    changelog = db.Column(db.Text)