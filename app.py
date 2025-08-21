from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
jwt = JWTManager(app)

db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Todo {self.title}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(120))  # Optional image upload
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    like_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Comment {self.body[:20]}>'




@app.route('/')
def index():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email} for u in users]), 200

@app.route('/register', methods=['POST'])
def register():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if username and email and password:
            new_user = User(username=username, email=email, password_hash=password)
            db.session.add(new_user)
            db.session.commit()
            return jsonify({"message": "Registration successful", "user_id": new_user.id}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error during registration: {e}")
        return jsonify({"message": "Registration failed", "error": str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
    else:
        username = request.form.get('username')
        password = request.form.get('password')

    if username and password:
        user = User.query.filter_by(username=username, password_hash=password).first()
        if user:
            access_token = create_access_token(identity=user.id)
            return jsonify({
                "message": "Login successful",
                "user_id": user.id,
                "access_token": access_token
            }), 200
        else:
            return jsonify({"message": "Invalid username or password"}), 401
    else:
        return jsonify({"message": "Username and password are required"}), 400


@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({'username': user.username, 'email': user.email}), 200

@app.route('/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"}), 200


@app.route('/create_post', methods=['POST'])
@jwt_required()
def create_post():
    try:
        title = request.form.get('title')
        body = request.form.get('body')
        user_id = get_jwt_identity()
        if title and body and user_id:
            new_post = Post(title=title, body=body, user_id=user_id)
            db.session.add(new_post)
            db.session.commit()
            return jsonify({"message": "Post created successfully"}), 200
        else:
            return jsonify({"message": "Title and body are required"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating post: {e}")
        return jsonify({"message": "Post creation failed", "error": str(e)}), 500

 
@app.route('/post/<int:post_id>')
def get_post(post_id):
    post = Post.query.get_or_404(post_id)
    return jsonify({'id': post.id, 'title': post.title, 'body': post.body, 'user_id': post.user_id}), 200


@app.route('/post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted"}), 200


@app.route('/create_comment', methods=['POST'])
@jwt_required()
def create_comment():
    try:
        body = request.form.get('body')
        post_id = request.form.get('post_id')
        user_id = get_jwt_identity()
        if body and user_id and post_id:
            new_comment = Comment(body=body, user_id=user_id, post_id=post_id)
            db.session.add(new_comment)
            db.session.commit()
            return jsonify({"message": "Comment created successfully", "comment_id": new_comment.id}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error creating comment: {e}")
        return jsonify({"message": "Comment creation failed", "error": str(e)}), 500



@app.route('/posts')
def posts():
    posts = Post.query.all()
    return jsonify([{'id': p.id, 'title': p.title, 'body': p.body} for p in posts]), 200

@app.route('/comments')
def comments():
    comments = Comment.query.all()
    return jsonify([{'id': c.id, 'body': c.body, 'post_id': c.post_id} for c in comments]), 200




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
