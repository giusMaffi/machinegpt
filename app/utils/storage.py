"""Storage Utils - Local for now, R2 later"""
import os
from werkzeug.utils import secure_filename

def save_uploaded_file(file, producer_id):
    """Save file locally"""
    filename = secure_filename(file.filename)
    file_path = os.path.join('data', 'raw', f'producer_{producer_id}', filename)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file.save(file_path)
    
    return file_path