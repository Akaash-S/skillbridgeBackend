import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import argparse
import os
import sys

def load_env(env_path):
    config = {}
    if not os.path.exists(env_path):
        return config
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                config[k.strip()] = v.strip().strip('"').strip("'")
    return config

def main():
    parser = argparse.ArgumentParser(description='Send SkillBridge Backup Notification Email')
    parser.add_argument('--status', required=True, choices=['success', 'failed'], help='Backup status')
    parser.add_argument('--file', help='Backup filename (for success)')
    parser.add_argument('--error', help='Error message (for failure)')
    args = parser.parse_args()

    # Path to backend env
    env_path = "/opt/skillbridge/backend/.env"
    if not os.path.exists(env_path):
        # Fallback to current dir if running locally
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

    config = load_env(env_path)
    
    smtp_host = config.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(config.get('SMTP_PORT', 587))
    smtp_user = config.get('SMTP_USER')
    smtp_password = config.get('SMTP_PASSWORD')
    email_support = config.get('EMAIL_SUPPORT', 'akaashofficial21@gmail.com')
    
    if not smtp_user or not smtp_password:
        print("Error: SMTP_USER and SMTP_PASSWORD must be configured in .env", file=sys.stderr)
        sys.exit(1)
        
    subject = f"[SkillBridge] Backup Notification: {args.status.upper()}"
    
    if args.status == 'success':
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #f8fafc;">
                <h2 style="color: #10b981; border-bottom: 2px solid #10b981; padding-bottom: 10px;">✅ Backup Succeeded</h2>
                <p>The automated daily backup for SkillBridge was created successfully.</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <tr style="background-color: #f1f5f9;">
                        <td style="padding: 10px; font-weight: bold; width: 120px;">Filename:</td>
                        <td style="padding: 10px; font-family: monospace;">{args.file}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">Location:</td>
                        <td style="padding: 10px; font-family: monospace;">/opt/skillbridge/backups</td>
                    </tr>
                    <tr style="background-color: #f1f5f9;">
                        <td style="padding: 10px; font-weight: bold;">Timestamp:</td>
                        <td style="padding: 10px;">{os.popen('date').read().strip()}</td>
                    </tr>
                </table>
                <p style="margin-top: 20px; font-size: 12px; color: #64748b; text-align: center;">This is an automated notification from your SkillBridge VM.</p>
            </div>
        </body>
        </html>
        """
    else:
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #fff5f5;">
                <h2 style="color: #ef4444; border-bottom: 2px solid #ef4444; padding-bottom: 10px;">❌ Backup Failed</h2>
                <p>The automated daily backup for SkillBridge failed to complete.</p>
                <div style="padding: 15px; background-color: #fee2e2; border-left: 4px solid #ef4444; margin-top: 15px; border-radius: 4px;">
                    <strong>Error Message:</strong><br/>
                    <pre style="font-family: monospace; white-space: pre-wrap; margin: 5px 0 0 0;">{args.error}</pre>
                </div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                    <tr style="background-color: #f1f5f9;">
                        <td style="padding: 10px; font-weight: bold; width: 120px;">Timestamp:</td>
                        <td style="padding: 10px;">{os.popen('date').read().strip()}</td>
                    </tr>
                </table>
                <p style="margin-top: 20px; font-size: 12px; color: #64748b; text-align: center;">Please log into the VM to troubleshoot the issue.</p>
            </div>
        </body>
        </html>
        """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"SkillBridge Backups <{smtp_user}>"
    msg['To'] = email_support
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        context = ssl.create_default_context()
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [email_support], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [email_support], msg.as_string())
        print("Email notification sent successfully.")
    except Exception as e:
        print(f"Failed to send email notification: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
