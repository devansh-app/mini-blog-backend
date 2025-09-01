"""
Authentication routes - only route definitions and request/response handling
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from app.auth.services import AuthService
from app.core.error_codes import ErrorMessages

# Create blueprint
auth = Blueprint('auth', __name__)


@auth.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'message': 'Flask Blog API is running'
    }), 200


@auth.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1100, "No JSON data provided")), 400
    
    response, status_code = AuthService.register_user(data)
    return jsonify(response), status_code


@auth.route('/login', methods=['POST'])
def login():
    """Login user and return JWT tokens"""
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1100, "No JSON data provided")), 400
    
    response, status_code = AuthService.login_user(data)
    return jsonify(response), status_code


@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify(ErrorMessages.get_error_response(1007, "Invalid refresh token")), 401

        new_access_token = create_access_token(identity=current_user_id)
        return jsonify({'access_token': new_access_token}), 200

    except Exception as e:
        return jsonify(ErrorMessages.get_error_response(1500, str(e))), 500


@auth.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    current_user_id = get_jwt_identity()
    response, status_code = AuthService.get_user_profile(current_user_id)
    return jsonify(response), status_code


@auth.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1100, "No JSON data provided")), 400
    
    response, status_code = AuthService.update_user_profile(current_user_id, data)
    return jsonify(response), status_code


@auth.route('/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Get user profile by ID"""
    response, status_code = AuthService.get_user_profile(user_id)
    return jsonify(response), status_code


@auth.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1100, "No JSON data provided")), 400
    
    response, status_code = AuthService.request_password_reset(data)
    return jsonify(response), status_code


@auth.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1100, "No JSON data provided")), 400
    
    response, status_code = AuthService.reset_password(data)
    return jsonify(response), status_code


@auth.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should discard tokens)"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify(ErrorMessages.get_error_response(1006, "Invalid token")), 401

        return jsonify({'message': 'Logged out successfully'}), 200

    except Exception as e:
        return jsonify(ErrorMessages.get_error_response(1500, str(e))), 500


@auth.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify(ErrorMessages.get_error_response(1006, "Invalid token")), 401

        data = request.get_json()
        if not data or not all(k in data for k in ['current_password', 'new_password']):
            return jsonify(ErrorMessages.get_error_response(1100, "Current password and new password are required")), 400

        # This would need to be implemented in AuthService
        # For now, return a placeholder response
        return jsonify({'message': 'Password change functionality to be implemented'}), 200

    except Exception as e:
        return jsonify(ErrorMessages.get_error_response(1500, str(e))), 500
