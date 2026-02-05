"""
White-Label Configuration
Created: 5 Feb 2026

Purpose: Allow each producer (tenant) to customize branding

Features:
- Custom logo
- Brand colors (primary, secondary, accent)
- Company name
- Custom domain (future)
- Email templates branding

Usage:
    from app.utils.branding import get_branding
    
    branding = get_branding(producer_id)
    logo_url = branding['logo_url']
    primary_color = branding['colors']['primary']
"""

from app.models import Producer
from app.middleware import get_current_producer_id


# Default branding fallback
DEFAULT_BRANDING = {
    "logo_url": "https://machinegpt.com/assets/logo-default.svg",
    "company_name": "MachineGPT",
    "colors": {
        "primary": "#1a56db",      # Blue
        "secondary": "#6b7280",    # Gray
        "accent": "#f59e0b",       # Amber
        "success": "#10b981",      # Green
        "error": "#ef4444",        # Red
        "background": "#ffffff",
        "text": "#111827"
    },
    "fonts": {
        "heading": "Inter",
        "body": "Inter"
    },
    "support_email": "support@machinegpt.com",
    "support_phone": None,
    "custom_domain": None
}


def get_branding(producer_id=None):
    """
    Get white-label branding for a producer.
    
    Args:
        producer_id: Optional producer ID, defaults to current tenant
    
    Returns:
        dict: Branding configuration
    
    Example:
        {
            "logo_url": "https://cdn.amotek.com/logo.svg",
            "company_name": "Amotek",
            "colors": {"primary": "#e63946", ...},
            "support_email": "support@amotek.com"
        }
    """
    pid = producer_id or get_current_producer_id()
    
    if not pid:
        return DEFAULT_BRANDING.copy()
    
    producer = Producer.query.get(pid)
    
    if not producer:
        return DEFAULT_BRANDING.copy()
    
    # Merge producer settings with defaults
    branding = DEFAULT_BRANDING.copy()
    
    # Update with producer-specific values
    if producer.logo_url:
        branding['logo_url'] = producer.logo_url
    
    branding['company_name'] = producer.company_name
    
    if producer.primary_color:
        branding['colors']['primary'] = producer.primary_color
    
    if producer.secondary_color:
        branding['colors']['secondary'] = producer.secondary_color
    
    if producer.support_email:
        branding['support_email'] = producer.support_email
    
    if producer.support_phone:
        branding['support_phone'] = producer.support_phone
    
    if producer.custom_domain:
        branding['custom_domain'] = producer.custom_domain
    
    return branding


def get_logo_url(producer_id=None):
    """Quick helper to get just the logo URL."""
    return get_branding(producer_id)['logo_url']


def get_primary_color(producer_id=None):
    """Quick helper to get primary brand color."""
    return get_branding(producer_id)['colors']['primary']


def get_support_email(producer_id=None):
    """Quick helper to get support email."""
    return get_branding(producer_id)['support_email']


# ============================================================================
# API ENDPOINT EXAMPLE
# ============================================================================

"""
Add this to your routes/admin.py or routes/public.py:

@app.route('/api/branding')
@token_required
def get_current_branding():
    '''
    Return branding for current tenant.
    Used by frontend to customize UI.
    '''
    from app.utils.branding import get_branding
    
    branding = get_branding()
    
    return jsonify(branding)


# Frontend usage example (JavaScript):

async function loadBranding() {
    const response = await fetch('/api/branding', {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });
    
    const branding = await response.json();
    
    // Apply to UI
    document.getElementById('logo').src = branding.logo_url;
    document.documentElement.style.setProperty(
        '--color-primary', 
        branding.colors.primary
    );
    document.title = `${branding.company_name} Support`;
}
"""

# ============================================================================
# EMAIL TEMPLATE EXAMPLE
# ============================================================================

def get_email_template(producer_id=None):
    """
    Get HTML email template with tenant branding.
    
    Returns:
        str: HTML template with placeholders
    """
    branding = get_branding(producer_id)
    
    template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: {branding['fonts']['body']}, sans-serif;
                color: {branding['colors']['text']};
            }}
            .header {{
                background: {branding['colors']['primary']};
                padding: 20px;
                text-align: center;
            }}
            .logo {{
                max-width: 200px;
            }}
            .button {{
                background: {branding['colors']['primary']};
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{branding['logo_url']}" alt="{branding['company_name']}" class="logo">
        </div>
        <div class="content">
            {{{{ content }}}}
        </div>
        <div class="footer">
            <p>Need help? Contact us at <a href="mailto:{branding['support_email']}">{branding['support_email']}</a></p>
        </div>
    </body>
    </html>
    """
    
    return template


# ============================================================================
# UPDATE PRODUCER MODEL (if needed)
# ============================================================================

"""
Ensure your Producer model has these fields:

class Producer(db.Model):
    __tablename__ = 'producers'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), unique=True)
    
    # White-label fields
    logo_url = db.Column(db.Text)
    primary_color = db.Column(db.String(7), default='#1a56db')
    secondary_color = db.Column(db.String(7), default='#6b7280')
    support_email = db.Column(db.String(255))
    support_phone = db.Column(db.String(50))
    custom_domain = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    end_customers = db.relationship('EndCustomer', backref='producer')
    machine_models = db.relationship('MachineModel', backref='producer')
    documents = db.relationship('Document', backref='producer')

If fields missing, create Alembic migration:

alembic revision --autogenerate -m "add white-label fields to producers"
alembic upgrade head
"""
