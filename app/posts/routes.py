"""
Posts routes - only route definitions and request/response handling
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.posts.services import PostService
from app.core.error_codes import ErrorMessages

# Create blueprint
posts = Blueprint('posts', __name__)


@posts.route('/', methods=['GET'])
def get_posts():
    """Get all posts with pagination and filters"""
    filters = {
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 10, type=int),
        'search': request.args.get('search', '').strip(),
        'author_id': request.args.get('author_id', type=int),
        'author': request.args.get('author', '').strip(),
        'date_from': request.args.get('date_from', '').strip(),
        'date_to': request.args.get('date_to', '').strip(),
        'sort_by': request.args.get('sort_by', 'created_at'),
        'sort_order': request.args.get('sort_order', 'desc')
    }
    
    response, status_code = PostService.get_posts(filters)
    return jsonify(response), status_code


@posts.route('/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post by ID"""
    response, status_code = PostService.get_post(post_id)
    return jsonify(response), status_code


@posts.route('/', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post"""
    try:
        current_user_id = PostService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1001, "No JSON data provided")), 400
    
    response, status_code = PostService.create_post(data, current_user_id)
    return jsonify(response), status_code


@posts.route('/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    """Update a post"""
    try:
        current_user_id = PostService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1001, "No JSON data provided")), 400
    
    response, status_code = PostService.update_post(post_id, data, current_user_id)
    return jsonify(response), status_code


@posts.route('/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a post"""
    try:
        current_user_id = PostService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    response, status_code = PostService.delete_post(post_id, current_user_id)
    return jsonify(response), status_code


@posts.route('/<int:post_id>/like', methods=['POST'])
@jwt_required()
def like_post(post_id):
    """Like or unlike a post"""
    try:
        current_user_id = PostService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    response, status_code = PostService.like_post(post_id, current_user_id)
    return jsonify(response), status_code


@posts.route('/upload-image-url', methods=['POST'])
@jwt_required()
def upload_image_url():
    """Generate S3 URL for direct image upload"""
    data = request.get_json()
    if not data:
        return jsonify(ErrorMessages.get_error_response(1100, "No JSON data provided")), 400
    
    file_extension = data.get('file_extension', '').strip()
    content_type = data.get('content_type', '').strip()
    
    if not file_extension or not content_type:
        return jsonify(ErrorMessages.get_error_response(1100, "file_extension and content_type are required")), 400
    
    response, status_code = PostService.upload_image_url(file_extension, content_type)
    return jsonify(response), status_code


@posts.route('/user/<int:user_id>', methods=['GET'])
def get_user_posts(user_id):
    """Get posts by a specific user"""
    filters = {
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 10, type=int)
    }
    
    response, status_code = PostService.get_user_posts(user_id, filters)
    return jsonify(response), status_code


@posts.route('/my-posts', methods=['GET'])
@jwt_required()
def get_my_posts():
    """Get posts by current user"""
    try:
        current_user_id = PostService.get_current_user_id()
    except ValueError as e:
        return jsonify(ErrorMessages.get_error_response(1006, str(e))), 401
    
    filters = {
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 10, type=int)
    }
    
    response, status_code = PostService.get_user_posts(current_user_id, filters)
    return jsonify(response), status_code
