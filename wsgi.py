"""WSGI entry point for Gunicorn on Railway."""
from app import app, init_db

with app.app_context():
    init_db()

application = app
