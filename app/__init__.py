from flask import Flask, request, make_response
from flask_cors import CORS
from app.config import Config
from app.db.firestore import init_firestore, is_firestore_available
from app.services.firebase_service import init_firebase, is_firebase_available, get_firebase_status
import os
import logging

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Get CORS origins from environment variable - Production ready
    cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
    cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
    
    # Add localhost for development
    if os.environ.get('FLASK_ENV') == 'development':
        cors_origins.extend([
            'http://localhost:3000',
            'http://localhost:8080', 
            'http://127.0.0.1:8080',
            'http://localhost:5173',  # Vite default
            'http://127.0.0.1:5173'
        ])
    
    logger.info(f"🌐 CORS Origins configured: {cors_origins}")
    
    # Enable CORS with comprehensive cross-domain support
    CORS(app, 
         origins=cors_origins,
         methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
         allow_headers=[
             "Content-Type", 
             "Authorization", 
             "X-Requested-With", 
             "Accept", 
             "Origin", 
             "X-CSRF-Token",
             "Access-Control-Allow-Origin",
             "Access-Control-Allow-Headers",
             "Access-Control-Allow-Methods"
         ],
         supports_credentials=True,
         max_age=86400,  # Cache preflight for 24 hours
         expose_headers=["Content-Range", "X-Content-Range"],
         send_wildcard=False,  # Important for credentials
         vary_header=True  # Add Vary: Origin header
    )
    
    # Add manual OPTIONS handler for all routes
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response

    # Add CORS headers to all responses
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        if origin in cors_origins or '*' in cors_origins:
            response.headers.add('Access-Control-Allow-Origin', origin or '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept,Origin,X-CSRF-Token')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS,PATCH')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '86400')
        return response
    
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