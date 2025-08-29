from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from app.auth import auth
from app.models import User
from app import db
import secrets
import string


password_reset_tokens = {}

def generate_reset_token():
    """Generate a secure random token for password reset"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))


from app import jwt

@jwt.invalid_token_loader
def invalid_token_callback(err):
    return jsonify({"error": "Invalid token", "details": err}), 422

@jwt.unauthorized_loader
def unauthorized_callback(err):
    return jsonify({"error": "Missing or invalid Authorization header", "details": err}), 401

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
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['username', 'email', 'password']):
            return jsonify({'error': 'Missing required fields'}), 400

        username = data['username']
        email = data['email']
        password = data['password']

        if len(username) < 3 or len(username) > 20:
            return jsonify({'error': 'Username must be between 3 and 20 characters'}), 400
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already taken'}), 409
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        if not user.id:
            raise Exception("User ID not generated after commit")

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500


@auth.route('/login', methods=['POST'])
def login():
    """Login user and return JWT tokens"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['username', 'password']):
            return jsonify({'error': 'Missing username or password'}), 400

        username = data['username']
        password = data['password']

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid username or password'}), 401

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    except Exception as e:
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500


@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'error': 'Invalid refresh token'}), 401

        new_access_token = create_access_token(identity=current_user_id)

        return jsonify({
            'access_token': new_access_token
        }), 200

    except Exception as e:
        return jsonify({'error': 'Token refresh failed', 'details': str(e)}), 500


@auth.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """Get current user profile"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'error': 'Invalid token'}), 401

        try:
            user_id = int(current_user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid user ID in token'}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'user': user.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to get profile', 'details': str(e)}), 500


@auth.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Send password reset email (simulated)"""
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400

        email = data['email']
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200

        reset_token = generate_reset_token()
        password_reset_tokens[reset_token] = {
            'user_id': user.id,
            'email': email
        }

        reset_link = f"/auth/reset-password?token={reset_token}"

        return jsonify({
            'message': 'Password reset link sent to your email',
            'reset_link': reset_link 
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to process password reset request', 'details': str(e)}), 500


@auth.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['token', 'password']):
            return jsonify({'error': 'Token and new password are required'}), 400

        token = data['token']
        new_password = data['password']

        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        if token not in password_reset_tokens:
            return jsonify({'error': 'Invalid or expired reset token'}), 400

        token_data = password_reset_tokens[token]
        user_id = token_data['user_id']

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.set_password(new_password)
        db.session.commit()

        del password_reset_tokens[token]

        return jsonify({'message': 'Password reset successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to reset password', 'details': str(e)}), 500


@auth.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should discard tokens)"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'error': 'Invalid token'}), 401

        return jsonify({'message': 'Logged out successfully'}), 200

    except Exception as e:
        return jsonify({'error': 'Logout failed', 'details': str(e)}), 500


@auth.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile information"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'error': 'Invalid token'}), 401

        try:
            user_id = int(current_user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid user ID in token'}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update username if provided
        if 'username' in data:
            new_username = data['username'].strip()
            if len(new_username) < 3 or len(new_username) > 20:
                return jsonify({'error': 'Username must be between 3 and 20 characters'}), 400
            
            # Check if username is already taken by another user
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Username already taken'}), 409
            
            user.username = new_username

        # Update email if provided
        if 'email' in data:
            new_email = data['email'].strip()
            if not new_email or '@' not in new_email:
                return jsonify({'error': 'Invalid email format'}), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Email already registered'}), 409
            
            user.email = new_email

        db.session.commit()

        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile', 'details': str(e)}), 500


@auth.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'error': 'Invalid token'}), 401

        try:
            user_id = int(current_user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid user ID in token'}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if not data or not all(k in data for k in ['current_password', 'new_password']):
            return jsonify({'error': 'Current password and new password are required'}), 400

        current_password = data['current_password']
        new_password = data['new_password']

        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400

        # Check if new password is same as current
        if user.check_password(new_password):
            return jsonify({'error': 'New password must be different from current password'}), 400

        # Update password
        user.set_password(new_password)
        db.session.commit()

        return jsonify({'message': 'Password changed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to change password', 'details': str(e)}), 500


@auth.route('/my-posts', methods=['GET'])
@jwt_required()
def get_my_posts():
    """Get posts by current user with pagination"""
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({'error': 'Invalid token'}), 401

        try:
            user_id = int(current_user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid user ID in token'}), 401

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 10

        # Import Post model here to avoid circular imports
        from app.models import Post
        
        # Get posts by current user
        posts_query = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc())
        
        # Apply pagination
        pagination = posts_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        posts = pagination.items
        
        # Convert posts to dictionary format
        posts_data = []
        for post in posts:
            post_dict = post.to_dict()
            posts_data.append(post_dict)

        return jsonify({
            'posts': posts_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to get posts', 'details': str(e)}), 500
