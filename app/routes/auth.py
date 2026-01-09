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
            # Check if MFA is enabled for this user
            user_mfa = db_service.get_document('user_mfa', uid)
            
            if user_mfa and user_mfa.get('enabled', False):
                # MFA is enabled, require MFA verification
                mfa_token = mfa_service.create_mfa_session(uid)
                
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
            db_service.log_user_activity(uid, 'LOGIN', 'User logged in')
            
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
    Expected payload: { "mfa_token": "token", "code": "123456", "is_recovery_code": false }
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
                        user_mfa['updated_at'] = datetime.utcnow().isoformat()
                        
                        # Update in database
                        db_service.update_document('user_mfa', uid, user_mfa)
                        
                        verification_successful = True
                        
                        # Log recovery code usage
                        db_service.log_user_activity(uid, 'MFA_RECOVERY_CODE_USED', 'Recovery code used for login')
                        break
        else:
            # Verify TOTP code
            secret = mfa_service.decrypt_secret(user_mfa['secret'])
            verification_successful = mfa_service.verify_totp_code(secret, verification_code)
        
        if not verification_successful:
            # Log failed attempt
            db_service.log_user_activity(uid, 'MFA_LOGIN_FAILED', f'Failed MFA login attempt')
            
            return jsonify({
                'error': 'Invalid verification code',
                'code': 'INVALID_VERIFICATION_CODE'
            }), 400
        
        # MFA verification successful, complete login
        user_profile = db_service.get_document('users', uid)
        if not user_profile:
            return jsonify({
                'error': 'User profile not found',
                'code': 'USER_NOT_FOUND'
            }), 404
        
        # Update last login time and MFA usage
        current_time = datetime.utcnow()
        db_service.update_document('users', uid, {
            'lastLoginAt': current_time
        })
        
        user_mfa['last_used_at'] = current_time.isoformat()
        db_service.update_document('user_mfa', uid, user_mfa)
        
        # Log successful login
        db_service.log_user_activity(uid, 'LOGIN_MFA_SUCCESS', 'User logged in with MFA')
        
        # Get remaining recovery codes count
        remaining_codes = mfa_service.get_backup_codes_count(user_mfa)
        
        return jsonify({
            'message': 'Login successful',
            'user': user_profile,
            'isNewUser': False,
            'mfa_verified': True,
            'remaining_recovery_codes': remaining_codes
        }), 200
        
    except Exception as e:
        logger.error(f"MFA login error: {str(e)}")
        return jsonify({
            'error': 'Internal server error during MFA login',
            'code': 'MFA_LOGIN_ERROR'
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