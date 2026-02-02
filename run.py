"""MachineGPT - Application Entry Point"""
import os
from app import create_app

app = create_app(os.getenv('FLASK_ENV'))

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config['DEBUG']
    )