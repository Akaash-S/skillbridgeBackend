from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.db.firestore import init_firestore
from app.services.firebase_service import init_firebase
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend with comprehensive configuration
    CORS(app, 
         origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8081", "http://127.0.0.1:8081", "https://skillbridge.app"],
         methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
         supports_credentials=True,
         max_age=86400  # Cache preflight for 24 hours
    )
    
    # Initialize Firebase and Firestore
    init_firebase()
    init_firestore()
    
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
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'skillbridge-backend'}, 200
    
    return app