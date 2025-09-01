#!/usr/bin/env python3
"""
WSGI entry point for Flask Blog Application
This file is used by production servers like Gunicorn, uWSGI, etc.
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Post, Comment, Like

# Create Flask application instance
application = create_app()

# For direct execution
if __name__ == "__main__":
    with application.app_context():
        try:
            db.create_all()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    # Run the application
    application.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
