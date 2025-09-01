"""
Authentication service containing business logic for user authentication
"""

import secrets
import string
from typing import Dict, Any, Optional, Tuple
from flask_jwt_extended import create_access_token, create_refresh_token
from app.models import User
from app import db
from app.core.error_codes import ErrorCodes, ErrorMessages

# In-memory storage for password reset tokens (in production, use Redis or database)
password_reset_tokens = {}


class AuthService:
    """Service class for authentication business logic"""
    
    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure random token for password reset"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    @staticmethod
    def register_user(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Register a new user"""
        try:
            # Validate required fields
            if not all(k in data for k in ['username', 'email', 'password']):
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS), 400
            
            username = data['username'].strip()
            email = data['email'].strip().lower()
            password = data['password']
            
            # Validate input lengths
            if len(username) < 3 or len(username) > 20:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_USERNAME_LENGTH), 400
            
            if len(password) < 6:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_PASSWORD_LENGTH), 400
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                return ErrorMessages.get_error_response(ErrorCodes.USERNAME_TAKEN), 409
            
            if User.query.filter_by(email=email).first():
                return ErrorMessages.get_error_response(ErrorCodes.EMAIL_TAKEN), 409
            
            # Create new user
            user = User(username=username, email=email)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            if not user.id:
                raise Exception("User ID not generated after commit")
            
            # Generate tokens
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            return {
                'message': 'User registered successfully',
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def login_user(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Login user and return JWT tokens"""
        try:
            # Validate required fields
            if not all(k in data for k in ['username', 'password']):
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS), 400
            
            username = data['username'].strip()
            password = data['password']
            
            # Find user and verify password
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_CREDENTIALS), 401
            
            # Generate tokens
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            return {
                'message': 'Login successful',
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
    
    @staticmethod
    def get_user_profile(user_id: str) -> Tuple[Dict[str, Any], int]:
        """Get user profile by ID"""
        try:
            user = User.query.get(user_id)
            if not user:
                return ErrorMessages.get_error_response(ErrorCodes.USER_NOT_FOUND_BY_ID), 404
            
            return {
                'user': user.to_dict()
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
    
    @staticmethod
    def update_user_profile(user_id: str, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Update user profile"""
        try:
            user = User.query.get(user_id)
            if not user:
                return ErrorMessages.get_error_response(ErrorCodes.USER_NOT_FOUND_BY_ID), 404
            
            # Update fields if provided
            if 'username' in data:
                new_username = data['username'].strip()
                if len(new_username) < 3 or len(new_username) > 20:
                    return ErrorMessages.get_error_response(ErrorCodes.INVALID_USERNAME_LENGTH), 400
                
                # Check if username is already taken by another user
                existing_user = User.query.filter_by(username=new_username).first()
                if existing_user and existing_user.id != user.id:
                    return ErrorMessages.get_error_response(ErrorCodes.USERNAME_TAKEN), 409
                
                user.username = new_username
            
            if 'email' in data:
                new_email = data['email'].strip().lower()
                # Check if email is already taken by another user
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user and existing_user.id != user.id:
                    return ErrorMessages.get_error_response(ErrorCodes.EMAIL_TAKEN), 409
                
                user.email = new_email
            
            db.session.commit()
            
            return {
                'message': 'Profile updated successfully',
                'user': user.to_dict()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def request_password_reset(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Request password reset"""
        try:
            if 'email' not in data:
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS), 400
            
            email = data['email'].strip().lower()
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Generate reset token
                reset_token = AuthService.generate_reset_token()
                password_reset_tokens[reset_token] = user.id
                
                # In a real application, send email here
                # For now, just return the token
                return {
                    'message': 'Password reset email sent',
                    'reset_token': reset_token  # Remove this in production
                }, 200
            else:
                # Don't reveal if email exists or not for security
                return {
                    'message': 'If the email exists, a password reset link has been sent'
                }, 200
                
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
    
    @staticmethod
    def reset_password(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Reset password using token"""
        try:
            if not all(k in data for k in ['token', 'new_password']):
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS), 400
            
            token = data['token']
            new_password = data['new_password']
            
            if len(new_password) < 6:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_PASSWORD_LENGTH), 400
            
            # Verify token
            user_id = password_reset_tokens.get(token)
            if not user_id:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_TOKEN), 400
            
            user = User.query.get(user_id)
            if not user:
                return ErrorMessages.get_error_response(ErrorCodes.USER_NOT_FOUND_BY_ID), 404
            
            # Update password
            user.set_password(new_password)
            db.session.commit()
            
            # Remove used token
            del password_reset_tokens[token]
            
            return {
                'message': 'Password reset successfully'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
