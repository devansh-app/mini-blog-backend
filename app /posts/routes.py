from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.posts import posts
from app.models import Post, User, Like
from app import db
from datetime import datetime
from sqlalchemy import or_, and_, desc, asc
import re
from app.s3_service import S3Service 

def get_current_user_id():
    """Get current user ID from JWT token and convert to integer"""
    current_user_id = get_jwt_identity()
    
    if not current_user_id:
        raise ValueError("Invalid token")
    
    try:
        return int(current_user_id)
    except (ValueError, TypeError):
        raise ValueError("Invalid user ID in token")

def parse_date_filter(date_str):
    """Parse date filter string (YYYY-MM-DD format)"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None

@posts.route('/', methods=['GET'])
def get_posts():
    """Get all posts with pagination and filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  
        
        search = request.args.get('search', '').strip()
        author_id = request.args.get('author_id', type=int)
        author_username = request.args.get('author', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')  
        sort_order = request.args.get('sort_order', 'desc')  
        
        query = Post.query
        
        if search:
            search_filter = or_(
                Post.title.ilike(f'%{search}%'),
                Post.content.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        if author_id:
            query = query.filter(Post.user_id == author_id)
        
        if author_username:
            query = query.join(User).filter(User.username.ilike(f'%{author_username}%'))
        
        if date_from:
            from_date = parse_date_filter(date_from)
            if from_date:
                query = query.filter(Post.created_at >= from_date)
        
        if date_to:
            to_date = parse_date_filter(date_to)
            if to_date:
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Post.created_at <= to_date)
        
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
        
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        posts_list = pagination.items
        
        response_data = {
            'posts': [post.to_dict() for post in posts_list],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_num': pagination.next_num,
                'prev_num': pagination.prev_num
            },
            'filters': {
                'search': search,
                'author_id': author_id,
                'author_username': author_username,
                'date_from': date_from,
                'date_to': date_to,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch posts', 'details': str(e)}), 500

@posts.route('/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post by ID"""
    try:
        post = Post.query.get_or_404(post_id)
        return jsonify({
            'post': post.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': 'Post not found', 'details': str(e)}), 404

@posts.route('/', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post"""
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        title = data['title']
        content = data['content']
        s3_file_key = data.get('s3_file_key', '').strip()  
        
       
        if s3_file_key and s3_file_key.startswith('http'):
           
            try:
                s3_file_key = s3_file_key.split('.com/')[-1]
            except:
                s3_file_key = None
        
        if len(title.strip()) == 0 or len(content.strip()) == 0:
            return jsonify({'error': 'Title and content cannot be empty'}), 400
        
        post = Post(
            title=title,
            content=content,
            s3_file_key=s3_file_key if s3_file_key else None,
            user_id=current_user_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'message': 'Post created successfully',
            'post': post.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create post', 'details': str(e)}), 500

@posts.route('/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    """Update a post"""
    try:
        current_user_id = get_current_user_id()
        post = Post.query.get_or_404(post_id)
        
        if post.user_id != current_user_id:
            return jsonify({'error': 'You can only edit your own posts'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if 'title' in data:
            if len(data['title'].strip()) == 0:
                return jsonify({'error': 'Title cannot be empty'}), 400
            post.title = data['title']
        
        if 'content' in data:
            if len(data['content'].strip()) == 0:
                return jsonify({'error': 'Content cannot be empty'}), 400
            post.content = data['content']
        
        # Handle S3 file key update
        if 's3_file_key' in data:
            # If there's an existing S3 file, delete it
            if post.s3_file_key:
                s3_service = S3Service()
                s3_service.delete_file(post.s3_file_key)
            
            s3_file_key = data['s3_file_key'].strip() if data['s3_file_key'].strip() else None
            
        
            if s3_file_key and s3_file_key.startswith('http'):
              
        
                try:
                    s3_file_key = s3_file_key.split('.com/')[-1]
                except:
                    s3_file_key = None
            
            post.s3_file_key = s3_file_key
        
        post.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Post updated successfully',
            'post': post.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update post', 'details': str(e)}), 500

@posts.route('/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a post"""
    try:
        current_user_id = get_current_user_id()
        post = Post.query.get_or_404(post_id)
        
        if post.user_id != current_user_id:
            return jsonify({'error': 'You can only delete your own posts'}), 403
        
      
        if post.s3_file_key:
            s3_service = S3Service()
            s3_service.delete_file(post.s3_file_key)
        
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({
            'message': 'Post deleted successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete post', 'details': str(e)}), 500

@posts.route('/user/<int:user_id>', methods=['GET'])
def get_user_posts(user_id):
    """Get all posts by a specific user with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
        search = request.args.get('search', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        user = User.query.get_or_404(user_id)
        
        query = Post.query.filter_by(user_id=user_id)
        
        if search:
            search_filter = or_(
                Post.title.ilike(f'%{search}%'),
                Post.content.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
 
        if date_from:
            from_date = parse_date_filter(date_from)
            if from_date:
                query = query.filter(Post.created_at >= from_date)
        
        if date_to:
            to_date = parse_date_filter(date_to)
            if to_date:
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Post.created_at <= to_date)
        
 
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
        
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        posts_list = pagination.items
        
        response_data = {
            'user': user.to_dict(),
            'posts': [post.to_dict() for post in posts_list],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_num': pagination.next_num,
                'prev_num': pagination.prev_num
            },
            'filters': {
                'search': search,
                'date_from': date_from,
                'date_to': date_to,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user posts', 'details': str(e)}), 500

@posts.route('/<int:post_id>/like', methods=['POST'])
@jwt_required()
def like_post(post_id):
    """Like a post"""
    try:
        current_user_id = get_current_user_id()
        post = Post.query.get_or_404(post_id)
        
       
        existing_like = Like.query.filter_by(user_id=current_user_id, post_id=post_id).first()
        if existing_like:
            return jsonify({'error': 'You have already liked this post'}), 409
        
       
        like = Like(
            user_id=current_user_id,
            post_id=post_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(like)
        db.session.commit()
        
        return jsonify({
            'message': 'Post liked successfully',
            'like': like.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to like post', 'details': str(e)}), 500

@posts.route('/<int:post_id>/unlike', methods=['DELETE'])
@jwt_required()
def unlike_post(post_id):
    """Unlike a post"""
    try:
        current_user_id = get_current_user_id()
        post = Post.query.get_or_404(post_id)
        
        like = Like.query.filter_by(user_id=current_user_id, post_id=post_id).first()
        if not like:
            return jsonify({'error': 'You have not liked this post'}), 404
        
 
        db.session.delete(like)
        db.session.commit()
        
        return jsonify({
            'message': 'Post unliked successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to unlike post', 'details': str(e)}), 500

@posts.route('/<int:post_id>/likes', methods=['GET'])
def get_post_likes(post_id):
    """Get all likes for a specific post with pagination"""
    try:
 
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        post = Post.query.get_or_404(post_id)
        
 
        query = Like.query.filter_by(post_id=post_id).order_by(Like.created_at.desc())
        
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        likes_list = pagination.items
        
        response_data = {
            'post': post.to_dict(),
            'likes': [like.to_dict() for like in likes_list],
            'likes_count': pagination.total,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_num': pagination.next_num,
                'prev_num': pagination.prev_num
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch post likes', 'details': str(e)}), 500

@posts.route('/upload-image-url', methods=['POST'])
@jwt_required()
def get_image_upload_url():
    """Generate a presigned URL for uploading an image to S3"""
    try:
        current_user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        file_extension = data.get('file_extension', '').strip()
        content_type = data.get('content_type', '').strip()
        
        if not file_extension or not content_type:
            return jsonify({'error': 'file_extension and content_type are required'}), 400
        
        s3_service = S3Service()
        if not s3_service.validate_file_extension(file_extension):
            return jsonify({'error': 'Invalid file extension. Allowed: jpg, jpeg, png, gif, webp'}), 400
        
        if not s3_service.validate_content_type(content_type):
            return jsonify({'error': 'Invalid content type. Allowed: image/jpeg, image/png, image/gif, image/webp'}), 400
        
        # Generate presigned URL
        presigned_data = s3_service.generate_presigned_url(file_extension, content_type)
        
        return jsonify({
            'message': 'Presigned URL generated successfully',
            'presigned_url': presigned_data['presigned_url'],
            'file_key': presigned_data['file_key'],
            'expires_in': presigned_data['expires_in'],
            'content_type': presigned_data['content_type']
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        return jsonify({'error': 'Failed to generate presigned URL', 'details': str(e)}), 500

@posts.route('/test-s3-connection', methods=['GET'])
@jwt_required()
def test_s3_connection():
    """Test AWS S3 connection and configuration"""
    try:
        s3_service = S3Service()
        result = s3_service.test_aws_connection()
        
        return jsonify({
            'message': 'S3 connection test completed',
            'result': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to test S3 connection', 'details': str(e)}), 500

@posts.route('/user/<int:user_id>/likes', methods=['GET'])
def get_user_likes(user_id):
    """Get all posts liked by a specific user with pagination"""
    try:
 
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
 
        search = request.args.get('search', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        user = User.query.get_or_404(user_id)
        
        query = Like.query.filter_by(user_id=user_id)
        
 
        if search:
            query = query.join(Post).filter(or_(
                Post.title.ilike(f'%{search}%'),
                Post.content.ilike(f'%{search}%')
            ))
        
        if date_from:
            from_date = parse_date_filter(date_from)
            if from_date:
                query = query.filter(Like.created_at >= from_date)
        
        if date_to:
            to_date = parse_date_filter(date_to)
            if to_date:
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Like.created_at <= to_date)
        
        if sort_by == 'post_title':
            query = query.join(Post).order_by(Post.title.asc() if sort_order == 'asc' else Post.title.desc())
        elif sort_by == 'post_created_at':
            query = query.join(Post).order_by(Post.created_at.asc() if sort_order == 'asc' else Post.created_at.desc())
        else:  
            query = query.order_by(Like.created_at.asc() if sort_order == 'asc' else Like.created_at.desc())
        
 
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        likes_list = pagination.items
        
        liked_posts = [like.post.to_dict() for like in likes_list]
        
        response_data = {
            'user': user.to_dict(),
            'liked_posts': liked_posts,
            'likes_count': pagination.total,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_num': pagination.next_num,
                'prev_num': pagination.prev_num
            },
            'filters': {
                'search': search,
                'date_from': date_from,
                'date_to': date_to,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user likes', 'details': str(e)}), 500
