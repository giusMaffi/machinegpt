"""
Multi-Tenant Middleware
Created: 5 Feb 2026

Purpose: Ensure data isolation between producers (tenants)

How it works:
1. Extract producer_id from JWT token in request
2. Set PostgreSQL session variable 'app.current_producer_id'
3. Row-Level Security policies use this variable to filter queries
4. Prevents cross-tenant data access

Dependencies:
- Flask g object (request-scoped storage)
- SQLAlchemy db.session
- JWT token in Authorization header

Security:
- CRITICAL: This is the ONLY way to set producer_id
- Token validation happens BEFORE this middleware
- RLS policies enforce at database level (defense in depth)
"""

from flask import g, request, jsonify
from functools import wraps
import jwt
from sqlalchemy import text
import os


def set_tenant_context():
    """
    Middleware to set tenant context from JWT token.
    Must run AFTER token validation but BEFORE any DB query.
    """
    # Extract token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        # No token = no tenant context (public endpoints OK)
        g.producer_id = None
        return
    
    token = auth_header.replace('Bearer ', '')
    
    try:
        # Decode JWT (validation already done by @token_required)
        payload = jwt.decode(
            token, 
            os.environ.get('JWT_SECRET_KEY', 'dev-secret'),
            algorithms=['HS256']
        )
        
        producer_id = payload.get('producer_id')
        
        if not producer_id:
            g.producer_id = None
            return
        
        # Store in Flask g (request-scoped)
        g.producer_id = producer_id
        g.end_customer_id = payload.get('end_customer_id')
        g.user_id = payload.get('user_id')
        
        # Set PostgreSQL session variable for RLS
        from app import db
        db.session.execute(
            text("SET LOCAL app.current_producer_id = :id"),
            {"id": producer_id}
        )
        
        # Optional: Set end_customer_id for additional isolation
        if g.end_customer_id:
            db.session.execute(
                text("SET LOCAL app.current_end_customer_id = :id"),
                {"id": g.end_customer_id}
            )
        
    except jwt.InvalidTokenError:
        # Token invalid, no context
        g.producer_id = None
    except Exception as e:
        # Log error but don't crash
        print(f"Tenant context error: {e}")
        g.producer_id = None


def require_tenant(f):
    """
    Decorator to ensure tenant context is set.
    Use on routes that MUST have a producer_id.
    
    Usage:
        @app.route('/api/admin/documents')
        @token_required
        @require_tenant
        def list_documents():
            # g.producer_id guaranteed to exist
            pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'producer_id') or g.producer_id is None:
            return jsonify({
                "error": "Tenant context required",
                "detail": "Valid authentication token with producer_id needed"
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated


def get_current_producer_id():
    """
    Helper to safely get current producer_id.
    Returns None if not set.
    """
    return getattr(g, 'producer_id', None)


def get_current_end_customer_id():
    """
    Helper to safely get current end_customer_id.
    Returns None if not set.
    """
    return getattr(g, 'end_customer_id', None)


def get_current_user_id():
    """
    Helper to safely get current user_id.
    Returns None if not set.
    """
    return getattr(g, 'user_id', None)


# Pinecone namespace helper
def get_pinecone_namespace(producer_id=None):
    """
    Get Pinecone namespace for current tenant.
    Format: 'producer_{producer_id}'
    
    Args:
        producer_id: Optional override, otherwise uses g.producer_id
    
    Returns:
        str: Namespace string
    
    Raises:
        ValueError: If no producer_id available
    """
    pid = producer_id or get_current_producer_id()
    
    if not pid:
        raise ValueError("No producer_id available for Pinecone namespace")
    
    return f"producer_{pid}"


def validate_tenant_access(resource_producer_id):
    """
    Validate that current tenant can access a resource.
    
    Args:
        resource_producer_id: producer_id of the resource being accessed
    
    Returns:
        bool: True if access allowed
    
    Raises:
        ValueError: If current tenant doesn't match resource tenant
    """
    current = get_current_producer_id()
    
    if not current:
        raise ValueError("No tenant context set")
    
    if current != resource_producer_id:
        raise ValueError(
            f"Cross-tenant access denied: current={current}, resource={resource_producer_id}"
        )
    
    return True
