"""Serve document images"""
from flask import Blueprint, send_from_directory
import os

bp = Blueprint('images', __name__)

@bp.route('/static/images/<path:filepath>')
def serve_image(filepath):
    """Serve images from data/processed/images/"""
    images_dir = os.path.join(os.getcwd(), 'data', 'processed', 'images')
    return send_from_directory(images_dir, filepath)
