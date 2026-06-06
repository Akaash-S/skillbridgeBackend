from flask import Flask, request, make_response
from flask_cors import CORS  # Re-enabled for direct backend access
from app.config import Config
from app.db.firestore import init_firestore, is_firestore_available
from app.services.firebase_service import init_firebase, is_firebase_available, get_firebase_status
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Limiter - Global Instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
    headers_enabled=True # Send rate limit headers to frontend
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize Limiter with app
    limiter.init_app(app)
    
    # Enable CORS for production deployment (direct backend access)
    # Read allowed origins from environment variable
    cors_origins = os.environ.get('CORS_ORIGINS', 'https://skillbridge.asolvitra.tech').split(',')
    CORS(app, 
         resources={r"/*": {"origins": cors_origins}},
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    logger.info(f"🌐 CORS enabled for origins: {cors_origins}")

    
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
    from app.routes.certificate import certificate_bp
    from app.routes.assessment import assessment_bp
    from app.routes.learning_journey import learning_journey_bp
    
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
    app.register_blueprint(certificate_bp, url_prefix='/certificate')
    app.register_blueprint(assessment_bp, url_prefix='/assessment')
    app.register_blueprint(learning_journey_bp, url_prefix='')
    
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