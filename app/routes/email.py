from flask import Blueprint, request, jsonify, make_response
import logging
from datetime import datetime
from app.middleware.auth_required import auth_required
from app.services.email_service import EmailService
from app.db.firestore import FirestoreService

logger = logging.getLogger(__name__)
email_bp = Blueprint('email', __name__)

email_service = EmailService()
db_service = FirestoreService()

@email_bp.route('/test-connection', methods=['GET', 'OPTIONS'])
def test_connection():
    """Test endpoint to verify API connectivity"""
    response = jsonify({
        'success': True,
        'message': 'Email API is working',
        'timestamp': datetime.utcnow().isoformat(),
        'cors_enabled': True
    })
    response.status_code = 200
    return response

@email_bp.route('/test', methods=['POST'])
@auth_required
def test_email_config():
    """Test email configuration and connectivity"""
    try:
        result = email_service.test_email_configuration()
        
        if result['config_valid'] and result['connection_successful']:
            return jsonify({
                'success': True,
                'message': 'Email configuration test successful',
                'details': result['details']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message'],
                'details': result['details']
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Email test failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Email test failed: {str(e)}'
        }), 500

@email_bp.route('/send-test', methods=['POST'])
@auth_required
def send_test_email():
    """Send a test email to verify functionality"""
    try:
        data = request.get_json()
        user_info = request.current_user
        
        # Use current user's email or provided email
        to_email = data.get('email', user_info.get('email'))
        
        if not to_email:
            return jsonify({
                'success': False,
                'message': 'Email address is required'
            }), 400
        
        # Send test email
        subject = "SkillBridge Email Test ✅"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #ffffff; padding: 30px; border-radius: 0 0 8px 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .success {{ background: #ecfdf5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Email Test Successful!</h1>
                </div>
                <div class="content">
                    <h2>Congratulations!</h2>
                    <p>If you're reading this email, it means your SkillBridge email service is working perfectly!</p>
                    
                    <div class="success">
                        <p><strong>🎯 Test Details:</strong></p>
                        <p>• Email service: Operational<br>
                        • SMTP connection: Successful<br>
                        • Template rendering: Working<br>
                        • Delivery: Confirmed</p>
                    </div>
                    
                    <p>Your email notifications for welcome messages, roadmap updates, and progress summaries are now ready to go!</p>
                    
                    <p>Best regards,<br><strong>The SkillBridge Team</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        success = email_service.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            priority='high'
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {to_email}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send test email'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Test email send failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Test email failed: {str(e)}'
        }), 500

@email_bp.route('/send-welcome', methods=['POST'])
@auth_required
def send_welcome_email():
    """Send welcome email to user"""
    try:
        user_info = request.current_user
        user_email = user_info.get('email')
        user_name = user_info.get('name', 'User')
        
        if not user_email:
            return jsonify({
                'success': False,
                'message': 'User email not found'
            }), 400
        
        success = email_service.send_welcome_email(user_email, user_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Welcome email sent successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send welcome email'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Welcome email send failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Welcome email failed: {str(e)}'
        }), 500

@email_bp.route('/feedback', methods=['POST', 'OPTIONS'])
@auth_required
def send_feedback_email():
    """Send feedback email to support team"""
    try:
        data = request.get_json()
        user_info = request.current_user
        
        user_email = user_info.get('email')
        user_name = user_info.get('name', 'User')
        feedback_type = data.get('type', 'General')
        message = data.get('message', '')
        
        if not message.strip():
            return jsonify({
                'success': False,
                'message': 'Feedback message is required'
            }), 400
        
        success = email_service.send_feedback_email(
            user_email=user_email,
            user_name=user_name,
            feedback_type=feedback_type,
            message=message
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Feedback sent successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send feedback'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Feedback email send failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Feedback email failed: {str(e)}'
        }), 500

@email_bp.route('/templates', methods=['GET'])
@auth_required
def get_email_templates():
    """Get available email templates"""
    try:
        templates = {
            'welcome': {
                'name': 'Welcome Email',
                'description': 'Sent to new users when they sign up',
                'variables': ['user_name']
            },
            'roadmap_generated': {
                'name': 'Roadmap Generated',
                'description': 'Sent when AI generates a learning roadmap',
                'variables': ['user_name', 'role_title', 'milestone_count']
            },
            'weekly_progress': {
                'name': 'Weekly Progress',
                'description': 'Weekly summary of learning progress',
                'variables': ['user_name', 'skills_added', 'resources_completed', 'roadmap_progress']
            },
            'feedback_confirmation': {
                'name': 'Feedback Confirmation',
                'description': 'Confirmation when user submits feedback',
                'variables': ['user_name', 'feedback_type']
            }
        }
        
        return jsonify({
            'success': True,
            'templates': templates
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Get templates failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get templates: {str(e)}'
        }), 500

@email_bp.route('/stats', methods=['GET'])
@auth_required
def get_email_stats():
    """Get email service statistics"""
    try:
        # This would typically come from database logs
        # For now, return mock data
        stats = {
            'emails_sent_today': 0,
            'emails_sent_this_week': 0,
            'emails_sent_this_month': 0,
            'success_rate': 100.0,
            'last_email_sent': None,
            'rate_limit_status': {
                'current_count': len(email_service.email_timestamps),
                'limit': email_service.rate_limit,
                'window_seconds': email_service.rate_window
            }
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Get email stats failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get email stats: {str(e)}'
        }), 500