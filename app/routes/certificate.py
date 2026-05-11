from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required
from app.services.certificate_service import CertificateService
import logging

logger = logging.getLogger(__name__)
certificate_bp = Blueprint('certificate', __name__)
cert_service = CertificateService()

@certificate_bp.route('/verify', methods=['POST'])
@auth_required
def verify_and_issue():
    """
    Verify roadmap completion and issue a certificate
    Expected payload: { "roleId": "string" }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not data or 'roleId' not in data:
            return jsonify({
                'error': 'Missing required field: roleId',
                'code': 'VALIDATION_ERROR'
            }), 400
            
        role_id = data['roleId']
        certificate = cert_service.verify_and_issue_certificate(uid, role_id)
        
        if not certificate:
            return jsonify({
                'error': 'Roadmap not complete or verification failed',
                'code': 'VERIFICATION_FAILED'
            }), 400
            
        return jsonify(certificate), 200
        
    except Exception as e:
        logger.error(f"Certificate verification error: {str(e)}")
        return jsonify({
            'error': 'Failed to verify certificate',
            'code': 'CERTIFICATE_ERROR'
        }), 500

@certificate_bp.route('/user', methods=['GET'])
@auth_required
def get_user_certificates():
    """Get all certificates issued to the authenticated user"""
    try:
        uid = request.current_user['uid']
        certificates = cert_service.get_user_certificates(uid)
        return jsonify(certificates), 200
    except Exception as e:
        logger.error(f"Error fetching user certificates: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch certificates',
            'code': 'FETCH_ERROR'
        }), 500

@certificate_bp.route('/<cert_id>', methods=['GET'])
def get_certificate(cert_id):
    """Public route to verify certificate authenticity"""
    try:
        certificate = cert_service.get_certificate_by_id(cert_id)
        if not certificate:
            return jsonify({
                'error': 'Certificate not found',
                'code': 'NOT_FOUND'
            }), 404
            
        return jsonify(certificate), 200
    except Exception as e:
        logger.error(f"Error fetching certificate {cert_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch certificate',
            'code': 'FETCH_ERROR'
        }), 500
