"""
Comments routes - only route definitions and request/response handling
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.comments.services import CommentService
from app.core.error_codes import ErrorMessages

# Create blueprint
comments = Blueprint('comments', __name__)


@comments.route('/post/<int:post_id>', methods=['GET'])
def get_post_comments(post_id):
    """Get all comments for a specific post"""
    response, status_code = CommentService.get_post_comments(post_id)
    return jsonify(response), status_code


@comments.route('/<int:comment_id>', methods=['GET'])
def get_comment(comment_id):
    """Get a specific comment by ID with its replies"""
    response, status_code = CommentService.get_comment(comment_id)
    return jsonify(response), status_code


@comments.route('/post/<int:post_id>', methods=['POST'])
@jwt_required()
def create_comment(post_id):
    """Create a new comment on a post"""
    try:
        current_user_id = CommentService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1001, "No JSON data provided")), 400
    
    response, status_code = CommentService.create_comment(post_id, data, current_user_id)
    return jsonify(response), status_code


@comments.route('/<int:comment_id>', methods=['PUT'])
@jwt_required()
def update_comment(comment_id):
    """Update a comment"""
    try:
        current_user_id = CommentService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1001, "No JSON data provided")), 400
    
    response, status_code = CommentService.update_comment(comment_id, data, current_user_id)
    return jsonify(response), status_code


@comments.route('/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    """Delete a comment"""
    try:
        current_user_id = CommentService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    response, status_code = CommentService.delete_comment(comment_id, current_user_id)
    return jsonify(response), status_code


@comments.route('/user/<int:user_id>', methods=['GET'])
def get_user_comments(user_id):
    """Get comments by a specific user"""
    filters = {
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 10, type=int)
    }
    
    response, status_code = CommentService.get_user_comments(user_id, filters)
    return jsonify(response), status_code


@comments.route('/my-comments', methods=['GET'])
@jwt_required()
def get_my_comments():
    """Get comments by current user"""
    try:
        current_user_id = CommentService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    filters = {
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 10, type=int)
    }
    
    response, status_code = CommentService.get_user_comments(current_user_id, filters)
    return jsonify(response), status_code
