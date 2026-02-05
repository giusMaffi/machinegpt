"""Activation code and serial number utilities"""
from app.models.machine import MachineInstance

def generate_serial_number(producer_code, model_code, year=2024):
    """
    Generate serial number: AMK-X500-2024-001234
    
    Args:
        producer_code: "AMK" for Amotek
        model_code: "X500"
        year: 2024
    
    Returns: Unique serial number
    """
    # Count existing machines for this model/year
    prefix = f"{producer_code}-{model_code}-{year}"
    count = MachineInstance.query.filter(
        MachineInstance.serial_number.like(f"{prefix}-%")
    ).count()
    
    next_number = count + 1
    serial = f"{prefix}-{next_number:06d}"
    
    return serial


def get_qr_code_url(activation_code, producer_slug='amotek'):
    """
    Generate activation URL for QR code
    
    Returns: https://support.amotek.com/activate?code=ABC123
    """
    base_url = f"https://support.{producer_slug}.com"
    return f"{base_url}/activate?code={activation_code}"
