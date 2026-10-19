#!/bin/bash

# Disable CORS in Flask since Nginx is handling it
set -e

echo "🔧 Disabling Flask CORS (Nginx will handle it)"
echo "==============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "app/__init__.py" ]; then
    echo "❌ Error: app/__init__.py not found"
    echo "Please run this script from the backend directory"
    exit 1
fi

# Backup the original file
echo "📋 Creating backup..."
cp app/__init__.py app/__init__.py.backup
echo "✅ Backup created: app/__init__.py.backup"

# Comment out CORS configuration
echo "🔧 Disabling CORS in Flask..."
cat > app/__init__.py << 'PYTHON_CODE'
from flask import Flask, request, make_response
# from flask_cors import CORS  # DISABLED - Nginx handles CORS
from app.config import Config
from app.db.firestore import init_firestore, is_firestore_available
from app.services.firebase_service import init_firebase, is_firebase_available, get_firebase_status
import os
import logging

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # CORS is now handled by Nginx - no need for flask-cors
    # This prevents duplicate CORS headers
    logger.info("🌐 CORS handling delegated to Nginx reverse proxy")
    
    # Initialize Firebase with detailed status reporting
    logger.info("🚀 Starting Firebase initialization...")
    try:
        init_firebase()
        firebase_status = get_firebase_status()
        
        if is_firebase_available():
            logger.info("✅ Firebase initialized successfully")
        else:
            if firebase_status['disabled']:
                logger.info("⚠️ Firebase disabled via DISABLE_FIREBASE environment variable")
            elif not firebase_status['base64_configured']:
                logger.warning("⚠️ Firebase not available - FIREBASE_SERVICE_ACCOUNT_BASE64 not configured")
            else:
                logger.warning("⚠️ Firebase not available - initialization failed")
        
        logger.info(f"🔥 Firebase Status: {firebase_status}")
        
    except Exception as e:
        logger.error(f"❌ Firebase initialization error: {str(e)}")
    
    # Initialize Firestore with detailed status reporting
    logger.info("🚀 Starting Firestore initialization...")
    try:
        init_firestore()
        
        if is_firestore_available():
            logger.info("✅ Firestore initialized successfully")
        else:
            logger.warning("⚠️ Firestore not available - using mock database operations")
        
    except Exception as e:
        logger.error(f"❌ Firestore initialization error: {str(e)}")
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.skills import skills_bp
    from app.routes.roles import roles_bp
    from app.routes.roadmap import roadmap_bp
    from app.routes.learning import learning_bp
    from app.routes.jobs import jobs_bp
    from app.routes.activity import activity_bp
    from app.routes.settings import settings_bp
    from app.routes.user_state import user_state_bp
    from app.routes.courses import courses_bp
    from app.routes.mfa import mfa_bp
    from app.routes.email import email_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(skills_bp, url_prefix='/skills')
    app.register_blueprint(roles_bp, url_prefix='/roles')
    app.register_blueprint(roadmap_bp, url_prefix='/roadmap')
    app.register_blueprint(learning_bp, url_prefix='/learning')
    app.register_blueprint(jobs_bp, url_prefix='/jobs')
    app.register_blueprint(activity_bp, url_prefix='/activity')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(user_state_bp, url_prefix='/user-state')
    app.register_blueprint(courses_bp, url_prefix='/courses')
    app.register_blueprint(mfa_bp, url_prefix='/mfa')
    app.register_blueprint(email_bp, url_prefix='/email')
    
    @app.route('/health')
    def health_check():
        firebase_status = get_firebase_status()
        return {
            'status': 'healthy', 
            'service': 'skillbridge-backend',
            'firebase': firebase_status,
            'firestore': {
                'available': is_firestore_available(),
                'base64_configured': bool(os.environ.get('FIREBASE_SERVICE_ACCOUNT_BASE64')),
                'disabled': os.environ.get('DISABLE_FIREBASE', '').lower() in ('true', '1', 'yes')
            }
        }, 200
    
    return app
PYTHON_CODE

echo "✅ Flask CORS disabled"

# Rebuild Docker container
echo ""
echo "🐳 Rebuilding Docker container..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo ""
echo "⏳ Waiting for container to start..."
sleep 15

# Test the application
echo "🧪 Testing application..."
if curl -f -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Application is running"
else
    echo "⚠️ Application may still be starting"
    echo "Check logs: docker compose logs -f"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Flask CORS Disabled Successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔒 CORS is now handled exclusively by Nginx"
echo "   This prevents duplicate CORS headers"
echo ""
echo "🧪 Test from your frontend:"
echo "   The CORS errors should now be resolved"
echo ""
echo "📋 If you need to restore Flask CORS:"
echo "   cp app/__init__.py.backup app/__init__.py"
echo "   docker compose restart"
echo ""