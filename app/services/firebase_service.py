import firebase_admin
from firebase_admin import credentials, auth
from flask import request, jsonify
from functools import wraps
import logging
import os

logger = logging.getLogger(__name__)

def init_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        if not firebase_admin._apps:
            cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                # For Google Cloud environments, use default credentials
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized with default credentials")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        raise

class FirebaseAuthService:
    """Firebase Authentication service"""
    
    @staticmethod
    def verify_token(id_token: str) -> dict:
        """Verify Firebase ID token and return user info"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            return {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'photoUrl': decoded_token.get('picture'),
                'email_verified': decoded_token.get('email_verified', False)
            }
        except auth.InvalidIdTokenError:
            logger.warning("Invalid Firebase ID token")
            return None
        except auth.ExpiredIdTokenError:
            logger.warning("Expired Firebase ID token")
            return None
        except Exception as e:
            logger.error(f"Error verifying Firebase token: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_uid(uid: str) -> dict:
        """Get user record by UID"""
        try:
            user_record = auth.get_user(uid)
            return {
                'uid': user_record.uid,
                'email': user_record.email,
                'name': user_record.display_name,
                'photoUrl': user_record.photo_url,
                'email_verified': user_record.email_verified,
                'disabled': user_record.disabled
            }
        except auth.UserNotFoundError:
            logger.warning(f"User not found: {uid}")
            return None
        except Exception as e:
            logger.error(f"Error getting user by UID: {str(e)}")
            return None
    
    @staticmethod
    def extract_token_from_request() -> str:
        """Extract Firebase ID token from request headers"""
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        # Expected format: "Bearer <token>"
        try:
            scheme, token = auth_header.split(' ', 1)
            if scheme.lower() != 'bearer':
                return None
            return token
        except ValueError:
            return None
    
    @staticmethod
    def get_current_user():
        """Get current authenticated user from request"""
        token = FirebaseAuthService.extract_token_from_request()
        if not token:
            return None
        
        return FirebaseAuthService.verify_token(token)

def auth_required(f):
    """Decorator to require Firebase authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extract token from Authorization header
            token = FirebaseAuthService.extract_token_from_request()
            if not token:
                logger.warning("Missing authorization token in request")
                return jsonify({
                    'error': 'Missing authorization token',
                    'code': 'AUTH_TOKEN_MISSING'
                }), 401
            
            logger.info(f"Verifying token: {token[:20]}...")
            
            # Verify token
            user_info = FirebaseAuthService.verify_token(token)
            if not user_info:
                logger.warning(f"Invalid or expired token: {token[:20]}...")
                return jsonify({
                    'error': 'Invalid or expired token',
                    'code': 'AUTH_TOKEN_INVALID'
                }), 401
            
            logger.info(f"Token verified successfully for user: {user_info.get('email', 'unknown')}")
            
            # Add user info to request context
            request.current_user = user_info
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({
                'error': 'Authentication failed',
                'code': 'AUTH_FAILED'
            }), 401
    
    return decorated_function

def optional_auth(f):
    """Decorator for optional authentication (user info available if authenticated)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = FirebaseAuthService.extract_token_from_request()
            if token:
                user_info = FirebaseAuthService.verify_token(token)
                request.current_user = user_info
            else:
                request.current_user = None
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Optional auth error: {str(e)}")
            request.current_user = None
            return f(*args, **kwargs)
    
    return decorated_function