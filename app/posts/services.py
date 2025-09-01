"""
Posts service containing business logic for post operations
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import or_, and_, desc, asc
from app.models import Post, User, Like, Comment
from app import db
from app.core.error_codes import ErrorCodes, ErrorMessages
from app.s3_service import S3Service


class PostService:
    """Service class for post business logic"""
    
    @staticmethod
    def get_current_user_id() -> int:
        """Get current user ID from JWT token and convert to integer"""
        from flask_jwt_extended import get_jwt_identity
        
        current_user_id = get_jwt_identity()
        
        if not current_user_id:
            raise ValueError("Invalid token")
        
        try:
            return int(current_user_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid user ID in token")
    
    @staticmethod
    def parse_date_filter(date_str: str) -> Optional[datetime]:
        """Parse date filter string (YYYY-MM-DD format)"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return None
    
    @staticmethod
    def get_posts(filters: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Get all posts with pagination and filters"""
        try:
            page = filters.get('page', 1)
            per_page = min(filters.get('per_page', 10), 100)
            
            search = filters.get('search', '').strip()
            author_id = filters.get('author_id')
            author_username = filters.get('author', '').strip()
            date_from = filters.get('date_from', '').strip()
            date_to = filters.get('date_to', '').strip()
            sort_by = filters.get('sort_by', 'created_at')
            sort_order = filters.get('sort_order', 'desc')
            
            query = Post.query
            
            # Apply search filter
            if search:
                search_filter = or_(
                    Post.title.ilike(f'%{search}%'),
                    Post.content.ilike(f'%{search}%')
                )
                query = query.filter(search_filter)
            
            # Apply author filter
            if author_id:
                query = query.filter(Post.user_id == author_id)
            
            if author_username:
                query = query.join(User).filter(User.username.ilike(f'%{author_username}%'))
            
            # Apply date filters
            if date_from:
                from_date = PostService.parse_date_filter(date_from)
                if from_date:
                    query = query.filter(Post.created_at >= from_date)
            
            if date_to:
                to_date = PostService.parse_date_filter(date_to)
                if to_date:
                    to_date = to_date.replace(hour=23, minute=59, second=59)
                    query = query.filter(Post.created_at <= to_date)
            
            # Apply sorting
            if sort_by == 'title':
                sort_column = Post.title
            elif sort_by == 'likes_count':
                query = query.outerjoin(Like).group_by(Post.id)
                sort_column = db.func.count(Like.id)
            else:
                sort_column = Post.created_at
            
            if sort_order == 'asc':
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            posts_list = pagination.items
            
            return {
                'posts': [post.to_dict() for post in posts_list],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev,
                }
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
    
    @staticmethod
    def get_post(post_id: int) -> Tuple[Dict[str, Any], int]:
        """Get a specific post by ID"""
        try:
            post = Post.query.get(post_id)
            if not post:
                return ErrorMessages.get_error_response(ErrorCodes.POST_NOT_FOUND), 404
            
            return {
                'post': post.to_dict()
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
    
    @staticmethod
    def create_post(data: Dict[str, Any], user_id: int) -> Tuple[Dict[str, Any], int]:
        """Create a new post"""
        try:
            # Validate required fields
            if not all(k in data for k in ['title', 'content']):
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS), 400
            
            title = data['title'].strip()
            content = data['content'].strip()
            
            # Validate input lengths
            if len(title) < 1 or len(title) > 200:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_POST_TITLE_LENGTH), 400
            
            if len(content) < 1 or len(content) > 10000:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_POST_CONTENT_LENGTH), 400
            
            # Create post
            post = Post(
                title=title,
                content=content,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            
            # Set S3 file key if provided
            if 's3_file_key' in data:
                s3_file_key = data['s3_file_key']
                if s3_file_key is not None:
                    s3_file_key = s3_file_key.strip()
                    if s3_file_key:
                        post.s3_file_key = s3_file_key
            
            # Set legacy image_path if provided (for backward compatibility)
            if 'image_path' in data:
                image_path = data['image_path']
                if image_path is not None:
                    image_path = image_path.strip()
                    if image_path:
                        post.image_path = image_path
            
            db.session.add(post)
            db.session.commit()
            
            return {
                'message': 'Post created successfully',
                'post': post.to_dict()
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def update_post(post_id: int, data: Dict[str, Any], user_id: int) -> Tuple[Dict[str, Any], int]:
        """Update a post"""
        try:
            post = Post.query.get(post_id)
            if not post:
                return ErrorMessages.get_error_response(ErrorCodes.POST_NOT_FOUND), 404
            
            # Check ownership
            if post.user_id != user_id:
                return ErrorMessages.get_error_response(ErrorCodes.UNAUTHORIZED), 403
            
            # Update fields if provided
            if 'title' in data:
                title = data['title'].strip()
                if len(title) < 1 or len(title) > 200:
                    return ErrorMessages.get_error_response(ErrorCodes.INVALID_POST_TITLE_LENGTH), 400
                post.title = title
            
            if 'content' in data:
                content = data['content'].strip()
                if len(content) < 1 or len(content) > 10000:
                    return ErrorMessages.get_error_response(ErrorCodes.INVALID_POST_CONTENT_LENGTH), 400
                post.content = content
            
            # Update S3 file key if provided
            if 's3_file_key' in data:
                s3_file_key = data['s3_file_key']
                if s3_file_key is not None:
                    s3_file_key = s3_file_key.strip()
                    if s3_file_key:
                        post.s3_file_key = s3_file_key
                        # Clear legacy image_path when using S3
                        post.image_path = None
                    else:
                        # If empty, clear both S3 and legacy fields
                        post.s3_file_key = None
                        post.image_path = None
                else:
                    # If None, clear both S3 and legacy fields
                    post.s3_file_key = None
                    post.image_path = None
            
            # Update legacy image_path if provided (for backward compatibility)
            if 'image_path' in data:
                image_path = data['image_path']
                if image_path is not None:
                    image_path = image_path.strip()
                    if image_path:
                        post.image_path = image_path
                        # Clear S3 file key when using legacy image_path
                        post.s3_file_key = None
                    else:
                        # If empty, clear both fields
                        post.image_path = None
                        post.s3_file_key = None
                else:
                    # If None, clear both fields
                    post.image_path = None
                    post.s3_file_key = None
            
            post.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'message': 'Post updated successfully',
                'post': post.to_dict()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def delete_post(post_id: int, user_id: int) -> Tuple[Dict[str, Any], int]:
        """Delete a post"""
        try:
            post = Post.query.get(post_id)
            if not post:
                return ErrorMessages.get_error_response(ErrorCodes.POST_NOT_FOUND), 404
            
            # Check ownership
            if post.user_id != user_id:
                return ErrorMessages.get_error_response(ErrorCodes.UNAUTHORIZED), 403
            
            # Delete associated comments and likes
            Comment.query.filter_by(post_id=post_id).delete()
            Like.query.filter_by(post_id=post_id).delete()
            
            db.session.delete(post)
            db.session.commit()
            
            return {
                'message': 'Post deleted successfully'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def like_post(post_id: int, user_id: int) -> Tuple[Dict[str, Any], int]:
        """Like or unlike a post"""
        try:
            post = Post.query.get(post_id)
            if not post:
                return ErrorMessages.get_error_response(ErrorCodes.POST_NOT_FOUND), 404
            
            # Check if user already liked the post
            existing_like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
            
            if existing_like:
                # Unlike
                db.session.delete(existing_like)
                message = 'Post unliked successfully'
            else:
                # Like
                like = Like(user_id=user_id, post_id=post_id, created_at=datetime.utcnow())
                db.session.add(like)
                message = 'Post liked successfully'
            
            db.session.commit()
            
            return {
                'message': message,
                'liked': existing_like is None
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def upload_image_url(file_extension: str, content_type: str) -> Tuple[Dict[str, Any], int]:
        """Generate S3 URL for direct image upload"""
        try:
            if not file_extension or not content_type:
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS, "file_extension and content_type are required"), 400
            
            # Validate file extension
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            if file_extension.lower() not in allowed_extensions:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_FILE_TYPE, f"File extension must be one of: {', '.join(allowed_extensions)}"), 400
            
            # Validate content type
            allowed_content_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if content_type.lower() not in allowed_content_types:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_FILE_TYPE, f"Content type must be one of: {', '.join(allowed_content_types)}"), 400
            
            # Generate presigned URL using S3 service
            s3_service = S3Service()
            presigned_data = s3_service.generate_presigned_url(file_extension, content_type)
            
            return {
                'message': 'S3 upload URL generated successfully',
                'presigned_url': presigned_data['presigned_url'],
                'file_key': presigned_data['file_key'],
                'bucket_name': presigned_data['bucket_name'],
                'expires_in': presigned_data['expires_in'],
                'content_type': presigned_data['content_type'],
                'file_extension': file_extension
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.UPLOAD_FAILED, str(e)), 500
    
    @staticmethod
    def get_user_posts(user_id: int, filters: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Get posts by a specific user"""
        try:
            page = filters.get('page', 1)
            per_page = min(filters.get('per_page', 10), 50)
            
            # Get posts by user
            posts_query = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc())
            
            # Apply pagination
            pagination = posts_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            posts = pagination.items
            
            return {
                'posts': [post.to_dict() for post in posts],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
