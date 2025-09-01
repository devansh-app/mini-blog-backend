"""
Comments service containing business logic for comment operations
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from app.models import Comment, Post, User
from app import db
from app.core.error_codes import ErrorCodes, ErrorMessages


class CommentService:
    """Service class for comment business logic"""
    
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
    def get_post_comments(post_id: int) -> Tuple[Dict[str, Any], int]:
        """Get all comments for a specific post"""
        try:
            post = Post.query.get(post_id)
            if not post:
                return ErrorMessages.get_error_response(ErrorCodes.POST_NOT_FOUND), 404
            
            comments_list = Comment.query.filter_by(
                post_id=post_id, 
                parent_id=None
            ).order_by(Comment.created_at.asc()).all()
            
            return {
                'post': post.to_dict(),
                'comments': [comment.to_dict(include_replies=True, max_depth=2) for comment in comments_list],
                'comments_count': len(comments_list)
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
    
    @staticmethod
    def get_comment(comment_id: int) -> Tuple[Dict[str, Any], int]:
        """Get a specific comment by ID with its replies"""
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return ErrorMessages.get_error_response(ErrorCodes.COMMENT_NOT_FOUND), 404
            
            return {
                'comment': comment.to_dict(include_replies=True, max_depth=2)
            }, 200
            
        except Exception as e:
            return ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(e)), 500
    
    @staticmethod
    def create_comment(post_id: int, data: Dict[str, Any], user_id: int) -> Tuple[Dict[str, Any], int]:
        """Create a new comment on a post"""
        try:
            # Check if post exists
            post = Post.query.get(post_id)
            if not post:
                return ErrorMessages.get_error_response(ErrorCodes.POST_NOT_FOUND), 404
            
            # Validate required fields
            if 'content' not in data:
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS), 400
            
            content = data['content'].strip()
            parent_id = data.get('parent_id')
            
            # Validate content
            if len(content) == 0:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_COMMENT_LENGTH), 400
            
            if len(content) > 1000:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_COMMENT_LENGTH), 400
            
            # Validate parent comment if provided
            if parent_id:
                parent_comment = Comment.query.filter_by(id=parent_id, post_id=post_id).first()
                if not parent_comment:
                    return ErrorMessages.get_error_response(ErrorCodes.COMMENT_NOT_FOUND), 404
            
            # Create comment
            comment = Comment(
                content=content,
                user_id=user_id,
                post_id=post_id,
                parent_id=parent_id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(comment)
            db.session.commit()
            
            return {
                'message': 'Comment created successfully',
                'comment': comment.to_dict(include_replies=False)
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def update_comment(comment_id: int, data: Dict[str, Any], user_id: int) -> Tuple[Dict[str, Any], int]:
        """Update a comment"""
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return ErrorMessages.get_error_response(ErrorCodes.COMMENT_NOT_FOUND), 404
            
            # Check ownership
            if comment.user_id != user_id:
                return ErrorMessages.get_error_response(ErrorCodes.UNAUTHORIZED), 403
            
            # Validate required fields
            if 'content' not in data:
                return ErrorMessages.get_error_response(ErrorCodes.MISSING_REQUIRED_FIELDS), 400
            
            content = data['content'].strip()
            
            # Validate content
            if len(content) == 0:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_COMMENT_LENGTH), 400
            
            if len(content) > 1000:
                return ErrorMessages.get_error_response(ErrorCodes.INVALID_COMMENT_LENGTH), 400
            
            # Update comment
            comment.content = content
            comment.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'message': 'Comment updated successfully',
                'comment': comment.to_dict(include_replies=False)
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def delete_comment(comment_id: int, user_id: int) -> Tuple[Dict[str, Any], int]:
        """Delete a comment"""
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return ErrorMessages.get_error_response(ErrorCodes.COMMENT_NOT_FOUND), 404
            
            # Check ownership
            if comment.user_id != user_id:
                return ErrorMessages.get_error_response(ErrorCodes.UNAUTHORIZED), 403
            
            # Delete comment and all its replies
            CommentService._delete_comment_and_replies(comment_id)
            db.session.commit()
            
            return {
                'message': 'Comment deleted successfully'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return ErrorMessages.get_error_response(ErrorCodes.COMMIT_ERROR, str(e)), 500
    
    @staticmethod
    def _delete_comment_and_replies(comment_id: int):
        """Recursively delete a comment and all its replies"""
        # Get all replies to this comment
        replies = Comment.query.filter_by(parent_id=comment_id).all()
        
        # Recursively delete all replies
        for reply in replies:
            CommentService._delete_comment_and_replies(reply.id)
        
        # Delete the comment itself
        comment = Comment.query.get(comment_id)
        if comment:
            db.session.delete(comment)
    
    @staticmethod
    def get_user_comments(user_id: int, filters: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Get comments by a specific user"""
        try:
            page = filters.get('page', 1)
            per_page = min(filters.get('per_page', 10), 50)
            
            # Get comments by user
            comments_query = Comment.query.filter_by(user_id=user_id).order_by(Comment.created_at.desc())
            
            # Apply pagination
            pagination = comments_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            comments = pagination.items
            
            return {
                'comments': [comment.to_dict(include_replies=False) for comment in comments],
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
