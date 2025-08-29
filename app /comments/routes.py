from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.comments import comments
from app.models import Comment, Post, User
from app import db
from datetime import datetime

def get_current_user_id():
    """Get current user ID from JWT token and convert to integer"""
    current_user_id = get_jwt_identity()
    
    if not current_user_id:
        raise ValueError("Invalid token")
    
    try:
        return int(current_user_id)
    except (ValueError, TypeError):
        raise ValueError("Invalid user ID in token")

@comments.route('/post/<int:post_id>', methods=['GET'])
def get_post_comments(post_id):
    """Get all comments for a specific post"""
    try:
        post = Post.query.get_or_404(post_id)
        comments_list = Comment.query.filter_by(post_id=post_id, parent_id=None).order_by(Comment.created_at.asc()).all()
        
        return jsonify({
            'post': post.to_dict(),
            'comments': [comment.to_dict(include_replies=True, max_depth=2) for comment in comments_list],
            'comments_count': len(comments_list)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch comments', 'details': str(e)}), 500

@comments.route('/<int:comment_id>', methods=['GET'])
def get_comment(comment_id):
    """Get a specific comment by ID with its replies"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        return jsonify({
            'comment': comment.to_dict(include_replies=True, max_depth=2)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Comment not found', 'details': str(e)}), 404

@comments.route('/post/<int:post_id>', methods=['POST'])
@jwt_required()
def create_comment(post_id):
    """Create a new comment on a post"""
    try:
        current_user_id = get_current_user_id()
        post = Post.query.get_or_404(post_id)
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content']
        parent_id = data.get('parent_id')  
        
        if len(content.strip()) == 0:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        if parent_id:
            parent_comment = Comment.query.filter_by(id=parent_id, post_id=post_id).first()
            if not parent_comment:
                return jsonify({'error': 'Parent comment not found or not on this post'}), 404
        
        comment = Comment(
            content=content,
            user_id=current_user_id,
            post_id=post_id,
            parent_id=parent_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'message': 'Comment created successfully',
            'comment': comment.to_dict(include_replies=False)
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create comment', 'details': str(e)}), 500

@comments.route('/<int:comment_id>', methods=['PUT'])
@jwt_required()
def update_comment(comment_id):
    """Update a comment"""
    try:
        current_user_id = get_current_user_id()
        comment = Comment.query.get_or_404(comment_id)
        
        if comment.user_id != current_user_id:
            return jsonify({'error': 'You can only edit your own comments'}), 403
        
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content']
        
        if len(content.strip()) == 0:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        comment.content = content
        db.session.commit()
        
        return jsonify({
            'message': 'Comment updated successfully',
            'comment': comment.to_dict(include_replies=False)
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update comment', 'details': str(e)}), 500

@comments.route('/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    """Delete a comment"""
    try:
        current_user_id = get_current_user_id()
        comment = Comment.query.get_or_404(comment_id)
        
        if comment.user_id != current_user_id:
            return jsonify({'error': 'You can only delete your own comments'}), 403
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({
            'message': 'Comment deleted successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete comment', 'details': str(e)}), 500

@comments.route('/user/<int:user_id>', methods=['GET'])
def get_user_comments(user_id):
    """Get all comments by a specific user"""
    try:
        user = User.query.get_or_404(user_id)
        comments_list = Comment.query.filter_by(user_id=user_id).order_by(Comment.created_at.desc()).all()
        
        return jsonify({
            'user': user.to_dict(),
            'comments': [comment.to_dict(include_replies=False) for comment in comments_list],
            'comments_count': len(comments_list)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user comments', 'details': str(e)}), 500

@comments.route('/<int:comment_id>/replies', methods=['GET'])
def get_comment_replies(comment_id):
    """Get all replies for a specific comment"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        replies_list = Comment.query.filter_by(parent_id=comment_id).order_by(Comment.created_at.asc()).all()
        
        return jsonify({
            'comment': comment.to_dict(include_replies=False),
            'replies': [reply.to_dict(include_replies=True, max_depth=1) for reply in replies_list],
            'replies_count': len(replies_list)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch comment replies', 'details': str(e)}), 500

@comments.route('/<int:comment_id>/reply', methods=['POST'])
@jwt_required()
def create_reply(comment_id):
    """Create a reply to a comment"""
    try:
        current_user_id = get_current_user_id()
        parent_comment = Comment.query.get_or_404(comment_id)
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content']
        
        if len(content.strip()) == 0:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        reply = Comment(
            content=content,
            user_id=current_user_id,
            post_id=parent_comment.post_id,  
            parent_id=comment_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(reply)
        db.session.commit()
        
        return jsonify({
            'message': 'Reply created successfully',
            'reply': reply.to_dict(include_replies=False)
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create reply', 'details': str(e)}), 500

@comments.route('/<int:comment_id>/replies/count', methods=['GET'])
def get_comment_replies_count(comment_id):
    """Get the total count of replies for a comment"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        total_replies = comment.get_all_replies_count()
        
        return jsonify({
            'comment_id': comment_id,
            'total_replies_count': total_replies,
            'direct_replies_count': len(comment.replies)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get replies count', 'details': str(e)}), 500
