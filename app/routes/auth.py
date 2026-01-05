from flask import Blueprint, request, jsonify
from app.services.firebase_service import FirebaseAuthService, auth_required
from app.db.firestore import FirestoreService
from app.utils.validators import validate_required_fields
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
db_service = FirestoreService()

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user with Firebase ID token and create/update user profile
    Expected payload: { "idToken": "firebase_id_token" }
    """
    try:
        data = request.get_json()
        
        # Validate request
        if not validate_required_fields(data, ['idToken']):
            return jsonify({
                'error': 'Missing required field: idToken',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Verify Firebase token
        user_info = FirebaseAuthService.verify_token(data['idToken'])
        if not user_info:
            return jsonify({
                'error': 'Invalid or expired Firebase token',
                'code': 'AUTH_TOKEN_INVALID'
            }), 401
        
        uid = user_info['uid']
        
        # Check if user exists in Firestore
        existing_user = db_service.get_document('users', uid)
        
        current_time = datetime.utcnow()
        
        if existing_user:
            # Update last login time
            db_service.update_document('users', uid, {
                'lastLoginAt': current_time
            })
            
            # Log activity
            db_service.log_user_activity(uid, 'LOGIN', 'User logged in')
            
            return jsonify({
                'message': 'Login successful',
                'user': existing_user,
                'isNewUser': False
            }), 200
        else:
            # Create new user profile
            new_user = {
                'uid': uid,
                'email': user_info['email'],
                'name': user_info['name'] or '',
                'avatar': user_info['photoUrl'] or '',
                'education': '',
                'experience': '',
                'interests': [],
                'notifications': True,
                'weeklyGoal': 10,
                'careerGoal': '',
                'experienceLevel': 'beginner',
                'onboardingCompleted': False,
                'createdAt': current_time,
                'lastLoginAt': current_time
            }
            
            success = db_service.create_document('users', uid, new_user)
            if not success:
                return jsonify({
                    'error': 'Failed to create user profile',
                    'code': 'USER_CREATION_FAILED'
                }), 500
            
            # Log activity
            db_service.log_user_activity(uid, 'REGISTRATION', 'New user registered')
            
            return jsonify({
                'message': 'User created successfully',
                'user': new_user,
                'isNewUser': True
            }), 201
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'error': 'Internal server error during login',
            'code': 'LOGIN_ERROR'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@auth_required
def get_current_user():
    """
    Get current authenticated user profile
    Requires: Authorization header with Firebase ID token
    """
    try:
        uid = request.current_user['uid']
        
        # Get user profile from Firestore
        user_profile = db_service.get_document('users', uid)
        if not user_profile:
            return jsonify({
                'error': 'User profile not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        return jsonify({
            'user': user_profile
        }), 200
        
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return jsonify({
            'error': 'Failed to get user profile',
            'code': 'GET_USER_ERROR'
        }), 500

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """
    Verify Firebase ID token without login
    Expected payload: { "idToken": "firebase_id_token" }
    """
    try:
        data = request.get_json()
        
        if not validate_required_fields(data, ['idToken']):
            return jsonify({
                'error': 'Missing required field: idToken',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        user_info = FirebaseAuthService.verify_token(data['idToken'])
        if not user_info:
            return jsonify({
                'error': 'Invalid or expired Firebase token',
                'code': 'AUTH_TOKEN_INVALID'
            }), 401
        
        return jsonify({
            'valid': True,
            'user': user_info
        }), 200
        
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return jsonify({
            'error': 'Token verification failed',
            'code': 'TOKEN_VERIFICATION_ERROR'
        }), 500

@auth_bp.route('/debug-token', methods=['GET'])
def debug_token():
    """
    Debug endpoint to check what token is being received
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'error': 'No Authorization header found',
                'headers': dict(request.headers)
            }), 400
        
        # Extract token
        try:
            scheme, token = auth_header.split(' ', 1)
            token_preview = f"{token[:20]}...{token[-10:]}" if len(token) > 30 else token
        except ValueError:
            return jsonify({
                'error': 'Invalid Authorization header format',
                'auth_header': auth_header
            }), 400
        
        # Try to verify token
        user_info = FirebaseAuthService.verify_token(token)
        
        return jsonify({
            'token_preview': token_preview,
            'token_length': len(token),
            'verification_result': 'valid' if user_info else 'invalid',
            'user_info': user_info if user_info else None
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Debug failed: {str(e)}',
            'auth_header': request.headers.get('Authorization', 'None')
        }), 500