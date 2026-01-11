import firebase_admin
from firebase_admin import credentials, auth
from flask import request, jsonify
from functools import wraps
import logging
import os
import json
import base64

logger = logging.getLogger(__name__)

# Global flag to track Firebase availability
FIREBASE_AVAILABLE = False

def init_firebase():
    """Initialize Firebase Admin SDK with base64 credentials only"""
    global FIREBASE_AVAILABLE
    
    # Check if Firebase should be disabled via environment variable
    if os.environ.get('DISABLE_FIREBASE', '').lower() in ('true', '1', 'yes'):
        logger.info("🔥 Firebase initialization disabled via DISABLE_FIREBASE environment variable")
        FIREBASE_AVAILABLE = False
        return
    
    try:
        if not firebase_admin._apps:
            # Only use base64 encoded service account
            firebase_base64 = os.environ.get('FIREBASE_SERVICE_ACCOUNT_BASE64')
            if not firebase_base64:
                logger.error("❌ FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable not found")
                logger.info("💡 Set FIREBASE_SERVICE_ACCOUNT_BASE64 or DISABLE_FIREBASE=true")
                FIREBASE_AVAILABLE = False
                return
            
            try:
                # Fix base64 padding if needed
                missing_padding = len(firebase_base64) % 4
                if missing_padding:
                    firebase_base64 += '=' * (4 - missing_padding)
                
                # Decode base64 and parse JSON
                decoded_credentials = base64.b64decode(firebase_base64).decode('utf-8')
                service_account_info = json.loads(decoded_credentials)
                
                # Validate required fields
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                for field in required_fields:
                    if field not in service_account_info:
                        raise ValueError(f"Missing required field: {field}")
                
                # Initialize Firebase with service account
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                
                logger.info("✅ Firebase Admin SDK initialized successfully with base64 credentials")
                logger.info(f"🔥 Project ID: {service_account_info.get('project_id')}")
                logger.info(f"🔥 Client Email: {service_account_info.get('client_email')}")
                FIREBASE_AVAILABLE = True
                return
                
            except json.JSONDecodeError as json_error:
                logger.error(f"❌ Invalid JSON in base64 credentials: {str(json_error)}")
                FIREBASE_AVAILABLE = False
                return
            except ValueError as val_error:
                logger.error(f"❌ Invalid service account format: {str(val_error)}")
                FIREBASE_AVAILABLE = False
                return
            except Exception as base64_error:
                logger.error(f"❌ Failed to initialize Firebase with base64 credentials: {str(base64_error)}")
                FIREBASE_AVAILABLE = False
                return
        else:
            logger.info("✅ Firebase Admin SDK already initialized")
            FIREBASE_AVAILABLE = True
            
    except Exception as e:
        logger.error(f"❌ Firebase initialization failed: {str(e)}")
        logger.info("⚠️ Application will continue without Firebase authentication")
        FIREBASE_AVAILABLE = False

def is_firebase_available():
    """Check if Firebase is available and initialized"""
    return FIREBASE_AVAILABLE

def encode_service_account_to_base64(service_account_path: str) -> str:
    """Helper function to encode service account JSON to base64"""
    try:
        with open(service_account_path, 'r') as f:
            service_account_json = f.read()
        encoded = base64.b64encode(service_account_json.encode('utf-8')).decode('utf-8')
        return encoded
    except Exception as e:
        logger.error(f"Failed to encode service account to base64: {str(e)}")
        return None

def get_firebase_status():
    """Get detailed Firebase initialization status"""
    return {
        'available': FIREBASE_AVAILABLE,
        'base64_configured': bool(os.environ.get('FIREBASE_SERVICE_ACCOUNT_BASE64')),
        'disabled': os.environ.get('DISABLE_FIREBASE', '').lower() in ('true', '1', 'yes'),
        'apps_count': len(firebase_admin._apps) if firebase_admin._apps else 0
    }

class FirebaseAuthService:
    """Firebase Authentication service with graceful fallback"""
    
    @staticmethod
    def verify_token(id_token: str) -> dict:
        """Verify Firebase ID token and return user info"""
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase not available - token verification skipped")
            return None
            
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
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase not available - user lookup skipped")
            return None
            
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
    """Decorator to require Firebase authentication with graceful fallback"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If Firebase is not available, allow development mode
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase not available - using development mode (no auth required)")
            # Create a mock user for development
            request.current_user = {
                'uid': 'dev-user-123',
                'email': 'dev@example.com',
                'name': 'Development User',
                'photoUrl': None,
                'email_verified': True
            }
            return f(*args, **kwargs)
        
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
    """Decorator for optional authentication with graceful fallback"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If Firebase is not available, set no user
        if not FIREBASE_AVAILABLE:
            logger.debug("Firebase not available - no user authentication")
            request.current_user = None
            return f(*args, **kwargs)
        
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