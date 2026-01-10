from flask import Blueprint, request, jsonify
from app.services.firebase_service import FirebaseAuthService, auth_required
from app.db.firestore import FirestoreService
from app.services.mfa_service import mfa_service
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
    Expected payload: { 
        "idToken": "firebase_id_token",
        "sessionType": "explicit_login|session_restore|redirect_complete",
        "skipMFA": boolean (optional)
    }
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
        session_type = data.get('sessionType', 'explicit_login')
        skip_mfa = data.get('skipMFA', False)
        
        logger.info(f"Login attempt - UID: {uid}, Session: {session_type}, Skip MFA: {skip_mfa}")
        
        # Check if user exists in Firestore
        existing_user = db_service.get_document('users', uid)
        
        current_time = datetime.utcnow()
        
        if existing_user:
            # Check if MFA is enabled for this user
            user_mfa = db_service.get_document('user_mfa', uid)
            
            # Determine if MFA should be required
            mfa_enabled = user_mfa and user_mfa.get('enabled', False)
            should_require_mfa = (
                mfa_enabled and 
                not skip_mfa and 
                session_type == 'explicit_login'
            )
            
            if should_require_mfa:
                # MFA is enabled and required for this login
                mfa_token = mfa_service.create_mfa_session(uid)
                
                logger.info(f"MFA required for user {uid}")
                return jsonify({
                    'message': 'MFA verification required',
                    'mfa_required': True,
                    'mfa_token': mfa_token,
                    'recovery_codes_available': mfa_service.get_backup_codes_count(user_mfa) > 0
                }), 200
            
            # No MFA required, proceed with normal login
            # Update last login time
            db_service.update_document('users', uid, {
                'lastLoginAt': current_time
            })
            
            # Log activity
            activity_message = f'User logged in via {session_type}'
            db_service.log_user_activity(uid, 'LOGIN', activity_message)
            
            logger.info(f"Login successful for user {uid} via {session_type}")
            return jsonify({
                'message': 'Login successful',
                'user': existing_user,
                'isNewUser': False,
                'mfa_required': False
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
            
            logger.info(f"New user created: {uid}")
            return jsonify({
                'message': 'User created successfully',
                'user': new_user,
                'isNewUser': True,
                'mfa_required': False
            }), 201
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'error': 'Internal server error during login',
            'code': 'LOGIN_ERROR'
        }), 500

@auth_bp.route('/login/mfa', methods=['POST'])
def complete_mfa_login():
    """
    Complete login after MFA verification
    Expected payload: { 
        "mfa_token": "token", 
        "code": "123456", 
        "is_recovery_code": false 
    }
    """
    try:
        data = request.get_json()
        
        if not validate_required_fields(data, ['mfa_token', 'code']):
            return jsonify({
                'error': 'Missing required fields: mfa_token and code',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        mfa_token = data['mfa_token']
        verification_code = data['code']
        is_recovery_code = data.get('is_recovery_code', False)
        
        # Verify MFA session
        uid = mfa_service.verify_mfa_session(mfa_token)
        if not uid:
            return jsonify({
                'error': 'Invalid or expired MFA token',
                'code': 'INVALID_MFA_TOKEN'
            }), 400
        
        # Get user MFA data
        user_mfa = db_service.get_document('user_mfa', uid)
        if not user_mfa or not user_mfa.get('enabled', False):
            return jsonify({
                'error': 'MFA not enabled for this account',
                'code': 'MFA_NOT_ENABLED'
            }), 400
        
        verification_successful = False
        
        if is_recovery_code:
            # Verify recovery code
            for recovery_code in user_mfa.get('recovery_codes', []):
                if not recovery_code.get('used', False):
                    if mfa_service.verify_recovery_code(verification_code, recovery_code['hash']):
                        # Mark recovery code as used
                        user_mfa = mfa_service.mark_recovery_code_used(user_mfa, verification_code)
                        db_service.update_document('user_mfa', uid, user_mfa)
                        verification_successful = True
                        break
        else:
            # Verify TOTP code
            secret = mfa_service.decrypt_secret(user_mfa['secret'])
            verification_successful = mfa_service.verify_totp_code(secret, verification_code)
        
        if not verification_successful:
            # Log failed attempt
            db_service.log_user_activity(uid, 'MFA_FAILED', f'Failed MFA verification attempt')
            
            return jsonify({
                'error': 'Invalid verification code',
                'code': 'INVALID_MFA_CODE'
            }), 400
        
        # MFA verification successful
        # Get user profile
        user_profile = db_service.get_document('users', uid)
        if not user_profile:
            return jsonify({
                'error': 'User profile not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        # Update last login time
        db_service.update_document('users', uid, {
            'lastLoginAt': datetime.utcnow()
        })
        
        # Log successful MFA
        mfa_method = 'recovery_code' if is_recovery_code else 'totp'
        db_service.log_user_activity(uid, 'MFA_SUCCESS', f'Successful MFA verification via {mfa_method}')
        
        logger.info(f"MFA login successful for user {uid} via {mfa_method}")
        
        return jsonify({
            'message': 'MFA verification successful',
            'user': user_profile
        }), 200
        
    except Exception as e:
        logger.error(f"MFA login error: {str(e)}")
        return jsonify({
            'error': 'Internal server error during MFA verification',
            'code': 'MFA_LOGIN_ERROR'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@auth_required
def get_current_user():
    """Get current authenticated user profile"""
    try:
        uid = request.current_user['uid']
        
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
            'error': 'Internal server error',
            'code': 'GET_USER_ERROR'
        }), 500

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token without login"""
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
            'message': 'Token is valid',
            'user_info': user_info
        }), 200
        
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return jsonify({
            'error': 'Internal server error during token verification',
            'code': 'TOKEN_VERIFY_ERROR'
        }), 500