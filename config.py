import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Handle database URL with special characters in password
    _database_url = os.environ.get('DATABASE_URL')
    if _database_url and 'postgresql://' in _database_url:
        # Extract parts of the connection string
        try:
            # Remove postgresql:// prefix
            url_without_prefix = _database_url.replace('postgresql://', '')
            
            # Split by the LAST @ to separate auth from host (password may contain @ symbols)
            if '@' in url_without_prefix:
                # Find the last occurrence of @
                last_at_index = url_without_prefix.rindex('@')
                auth_part = url_without_prefix[:last_at_index]
                host_part = url_without_prefix[last_at_index + 1:]
                
                # Split auth part to get username and password
                if ':' in auth_part:
                    username, password = auth_part.split(':', 1)
                    
                    # URL encode the password to handle special characters
                    encoded_password = quote_plus(password)
                    
                    # Reconstruct the connection string
                    SQLALCHEMY_DATABASE_URI = f"postgresql://{username}:{encoded_password}@{host_part}"
                else:
                    SQLALCHEMY_DATABASE_URI = _database_url
            else:
                SQLALCHEMY_DATABASE_URI = _database_url
        except Exception:
            # Fallback to original URL if parsing fails
            SQLALCHEMY_DATABASE_URI = _database_url
    else:
        SQLALCHEMY_DATABASE_URI = _database_url or 'sqlite:///blog.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 24 * 3600  # 30 days

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
