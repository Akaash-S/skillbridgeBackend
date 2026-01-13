import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import json
import os

from app.config import Config
from app.db.firestore import FirestoreService

logger = logging.getLogger(__name__)

@dataclass
class EmailTemplate:
    """Email template data structure"""
    subject: str
    html_content: str
    text_content: Optional[str] = None
    variables: Optional[List[str]] = None

class EmailService:
    """Enhanced email service with multiple provider support and advanced features"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        self.smtp_host = Config.SMTP_HOST
        self.smtp_port = Config.SMTP_PORT
        self.smtp_user = Config.SMTP_USER
        self.smtp_password = Config.SMTP_PASSWORD
        self.from_email = Config.SMTP_USER
        self.from_name = "SkillBridge Suite"
        
        # Rate limiting: max 10 emails per minute
        self.rate_limit = 10
        self.rate_window = 60  # seconds
        self.email_timestamps = []
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Validate configuration on initialization
        self._validate_config()
        
    def _validate_config(self) -> bool:
        """Validate email configuration"""
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.warning("⚠️ SMTP configuration incomplete. Email functionality will be disabled.")
            logger.warning(f"SMTP Host: {'✓' if self.smtp_host else '✗'}")
            logger.warning(f"SMTP User: {'✓' if self.smtp_user else '✗'}")
            logger.warning(f"SMTP Password: {'✓' if self.smtp_password else '✗'}")
            return False
        
        logger.info("✅ Email service configuration validated successfully")
        return True
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = time.time()
        # Remove timestamps older than the rate window
        self.email_timestamps = [ts for ts in self.email_timestamps if now - ts < self.rate_window]
        
        if len(self.email_timestamps) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded: {len(self.email_timestamps)} emails in last {self.rate_window}s")
            return False
        
        return True
    
    def _record_email_sent(self):
        """Record timestamp of sent email for rate limiting"""
        self.email_timestamps.append(time.time())
    
    def _create_smtp_connection(self):
        """Create and configure SMTP connection with proper security"""
        try:
            # Create SMTP connection with timeout
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            
            # Enable debug mode in development
            if Config.FLASK_ENV == 'development':
                server.set_debuglevel(1)
            
            # Start TLS encryption
            context = ssl.create_default_context()
            server.starttls(context=context)
            
            # Login to server
            server.login(self.smtp_user, self.smtp_password)
            
            return server
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {str(e)}")
            logger.error("💡 Check your email credentials and app password settings")
            raise
        except smtplib.SMTPConnectError as e:
            logger.error(f"❌ SMTP Connection failed: {str(e)}")
            logger.error("💡 Check your SMTP host and port settings")
            raise
        except Exception as e:
            logger.error(f"❌ SMTP setup failed: {str(e)}")
            raise
    
    def send_email(self, 
                   to_email: Union[str, List[str]], 
                   subject: str, 
                   html_content: str, 
                   text_content: Optional[str] = None,
                   attachments: Optional[List[Dict]] = None,
                   priority: str = 'normal') -> bool:
        """
        Send email with enhanced features
        
        Args:
            to_email: Recipient email(s) - string or list of strings
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text content (optional)
            attachments: List of attachment dicts with 'filename' and 'content' keys
            priority: Email priority ('high', 'normal', 'low')
        """
        try:
            # Validate configuration
            if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
                logger.warning("📧 SMTP configuration incomplete, skipping email send")
                return False
            
            # Check rate limits
            if not self._check_rate_limit():
                logger.warning("📧 Rate limit exceeded, email not sent")
                return False
            
            # Normalize recipient list
            recipients = [to_email] if isinstance(to_email, str) else to_email
            
            # Validate recipients
            for email in recipients:
                if not self._validate_email_format(email):
                    logger.error(f"❌ Invalid email format: {email}")
                    return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = ', '.join(recipients)
            
            # Set priority
            if priority == 'high':
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            elif priority == 'low':
                msg['X-Priority'] = '5'
                msg['X-MSMail-Priority'] = 'Low'
            
            # Add custom headers
            msg['X-Mailer'] = 'SkillBridge Suite Email Service'
            msg['Message-ID'] = f"<{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{hash(subject)}@skillbridge.app>"
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email with retry logic
            success = self._send_with_retry(msg, recipients)
            
            if success:
                self._record_email_sent()
                logger.info(f"✅ Email sent successfully to {', '.join(recipients)}")
                
                # Log email activity to database
                self._log_email_activity(recipients, subject, 'sent')
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {str(e)}")
            self._log_email_activity(recipients if 'recipients' in locals() else [to_email], subject, 'failed', str(e))
            return False
    
    def _send_with_retry(self, msg: MIMEMultipart, recipients: List[str]) -> bool:
        """Send email with retry logic"""
        for attempt in range(self.max_retries):
            try:
                with self._create_smtp_connection() as server:
                    server.send_message(msg, to_addrs=recipients)
                return True
                
            except Exception as e:
                logger.warning(f"📧 Email send attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"❌ All {self.max_retries} email send attempts failed")
                    return False
        
        return False
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict):
        """Add attachment to email message"""
        try:
            filename = attachment.get('filename', 'attachment')
            content = attachment.get('content', b'')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"❌ Failed to add attachment {filename}: {str(e)}")
    
    def _validate_email_format(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _log_email_activity(self, recipients: List[str], subject: str, status: str, error: Optional[str] = None):
        """Log email activity to database"""
        try:
            activity_data = {
                'recipients': recipients,
                'subject': subject,
                'status': status,
                'timestamp': datetime.utcnow().isoformat(),
                'from_email': self.from_email,
                'error': error
            }
            
            # Store in Firestore (optional - only if database is available)
            if hasattr(self.db_service, 'add_document'):
                self.db_service.add_document('email_logs', activity_data)
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to log email activity: {str(e)}")
    
    def get_email_template(self, template_name: str) -> Optional[EmailTemplate]:
        """Get email template by name"""
        templates = {
            'welcome': EmailTemplate(
                subject="Welcome to SkillBridge Suite! 🚀",
                html_content=self._get_welcome_template(),
                variables=['user_name']
            ),
            'roadmap_generated': EmailTemplate(
                subject="Your {role_title} Learning Roadmap is Ready! 🎯",
                html_content=self._get_roadmap_template(),
                variables=['user_name', 'role_title', 'milestone_count']
            ),
            'weekly_progress': EmailTemplate(
                subject="Your Weekly Progress Summary 📊",
                html_content=self._get_progress_template(),
                variables=['user_name', 'skills_added', 'resources_completed', 'roadmap_progress']
            ),
            'feedback_confirmation': EmailTemplate(
                subject="We received your feedback - SkillBridge Support",
                html_content=self._get_feedback_confirmation_template(),
                variables=['user_name', 'feedback_type']
            )
        }
        
        return templates.get(template_name)
    
    def send_templated_email(self, 
                           to_email: Union[str, List[str]], 
                           template_name: str, 
                           variables: Dict[str, str],
                           priority: str = 'normal') -> bool:
        """Send email using predefined template"""
        try:
            template = self.get_email_template(template_name)
            if not template:
                logger.error(f"❌ Email template '{template_name}' not found")
                return False
            
            # Replace variables in subject and content
            subject = template.subject.format(**variables)
            html_content = template.html_content.format(**variables)
            text_content = template.text_content.format(**variables) if template.text_content else None
            
            return self.send_email(to_email, subject, html_content, text_content, priority=priority)
            
        except KeyError as e:
            logger.error(f"❌ Missing template variable: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send templated email: {str(e)}")
            return False
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new users"""
        try:
            subject = "Welcome to SkillBridge Suite! 🚀"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .features {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .feature {{ margin: 15px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to SkillBridge Suite!</h1>
                        <p>Your AI-powered career development journey starts here</p>
                    </div>
                    <div class="content">
                        <h2>Hi {user_name}! 👋</h2>
                        <p>Welcome to SkillBridge Suite! We're excited to help you accelerate your tech career with AI-powered insights and personalized learning paths.</p>
                        
                        <div class="features">
                            <h3>What you can do with SkillBridge:</h3>
                            <div class="feature">🎯 <strong>Smart Skill Analysis</strong> - Track your technical skills and get AI-powered gap analysis</div>
                            <div class="feature">🗺️ <strong>Personalized Roadmaps</strong> - Get custom learning paths generated by AI for your career goals</div>
                            <div class="feature">💼 <strong>Job Matching</strong> - Discover opportunities that match your skills and aspirations</div>
                            <div class="feature">📚 <strong>Curated Resources</strong> - Access hand-picked learning materials for every skill level</div>
                            <div class="feature">📊 <strong>Progress Tracking</strong> - Monitor your growth with detailed analytics and insights</div>
                        </div>
                        
                        <p>Ready to get started? Complete your profile and add your first skills to unlock personalized recommendations!</p>
                        
                        <a href="https://skillbridge.app/onboarding" class="button">Complete Your Profile</a>
                        
                        <p>If you have any questions, feel free to reach out to our support team. We're here to help you succeed!</p>
                        
                        <p>Best regards,<br>The SkillBridge Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 SkillBridge Suite. All rights reserved.</p>
                        <p>You received this email because you signed up for SkillBridge Suite.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Welcome to SkillBridge Suite!
            
            Hi {user_name}!
            
            Welcome to SkillBridge Suite! We're excited to help you accelerate your tech career with AI-powered insights and personalized learning paths.
            
            What you can do with SkillBridge:
            • Smart Skill Analysis - Track your technical skills and get AI-powered gap analysis
            • Personalized Roadmaps - Get custom learning paths generated by AI for your career goals
            • Job Matching - Discover opportunities that match your skills and aspirations
            • Curated Resources - Access hand-picked learning materials for every skill level
            • Progress Tracking - Monitor your growth with detailed analytics and insights
            
            Ready to get started? Complete your profile and add your first skills to unlock personalized recommendations!
            
            Visit: https://skillbridge.app/onboarding
            
            If you have any questions, feel free to reach out to our support team. We're here to help you succeed!
            
            Best regards,
            The SkillBridge Team
            
            © 2024 SkillBridge Suite. All rights reserved.
            """
            
            return self.send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            return False
    
    def send_roadmap_generated_email(self, user_email: str, user_name: str, role_title: str, milestone_count: int) -> bool:
        """Send notification when AI roadmap is generated"""
        try:
            subject = f"Your {role_title} Learning Roadmap is Ready! 🎯"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .stats {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 Your Roadmap is Ready!</h1>
                        <p>AI-generated learning path for {role_title}</p>
                    </div>
                    <div class="content">
                        <h2>Hi {user_name}!</h2>
                        <p>Great news! Your personalized learning roadmap for <strong>{role_title}</strong> has been generated using our AI engine.</p>
                        
                        <div class="stats">
                            <h3>Your Roadmap Includes:</h3>
                            <p><strong>{milestone_count} Learning Milestones</strong></p>
                            <p>Curated resources, skill progression, and estimated timelines</p>
                        </div>
                        
                        <p>Your roadmap is tailored to your current skills and experience level, providing a clear path to achieve your career goals.</p>
                        
                        <a href="https://skillbridge.app/roadmap" class="button">View Your Roadmap</a>
                        
                        <p>Start learning today and track your progress as you advance toward your {role_title} goals!</p>
                        
                        <p>Happy learning!<br>The SkillBridge Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 SkillBridge Suite. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self.send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send roadmap generated email: {str(e)}")
            return False
    
    def send_feedback_email(self, user_email: str, user_name: str, feedback_type: str, message: str) -> bool:
        """Send feedback/query email to support team"""
        try:
            subject = f"SkillBridge Feedback: {feedback_type} from {user_name}"
            
            # Send to support team (using same SMTP for simplicity)
            support_email = self.from_email  # In production, use dedicated support email
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #f59e0b; color: white; padding: 20px; text-align: center; }}
                    .content {{ background: #f9f9f9; padding: 30px; }}
                    .user-info {{ background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                    .message {{ background: white; padding: 20px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #f59e0b; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>New Feedback Received</h1>
                        <p>Type: {feedback_type}</p>
                    </div>
                    <div class="content">
                        <div class="user-info">
                            <h3>User Information:</h3>
                            <p><strong>Name:</strong> {user_name}</p>
                            <p><strong>Email:</strong> {user_email}</p>
                            <p><strong>Feedback Type:</strong> {feedback_type}</p>
                            <p><strong>Submitted:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                        </div>
                        
                        <div class="message">
                            <h3>Message:</h3>
                            <p>{message}</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send to support team
            success = self.send_email(support_email, subject, html_content)
            
            if success:
                # Send confirmation to user
                self._send_feedback_confirmation(user_email, user_name, feedback_type)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send feedback email: {str(e)}")
            return False
    
    def _send_feedback_confirmation(self, user_email: str, user_name: str, feedback_type: str) -> bool:
        """Send feedback confirmation to user"""
        try:
            subject = "We received your feedback - SkillBridge Support"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #10b981; color: white; padding: 20px; text-align: center; }}
                    .content {{ background: #f9f9f9; padding: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Thank You for Your Feedback!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {user_name}!</h2>
                        <p>Thank you for reaching out to us regarding: <strong>{feedback_type}</strong></p>
                        
                        <p>We've received your message and our team will review it carefully. If your inquiry requires a response, we'll get back to you within 24-48 hours.</p>
                        
                        <p>Your feedback helps us improve SkillBridge Suite for everyone. We appreciate you taking the time to share your thoughts with us.</p>
                        
                        <p>Best regards,<br>SkillBridge Support Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self.send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send feedback confirmation: {str(e)}")
            return False
    
    def send_weekly_progress_email(self, user_email: str, user_name: str, progress_data: Dict) -> bool:
        """Send weekly progress summary email"""
        try:
            subject = "Your Weekly Progress Summary 📊"
            
            skills_added = progress_data.get('skillsAdded', 0)
            resources_completed = progress_data.get('resourcesCompleted', 0)
            roadmap_progress = progress_data.get('roadmapProgress', 0)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ background: #f9f9f9; padding: 30px; }}
                    .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                    .stat {{ background: white; padding: 20px; border-radius: 5px; text-align: center; flex: 1; margin: 0 10px; }}
                    .stat h3 {{ color: #667eea; margin: 0; font-size: 2em; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 Weekly Progress Summary</h1>
                        <p>Your learning journey this week</p>
                    </div>
                    <div class="content">
                        <h2>Hi {user_name}!</h2>
                        <p>Here's a summary of your progress this week on SkillBridge Suite:</p>
                        
                        <div class="stats">
                            <div class="stat">
                                <h3>{skills_added}</h3>
                                <p>Skills Added</p>
                            </div>
                            <div class="stat">
                                <h3>{resources_completed}</h3>
                                <p>Resources Completed</p>
                            </div>
                            <div class="stat">
                                <h3>{roadmap_progress}%</h3>
                                <p>Roadmap Progress</p>
                            </div>
                        </div>
                        
                        <p>Keep up the great work! Consistent learning is the key to achieving your career goals.</p>
                        
                        <a href="https://skillbridge.app/dashboard" class="button">View Full Dashboard</a>
                        
                        <p>Ready for next week? Check out your personalized recommendations and continue your learning journey!</p>
                        
                        <p>Best regards,<br>The SkillBridge Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self.send_email(user_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send weekly progress email: {str(e)}")
            return False
    
    def _get_welcome_template(self) -> str:
        """Get welcome email HTML template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0 0 10px 0; font-size: 28px; font-weight: 700; }}
                .header p {{ margin: 0; font-size: 16px; opacity: 0.9; }}
                .content {{ background: #ffffff; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .content h2 {{ color: #333; margin: 0 0 20px 0; font-size: 24px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; margin: 25px 0; font-weight: 600; transition: transform 0.2s; }}
                .button:hover {{ transform: translateY(-2px); }}
                .features {{ background: #f8fafc; padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #667eea; }}
                .features h3 {{ color: #333; margin: 0 0 15px 0; font-size: 18px; }}
                .feature {{ margin: 12px 0; padding: 8px 0; }}
                .feature strong {{ color: #667eea; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 14px; }}
                .social {{ margin: 20px 0; }}
                .social a {{ display: inline-block; margin: 0 10px; color: #667eea; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Welcome to SkillBridge Suite!</h1>
                    <p>Your AI-powered career development journey starts here</p>
                </div>
                <div class="content">
                    <h2>Hi {user_name}! 👋</h2>
                    <p>Welcome to SkillBridge Suite! We're thrilled to have you join our community of ambitious professionals who are taking control of their career growth.</p>
                    
                    <div class="features">
                        <h3>🎯 What you can achieve with SkillBridge:</h3>
                        <div class="feature">🧠 <strong>AI-Powered Skill Analysis</strong> - Get intelligent insights into your technical skills and career readiness</div>
                        <div class="feature">🗺️ <strong>Personalized Learning Roadmaps</strong> - Receive custom learning paths tailored to your goals and experience</div>
                        <div class="feature">💼 <strong>Smart Job Matching</strong> - Discover opportunities that align perfectly with your skills and aspirations</div>
                        <div class="feature">📚 <strong>Curated Learning Resources</strong> - Access premium courses, tutorials, and materials for every skill level</div>
                        <div class="feature">📊 <strong>Advanced Progress Tracking</strong> - Monitor your growth with detailed analytics and achievement milestones</div>
                        <div class="feature">🏆 <strong>Skill Certifications</strong> - Earn verified certificates to showcase your expertise</div>
                    </div>
                    
                    <p>Ready to accelerate your career? Let's start by setting up your profile and adding your first skills!</p>
                    
                    <div style="text-align: center;">
                        <a href="https://skillbridge.app/onboarding" class="button">🚀 Complete Your Profile</a>
                    </div>
                    
                    <p>Need help getting started? Our support team is here to assist you every step of the way. Simply reply to this email with any questions!</p>
                    
                    <p>Welcome aboard! 🎉<br><strong>The SkillBridge Team</strong></p>
                </div>
                <div class="footer">
                    <div class="social">
                        <a href="https://skillbridge.app">🌐 Website</a>
                        <a href="https://skillbridge.app/help">❓ Help Center</a>
                        <a href="https://skillbridge.app/community">👥 Community</a>
                    </div>
                    <p>© 2024 SkillBridge Suite. All rights reserved.</p>
                    <p>You received this email because you signed up for SkillBridge Suite.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_roadmap_template(self) -> str:
        """Get roadmap generated email HTML template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }}
                .content {{ background: #ffffff; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; margin: 25px 0; font-weight: 600; }}
                .stats {{ background: #ecfdf5; padding: 25px; border-radius: 8px; margin: 25px 0; text-align: center; border: 2px solid #10b981; }}
                .stats h3 {{ color: #059669; margin: 0 0 15px 0; }}
                .milestone-count {{ font-size: 48px; font-weight: bold; color: #10b981; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #64748b; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Your Roadmap is Ready!</h1>
                    <p>AI-generated learning path for {role_title}</p>
                </div>
                <div class="content">
                    <h2>Congratulations, {user_name}! 🎉</h2>
                    <p>Your personalized learning roadmap for <strong>{role_title}</strong> has been generated using our advanced AI engine. This roadmap is specifically tailored to your current skills and career goals.</p>
                    
                    <div class="stats">
                        <h3>📋 Your Roadmap Includes:</h3>
                        <div class="milestone-count">{milestone_count}</div>
                        <p><strong>Learning Milestones</strong></p>
                        <p>✅ Curated resources and tutorials<br>
                        ⏱️ Realistic time estimates<br>
                        🎯 Skill progression tracking<br>
                        🏆 Achievement milestones</p>
                    </div>
                    
                    <p>Your roadmap provides a clear, step-by-step path to master the skills needed for your target role. Each milestone includes carefully selected resources, practical exercises, and progress checkpoints.</p>
                    
                    <div style="text-align: center;">
                        <a href="https://skillbridge.app/roadmap" class="button">🚀 Start Learning Now</a>
                    </div>
                    
                    <p><strong>💡 Pro Tip:</strong> Set aside dedicated time each day for learning. Consistency is key to achieving your {role_title} goals!</p>
                    
                    <p>Ready to begin your journey? Your future self will thank you for starting today!</p>
                    
                    <p>Happy learning! 📚<br><strong>The SkillBridge Team</strong></p>
                </div>
                <div class="footer">
                    <p>© 2024 SkillBridge Suite. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_progress_template(self) -> str:
        """Get weekly progress email HTML template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }}
                .content {{ background: #ffffff; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .stats {{ display: flex; justify-content: space-around; margin: 30px 0; flex-wrap: wrap; }}
                .stat {{ background: #f8fafc; padding: 20px; border-radius: 8px; text-align: center; flex: 1; margin: 5px; min-width: 120px; border-top: 3px solid #667eea; }}
                .stat h3 {{ color: #667eea; margin: 0; font-size: 32px; font-weight: bold; }}
                .stat p {{ margin: 5px 0 0 0; color: #64748b; font-size: 14px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; margin: 25px 0; font-weight: 600; }}
                .encouragement {{ background: #fef3c7; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; margin-top: 30px; color: #64748b; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Weekly Progress Summary</h1>
                    <p>Your learning journey this week</p>
                </div>
                <div class="content">
                    <h2>Great work this week, {user_name}! 🌟</h2>
                    <p>Here's a summary of your learning progress over the past 7 days. Every step forward brings you closer to your career goals!</p>
                    
                    <div class="stats">
                        <div class="stat">
                            <h3>{skills_added}</h3>
                            <p>Skills Added</p>
                        </div>
                        <div class="stat">
                            <h3>{resources_completed}</h3>
                            <p>Resources Completed</p>
                        </div>
                        <div class="stat">
                            <h3>{roadmap_progress}%</h3>
                            <p>Roadmap Progress</p>
                        </div>
                    </div>
                    
                    <div class="encouragement">
                        <p><strong>🎯 Keep the momentum going!</strong> Consistent learning is the key to achieving your career goals. You're building valuable skills that will serve you throughout your professional journey.</p>
                    </div>
                    
                    <p>Ready to continue your learning journey? Check out your personalized recommendations and take the next step toward mastering your target skills.</p>
                    
                    <div style="text-align: center;">
                        <a href="https://skillbridge.app/dashboard" class="button">📈 View Full Dashboard</a>
                    </div>
                    
                    <p><strong>💡 This Week's Focus:</strong> Consider dedicating extra time to hands-on practice and real-world projects to reinforce your learning.</p>
                    
                    <p>Keep up the excellent work! 🚀<br><strong>The SkillBridge Team</strong></p>
                </div>
                <div class="footer">
                    <p>© 2024 SkillBridge Suite. All rights reserved.</p>
                    <p>Want to change your email preferences? <a href="https://skillbridge.app/settings">Update settings</a></p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_feedback_confirmation_template(self) -> str:
        """Get feedback confirmation email HTML template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
                .content {{ background: #ffffff; padding: 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .highlight {{ background: #ecfdf5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
                .footer {{ text-align: center; margin-top: 30px; color: #64748b; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Thank You for Your Feedback!</h1>
                </div>
                <div class="content">
                    <h2>Hi {user_name}!</h2>
                    <p>Thank you for taking the time to share your feedback with us regarding: <strong>{feedback_type}</strong></p>
                    
                    <div class="highlight">
                        <p><strong>📝 What happens next?</strong></p>
                        <p>• Our team will carefully review your message<br>
                        • If a response is needed, we'll get back to you within 24-48 hours<br>
                        • Your feedback helps us improve SkillBridge for everyone</p>
                    </div>
                    
                    <p>We truly appreciate you taking the time to help us make SkillBridge Suite better. User feedback is invaluable in shaping our platform and ensuring we're meeting your needs.</p>
                    
                    <p>In the meantime, feel free to continue exploring SkillBridge and working toward your career goals. If you have any urgent questions, don't hesitate to reach out!</p>
                    
                    <p>Thank you for being part of our community! 🙏<br><strong>SkillBridge Support Team</strong></p>
                </div>
                <div class="footer">
                    <p>© 2024 SkillBridge Suite. All rights reserved.</p>
                    <p>Need immediate help? Visit our <a href="https://skillbridge.app/help">Help Center</a></p>
                </div>
            </div>
        </body>
        </html>
        """
    
    # Updated convenience methods using the new enhanced functionality
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new users"""
        return self.send_templated_email(
            to_email=user_email,
            template_name='welcome',
            variables={'user_name': user_name},
            priority='high'
        )
    
    def send_roadmap_generated_email(self, user_email: str, user_name: str, role_title: str, milestone_count: int) -> bool:
        """Send notification when AI roadmap is generated"""
        return self.send_templated_email(
            to_email=user_email,
            template_name='roadmap_generated',
            variables={
                'user_name': user_name,
                'role_title': role_title,
                'milestone_count': str(milestone_count)
            },
            priority='high'
        )
    
    def send_weekly_progress_email(self, user_email: str, user_name: str, progress_data: Dict) -> bool:
        """Send weekly progress summary email"""
        return self.send_templated_email(
            to_email=user_email,
            template_name='weekly_progress',
            variables={
                'user_name': user_name,
                'skills_added': str(progress_data.get('skillsAdded', 0)),
                'resources_completed': str(progress_data.get('resourcesCompleted', 0)),
                'roadmap_progress': str(progress_data.get('roadmapProgress', 0))
            }
        )
    
    def send_feedback_email(self, user_email: str, user_name: str, feedback_type: str, message: str) -> bool:
        """Send feedback/query email to support team"""
        try:
            subject = f"SkillBridge Feedback: {feedback_type} from {user_name}"
            
            # Send to support team (using same SMTP for simplicity)
            support_email = self.from_email  # In production, use dedicated support email
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #f59e0b; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #ffffff; padding: 30px; border-radius: 0 0 8px 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .user-info {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
                    .message {{ background: #fefce8; padding: 25px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #eab308; }}
                    .urgent {{ background: #fef2f2; border-left-color: #ef4444; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📬 New Feedback Received</h1>
                        <p>Type: {feedback_type}</p>
                    </div>
                    <div class="content">
                        <div class="user-info">
                            <h3>👤 User Information:</h3>
                            <p><strong>Name:</strong> {user_name}</p>
                            <p><strong>Email:</strong> {user_email}</p>
                            <p><strong>Feedback Type:</strong> {feedback_type}</p>
                            <p><strong>Submitted:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                        </div>
                        
                        <div class="message {'urgent' if feedback_type.lower() in ['bug', 'error', 'urgent'] else ''}">
                            <h3>💬 Message:</h3>
                            <p>{message}</p>
                        </div>
                        
                        <p><strong>⚡ Action Required:</strong> Please review and respond to this feedback within 24-48 hours.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send to support team with high priority for urgent issues
            priority = 'high' if feedback_type.lower() in ['bug', 'error', 'urgent'] else 'normal'
            success = self.send_email(support_email, subject, html_content, priority=priority)
            
            if success:
                # Send confirmation to user
                self.send_templated_email(
                    to_email=user_email,
                    template_name='feedback_confirmation',
                    variables={'user_name': user_name, 'feedback_type': feedback_type}
                )
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to send feedback email: {str(e)}")
            return False
    
    def send_bulk_email(self, recipients: List[str], subject: str, html_content: str, 
                       text_content: Optional[str] = None, batch_size: int = 50) -> Dict[str, int]:
        """
        Send bulk emails with batch processing
        
        Returns:
            Dict with 'sent' and 'failed' counts
        """
        results = {'sent': 0, 'failed': 0}
        
        try:
            # Process in batches to avoid overwhelming the SMTP server
            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i + batch_size]
                
                for email in batch:
                    if self.send_email(email, subject, html_content, text_content):
                        results['sent'] += 1
                    else:
                        results['failed'] += 1
                    
                    # Small delay between emails to be respectful to SMTP server
                    time.sleep(0.1)
                
                # Longer delay between batches
                if i + batch_size < len(recipients):
                    time.sleep(2)
            
            logger.info(f"📧 Bulk email completed: {results['sent']} sent, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"❌ Bulk email failed: {str(e)}")
            return results
    
    def test_email_configuration(self) -> Dict[str, Union[bool, str]]:
        """Test email configuration and connectivity"""
        result = {
            'config_valid': False,
            'connection_successful': False,
            'authentication_successful': False,
            'message': '',
            'details': {}
        }
        
        try:
            # Check configuration
            if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
                result['message'] = 'SMTP configuration incomplete'
                result['details'] = {
                    'smtp_host': bool(self.smtp_host),
                    'smtp_user': bool(self.smtp_user),
                    'smtp_password': bool(self.smtp_password)
                }
                return result
            
            result['config_valid'] = True
            
            # Test connection
            with self._create_smtp_connection() as server:
                result['connection_successful'] = True
                result['authentication_successful'] = True
                result['message'] = 'Email configuration test successful'
                
                # Get server info
                result['details'] = {
                    'smtp_host': self.smtp_host,
                    'smtp_port': self.smtp_port,
                    'from_email': self.from_email,
                    'server_features': list(server.esmtp_features.keys()) if hasattr(server, 'esmtp_features') else []
                }
            
            logger.info("✅ Email configuration test passed")
            return result
            
        except smtplib.SMTPAuthenticationError as e:
            result['message'] = f'Authentication failed: {str(e)}'
            logger.error(f"❌ Email authentication test failed: {str(e)}")
        except smtplib.SMTPConnectError as e:
            result['message'] = f'Connection failed: {str(e)}'
            logger.error(f"❌ Email connection test failed: {str(e)}")
        except Exception as e:
            result['message'] = f'Test failed: {str(e)}'
            logger.error(f"❌ Email configuration test failed: {str(e)}")
        
        return result