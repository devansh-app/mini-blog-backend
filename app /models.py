from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255)) 
    s3_file_key = db.Column(db.String(500))  # S3 file 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        # Get image URL from S3
        image_url = None
        if self.s3_file_key:
            from app.s3_service import S3Service
            s3_service = S3Service()
            image_url = s3_service.get_file_url(self.s3_file_key)
        elif self.image_path:
            image_url = self.image_path
            
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'image_path': self.image_path,
            's3_file_key': self.s3_file_key,
            'image_url': image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id,
            'author': self.author.to_dict() if self.author else None,
            'likes_count': len(self.likes),
            'likes': [like.to_dict() for like in self.likes],
            'comments_count': len(self.comments)
        }
    
    def __repr__(self):
        return f'<Post {self.title}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)  # For replies
    
    # Relationships
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_replies=True, max_depth=2, current_depth=0):
        """Convert comment to dictionary with optional nested replies"""
        comment_dict = {
            'id': self.id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'parent_id': self.parent_id,
            'author': self.author.to_dict() if self.author else None,
            'replies_count': len(self.replies) if self.replies else 0
        }
        
        # Include replies 
        if include_replies and self.replies and current_depth < max_depth:
            comment_dict['replies'] = [
                reply.to_dict(include_replies=True, max_depth=max_depth, current_depth=current_depth + 1)
                for reply in sorted(self.replies, key=lambda x: x.created_at)
            ]
        
        return comment_dict
    
    def get_all_replies_count(self):
        """Get total count of all replies (including nested ones)"""
        count = len(self.replies)
        for reply in self.replies:
            count += reply.get_all_replies_count()
        return count
    
    def __repr__(self):
        return f'<Comment {self.id}>'

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can only like a post once
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': self.user.to_dict() if self.user else None
        }
    
    def __repr__(self):
        return f'<Like {self.id}>'
