# Flask Blog Application

A complete Flask-based blog application with user authentication, posts, comments, and file uploads.

## Features

- 🔐 User authentication with JWT tokens
- 📝 Create, read, update, delete blog posts
- 💬 Comment system with nested replies
- ❤️ Like/unlike posts
- 📁 File uploads with S3 integration
- 🎨 Modern REST API
- 🐳 Docker support
- ☁️ Cloud deployment ready

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Make the deployment script executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# 5. Initialize database
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"

# 6. Run the application
python wsgi.py
```

### Option 3: Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build Docker image manually
docker build -t flask-blog-app .
docker run -p 5000:5000 flask-blog-app
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/refresh` - Refresh access token
- `GET /auth/profile` - Get user profile
- `POST /auth/logout` - Logout user

### Posts
- `GET /posts/` - Get all posts
- `POST /posts/create` - Create new post
- `GET /posts/<id>` - Get specific post
- `PUT /posts/<id>` - Update post
- `DELETE /posts/<id>` - Delete post

### Comments
- `GET /posts/<id>/comments` - Get post comments
- `POST /posts/<id>/comments` - Add comment
- `PUT /comments/<id>` - Update comment
- `DELETE /comments/<id>` - Delete comment

### Likes
- `POST /posts/<id>/like` - Like/unlike post
- `GET /posts/<id>/likes` - Get post likes

### Health Check
- `GET /auth/health` - Application health status

## Environment Variables

Create a `.env` file with the following variables:

```env
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_URL=your-database-url-here

# Optional: S3 Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_BUCKET_NAME=your-s3-bucket-name
AWS_REGION=your-aws-region
```

## Database Setup

### SQLite (Development)
```bash
# Default configuration uses SQLite
# No additional setup required
```

### PostgreSQL (Production)
```bash
# Install PostgreSQL dependencies
pip install psycopg2-binary

# Set DATABASE_URL in .env
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

## Deployment

### Render (Recommended)
1. Push your code to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com)
3. Click "New +" → "Blueprint"
4. Connect your repository
5. Click "Apply" to deploy

### Heroku
```bash
# Install Heroku CLI
# Create app and deploy
heroku create your-app-name
git push heroku main
```

### Docker
```bash
# Build image
docker build -t flask-blog-app .

# Run container
docker run -p 5000:5000 -e DATABASE_URL=your-db-url flask-blog-app
```

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest
```

### Code Formatting
```bash
# Install black
pip install black

# Format code
black .
```

### Database Migrations
```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade
```

## Project Structure

```
flask-blog-app/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Database models
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py        # Authentication routes
│   ├── posts/
│   │   ├── __init__.py
│   │   ├── forms.py         # Post forms
│   │   └── routes.py        # Post routes
│   ├── comments/
│   │   ├── __init__.py
│   │   └── routes.py        # Comment routes
│   ├── s3_service.py        # S3 file upload service
│   └── static/
│       └── uploads/         # File uploads
├── wsgi.py                  # WSGI entry point
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
├── render.yaml             # Render deployment config
├── deploy.sh               # Deployment script
└── README.md               # This file
```

## Configuration

### Production Settings
- Use PostgreSQL database
- Set `FLASK_ENV=production`
- Use strong secret keys
- Enable HTTPS
- Configure CORS for your domain

### Development Settings
- Use SQLite database
- Set `FLASK_ENV=development`
- Enable debug mode
- Allow all CORS origins

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure virtual environment is activated
   - Check all dependencies are installed
   - Verify Python version compatibility

2. **Database Connection**
   - Check `DATABASE_URL` environment variable
   - Ensure database server is running
   - Verify network connectivity

3. **File Uploads**
   - Check S3 credentials
   - Verify bucket permissions
   - Ensure upload directory exists

4. **CORS Issues**
   - Configure allowed origins
   - Check request headers
   - Verify frontend domain

### Debug Commands

```bash
# Check application status
curl http://localhost:5000/auth/health

# Test database connection
python -c "from app import create_app; app = create_app(); print(app.config['SQLALCHEMY_DATABASE_URI'])"

# View application logs
tail -f logs/app.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- 📧 Email: support@example.com
- 📖 Documentation: [docs.example.com](https://docs.example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
