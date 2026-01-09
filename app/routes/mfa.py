from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.db.firestore import FirestoreService
from app.services.mfa_service import mfa_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
mfa_bp = Blueprint('mfa', __name__)
db_service = FirestoreService()

@mfa_bp.route('/setup', methods=['POST'])
@auth_required
def setup_mfa():
    """
    Setup MFA for user account
    Returns QR code and recovery codes
    """
    try:
        uid = request.current_user['uid']
        user_email = request.current_user.get('email', 'user@example.com')
        
        # Check if MFA is already enabled
        user_mfa = db_service.get_document('user_mfa', uid)
        if user_mfa and user_mfa.get('enabled', False):
            return jsonify({
                'error': 'MFA is already enabled for this account',
                'code': 'MFA_ALREADY_ENABLED'
            }), 400
        
        # Generate new secret
        secret = mfa_service.generate_secret()
        encrypted_secret = mfa_service.encrypt_secret(secret)
        
        # Generate QR code
        qr_code = mfa_service.generate_qr_code(user_email, secret)
        
        # Generate recovery codes
        recovery_codes = mfa_service.generate_recovery_codes()
        hashed_recovery_codes = [
            {
                'hash': mfa_service.hash_recovery_code(code),
                'used': False,
                'created_at': datetime.utcnow().isoformat()
            }
            for code in recovery_codes
        ]
        
        # Store MFA data (but don't enable yet - user needs to verify)
        mfa_data = {
            'uid': uid,
            'secret': encrypted_secret,
            'enabled': False,  # Will be enabled after verification
            'setup_completed': False,
            'recovery_codes': hashed_recovery_codes,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        success = db_service.create_document('user_mfa', uid, mfa_data)
        
        if not success:
            return jsonify({
                'error': 'Failed to setup MFA',
                'code': 'MFA_SETUP_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'MFA_SETUP_INITIATED', 'User initiated MFA setup')
        
        return jsonify({
            'message': 'MFA setup initiated successfully',
            'qr_code': qr_code,
            'recovery_codes': recovery_codes,  # Return plain codes for user to save
            'setup_token': mfa_service.create_mfa_session(uid)
        }), 200
        
    except Exception as e:
        logger.error(f"MFA setup error: {str(e)}")
        return jsonify({
            'error': 'Failed to setup MFA',
            'code': 'MFA_SETUP_ERROR'
        }), 500

@mfa_bp.route('/verify-setup', methods=['POST'])
def verify_mfa_setup():
    """
    Verify MFA setup with TOTP code
    Enables MFA after successful verification
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('setup_token') or not data.get('totp_code'):
            return jsonify({
                'error': 'Setup token and TOTP code are required',
                'code': 'MISSING_REQUIRED_FIELDS'
            }), 400
        
        setup_token = data['setup_token']
        totp_code = data['totp_code']
        
        # Verify setup session
        uid = mfa_service.verify_mfa_session(setup_token)
        if not uid:
            return jsonify({
                'error': 'Invalid or expired setup token',
                'code': 'INVALID_SETUP_TOKEN'
            }), 400
        
        # Get user MFA data
        user_mfa = db_service.get_document('user_mfa', uid)
        if not user_mfa:
            return jsonify({
                'error': 'MFA setup not found',
                'code': 'MFA_SETUP_NOT_FOUND'
            }), 404
        
        # Decrypt secret and verify TOTP code
        secret = mfa_service.decrypt_secret(user_mfa['secret'])
        if not mfa_service.verify_totp_code(secret, totp_code):
            return jsonify({
                'error': 'Invalid TOTP code',
                'code': 'INVALID_TOTP_CODE'
            }), 400
        
        # Enable MFA
        user_mfa['enabled'] = True
        user_mfa['setup_completed'] = True
        user_mfa['verified_at'] = datetime.utcnow().isoformat()
        user_mfa['updated_at'] = datetime.utcnow().isoformat()
        
        success = db_service.update_document('user_mfa', uid, user_mfa)
        
        if not success:
            return jsonify({
                'error': 'Failed to enable MFA',
                'code': 'MFA_ENABLE_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'MFA_ENABLED', 'MFA successfully enabled for account')
        
        return jsonify({
            'message': 'MFA enabled successfully',
            'enabled': True
        }), 200
        
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}")
        return jsonify({
            'error': 'Failed to verify MFA setup',
            'code': 'MFA_VERIFICATION_ERROR'
        }), 500

@mfa_bp.route('/verify', methods=['POST'])
def verify_mfa():
    """
    Verify MFA code during login
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('mfa_token') or not data.get('code'):
            return jsonify({
                'error': 'MFA token and code are required',
                'code': 'MISSING_REQUIRED_FIELDS'
            }), 400
        
        mfa_token = data['mfa_token']
        code = data['code']
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
                    if mfa_service.verify_recovery_code(code, recovery_code['hash']):
                        # Mark recovery code as used
                        user_mfa = mfa_service.mark_recovery_code_used(user_mfa, code)
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
            verification_successful = mfa_service.verify_totp_code(secret, code)
        
        if not verification_successful:
            # Log failed attempt
            db_service.log_user_activity(uid, 'MFA_VERIFICATION_FAILED', f'Failed MFA verification attempt')
            
            return jsonify({
                'error': 'Invalid verification code',
                'code': 'INVALID_VERIFICATION_CODE'
            }), 400
        
        # Log successful verification
        db_service.log_user_activity(uid, 'MFA_VERIFICATION_SUCCESS', 'MFA verification successful')
        
        # Get remaining recovery codes count
        remaining_codes = mfa_service.get_backup_codes_count(user_mfa)
        
        return jsonify({
            'message': 'MFA verification successful',
            'verified': True,
            'remaining_recovery_codes': remaining_codes
        }), 200
        
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}")
        return jsonify({
            'error': 'Failed to verify MFA',
            'code': 'MFA_VERIFICATION_ERROR'
        }), 500

@mfa_bp.route('/status', methods=['GET'])
@auth_required
def get_mfa_status():
    """
    Get MFA status for current user
    """
    try:
        uid = request.current_user['uid']
        
        user_mfa = db_service.get_document('user_mfa', uid)
        
        if not user_mfa:
            return jsonify({
                'enabled': False,
                'setup_required': True,
                'recovery_codes_count': 0
            }), 200
        
        recovery_codes_count = mfa_service.get_backup_codes_count(user_mfa)
        
        return jsonify({
            'enabled': user_mfa.get('enabled', False),
            'setup_required': not user_mfa.get('setup_completed', False),
            'recovery_codes_count': recovery_codes_count,
            'setup_date': user_mfa.get('verified_at'),
            'last_used': user_mfa.get('last_used_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Get MFA status error: {str(e)}")
        return jsonify({
            'error': 'Failed to get MFA status',
            'code': 'MFA_STATUS_ERROR'
        }), 500

@mfa_bp.route('/disable', methods=['POST'])
@auth_required
def disable_mfa():
    """
    Disable MFA for user account
    Requires current password or recovery code
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not data or not data.get('verification_code'):
            return jsonify({
                'error': 'Verification code is required to disable MFA',
                'code': 'MISSING_VERIFICATION_CODE'
            }), 400
        
        verification_code = data['verification_code']
        is_recovery_code = data.get('is_recovery_code', False)
        
        # Get user MFA data
        user_mfa = db_service.get_document('user_mfa', uid)
        if not user_mfa or not user_mfa.get('enabled', False):
            return jsonify({
                'error': 'MFA is not enabled for this account',
                'code': 'MFA_NOT_ENABLED'
            }), 400
        
        # Verify the code before disabling
        verification_successful = False
        
        if is_recovery_code:
            # Verify recovery code
            for recovery_code in user_mfa.get('recovery_codes', []):
                if not recovery_code.get('used', False):
                    if mfa_service.verify_recovery_code(verification_code, recovery_code['hash']):
                        verification_successful = True
                        break
        else:
            # Verify TOTP code
            secret = mfa_service.decrypt_secret(user_mfa['secret'])
            verification_successful = mfa_service.verify_totp_code(secret, verification_code)
        
        if not verification_successful:
            return jsonify({
                'error': 'Invalid verification code',
                'code': 'INVALID_VERIFICATION_CODE'
            }), 400
        
        # Disable MFA
        user_mfa['enabled'] = False
        user_mfa['disabled_at'] = datetime.utcnow().isoformat()
        user_mfa['updated_at'] = datetime.utcnow().isoformat()
        
        success = db_service.update_document('user_mfa', uid, user_mfa)
        
        if not success:
            return jsonify({
                'error': 'Failed to disable MFA',
                'code': 'MFA_DISABLE_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'MFA_DISABLED', 'MFA disabled for account')
        
        return jsonify({
            'message': 'MFA disabled successfully',
            'enabled': False
        }), 200
        
    except Exception as e:
        logger.error(f"MFA disable error: {str(e)}")
        return jsonify({
            'error': 'Failed to disable MFA',
            'code': 'MFA_DISABLE_ERROR'
        }), 500

@mfa_bp.route('/regenerate-recovery-codes', methods=['POST'])
@auth_required
def regenerate_recovery_codes():
    """
    Regenerate recovery codes for user
    Requires TOTP verification
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not data or not data.get('totp_code'):
            return jsonify({
                'error': 'TOTP code is required',
                'code': 'MISSING_TOTP_CODE'
            }), 400
        
        totp_code = data['totp_code']
        
        # Get user MFA data
        user_mfa = db_service.get_document('user_mfa', uid)
        if not user_mfa or not user_mfa.get('enabled', False):
            return jsonify({
                'error': 'MFA is not enabled for this account',
                'code': 'MFA_NOT_ENABLED'
            }), 400
        
        # Verify TOTP code
        secret = mfa_service.decrypt_secret(user_mfa['secret'])
        if not mfa_service.verify_totp_code(secret, totp_code):
            return jsonify({
                'error': 'Invalid TOTP code',
                'code': 'INVALID_TOTP_CODE'
            }), 400
        
        # Generate new recovery codes
        recovery_codes = mfa_service.generate_recovery_codes()
        hashed_recovery_codes = [
            {
                'hash': mfa_service.hash_recovery_code(code),
                'used': False,
                'created_at': datetime.utcnow().isoformat()
            }
            for code in recovery_codes
        ]
        
        # Update MFA data
        user_mfa['recovery_codes'] = hashed_recovery_codes
        user_mfa['recovery_codes_regenerated_at'] = datetime.utcnow().isoformat()
        user_mfa['updated_at'] = datetime.utcnow().isoformat()
        
        success = db_service.update_document('user_mfa', uid, user_mfa)
        
        if not success:
            return jsonify({
                'error': 'Failed to regenerate recovery codes',
                'code': 'RECOVERY_CODES_REGENERATION_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'MFA_RECOVERY_CODES_REGENERATED', 'Recovery codes regenerated')
        
        return jsonify({
            'message': 'Recovery codes regenerated successfully',
            'recovery_codes': recovery_codes
        }), 200
        
    except Exception as e:
        logger.error(f"Regenerate recovery codes error: {str(e)}")
        return jsonify({
            'error': 'Failed to regenerate recovery codes',
            'code': 'RECOVERY_CODES_ERROR'
        }), 500