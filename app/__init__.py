from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config import config
import os

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
 
    db.init_app(app)
    jwt.init_app(app)
    

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
 
    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    

    
    from app.models import User
    
    return app