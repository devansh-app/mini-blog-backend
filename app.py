from app import create_app, db
from app.models import User, Post, Comment, Like

app = create_app()

@app.before_first_request
def create_tables():
    """Create database tables if they don't exist"""
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
    app.run(debug=True, host='0.0.0.0', port=5000)
