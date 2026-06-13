"""WSGI entry point for Gunicorn on Railway."""
from app import app, init_db
import os

# Ensure writable directories exist
os.makedirs(os.path.join(app.instance_path), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    init_db()

application = app
