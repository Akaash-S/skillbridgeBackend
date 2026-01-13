import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Firebase
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Gemini AI
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # YouTube Data API
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    
    # Adzuna Jobs API
    ADZUNA_APP_ID = os.environ.get('ADZUNA_APP_ID')
    ADZUNA_APP_KEY = os.environ.get('ADZUNA_APP_KEY')
    
    # SMTP Email Configuration
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    
    # Email Settings
    EMAIL_FROM_NAME = os.environ.get('EMAIL_FROM_NAME', 'SkillBridge Suite')
    EMAIL_SUPPORT = os.environ.get('EMAIL_SUPPORT', os.environ.get('SMTP_USER'))
    EMAIL_RATE_LIMIT = int(os.environ.get('EMAIL_RATE_LIMIT', 10))  # emails per minute
    EMAIL_BATCH_SIZE = int(os.environ.get('EMAIL_BATCH_SIZE', 50))  # for bulk emails
    
    # Environment
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    
    @staticmethod
    def validate_config():
        """Validate required environment variables"""
        required_vars = [
            'GOOGLE_APPLICATION_CREDENTIALS',
            'GEMINI_API_KEY',
            'YOUTUBE_API_KEY',
            'ADZUNA_APP_ID',
            'ADZUNA_APP_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True