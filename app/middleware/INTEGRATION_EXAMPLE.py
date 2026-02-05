"""
Flask App Integration Example
Shows how to integrate multi-tenant middleware

UPDATE YOUR app/__init__.py with this code:
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # ========================================================================
    # CRITICAL: Register tenant middleware BEFORE any routes
    # ========================================================================
    
    from app.middleware import set_tenant_context
    
    @app.before_request
    def setup_tenant_context():
        """
        Execute BEFORE every request.
        Sets producer_id context from JWT token.
        """
        set_tenant_context()
    
    # ========================================================================
    # Register blueprints
    # ========================================================================
    
    from app.routes.auth import auth_bp
    from app.routes.documents import documents_bp
    from app.routes.query import query_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(query_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # ========================================================================
    # Health check (no tenant context needed)
    # ========================================================================
    
    @app.route('/api/health')
    def health():
        return {"status": "ok"}
    
    return app


# ============================================================================
# EXAMPLE ROUTE USAGE
# ============================================================================

"""
Example 1: Admin route (requires tenant context)

from flask import Blueprint, jsonify
from app.middleware import require_tenant, get_current_producer_id
from app.models import Document

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/documents')
@token_required  # First: validate JWT
@require_tenant  # Second: ensure tenant context
def list_documents():
    # g.producer_id is guaranteed to be set
    # RLS policies automatically filter queries
    
    producer_id = get_current_producer_id()
    
    # This query is automatically filtered by RLS
    documents = Document.query.all()
    
    return jsonify({
        "producer_id": producer_id,
        "documents": [d.to_dict() for d in documents]
    })
"""

"""
Example 2: Pinecone query (namespace isolation)

from app.middleware import get_pinecone_namespace
from app.utils.vector_db import index

@query_bp.route('/query', methods=['POST'])
@token_required
@require_tenant
def query_ai():
    question = request.json['question']
    
    # Get tenant-specific namespace
    namespace = get_pinecone_namespace()
    
    # Search only within tenant's vectors
    results = index.query(
        vector=embedding,
        namespace=namespace,  # e.g., "producer_7"
        top_k=5
    )
    
    return jsonify(results)
"""

"""
Example 3: Cross-tenant access prevention

from app.middleware import validate_tenant_access
from app.models import Document

@admin_bp.route('/documents/<int:doc_id>')
@token_required
@require_tenant
def get_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Extra safety check (RLS already prevents this)
    try:
        validate_tenant_access(document.producer_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    
    return jsonify(document.to_dict())
"""

"""
Example 4: Manual namespace for admin operations

from app.middleware import get_current_producer_id

@admin_bp.route('/cleanup-vectors')
@token_required
@require_tenant
def cleanup_vectors():
    producer_id = get_current_producer_id()
    namespace = f"producer_{producer_id}"
    
    # Delete ALL vectors in tenant's namespace
    index.delete(delete_all=True, namespace=namespace)
    
    return jsonify({"success": True})
"""

# ============================================================================
# TESTING ISOLATION
# ============================================================================

"""
Test script to verify multi-tenant isolation:

import requests

# Get tokens for two different producers
token_producer_1 = login_user_from_producer_1()
token_producer_2 = login_user_from_producer_2()

# Producer 1 query
resp1 = requests.get(
    'https://api.machinegpt.com/api/admin/documents',
    headers={'Authorization': f'Bearer {token_producer_1}'}
)
docs_p1 = resp1.json()['documents']

# Producer 2 query
resp2 = requests.get(
    'https://api.machinegpt.com/api/admin/documents',
    headers={'Authorization': f'Bearer {token_producer_2}'}
)
docs_p2 = resp2.json()['documents']

# Verify NO overlap
assert set(d['id'] for d in docs_p1).isdisjoint(
    set(d['id'] for d in docs_p2)
), "ISOLATION BREACH: Cross-tenant data leak!"

print("✅ Isolation verified: No cross-tenant access")
"""
