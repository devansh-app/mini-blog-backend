from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config
import os

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize CORS with wildcard to allow all origins
    CORS(app, resources={
        r"/*": {
            "origins": "*",
      
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register error handlers
    from app.core.error_handler import register_error_handlers
    register_error_handlers(app)
    
    # Register blueprints
    from app.auth.routes import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from app.posts.routes import posts as posts_blueprint
    app.register_blueprint(posts_blueprint, url_prefix='/posts')
    
    from app.comments.routes import comments as comments_blueprint
    app.register_blueprint(comments_blueprint, url_prefix='/comments')
    
    # Import models to ensure they are registered with SQLAlchemy
    from app.models import User, Post, Comment, Like
    
    return app
