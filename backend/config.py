import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///unified_calendar.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    # Microsoft OAuth Configuration
    MICROSOFT_CLIENT_ID = os.environ.get('MICROSOFT_CLIENT_ID')
    MICROSOFT_CLIENT_SECRET = os.environ.get('MICROSOFT_CLIENT_SECRET')
    MICROSOFT_REDIRECT_URI = os.environ.get('MICROSOFT_REDIRECT_URI', 'http://localhost:5000/outlook_callback')
    MICROSOFT_TENANT_ID = os.environ.get('MICROSOFT_TENANT_ID')
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'session'
    
    # Flask-Login Configuration
    REMEMBER_COOKIE_DURATION = 3600  # 1 hour
    REMEMBER_COOKIE_SECURE = False  # Set to True in production with HTTPS
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
    
    # CORS Configuration
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173']
    
    # Timezone Configuration
    DEFAULT_TIMEZONE = os.environ.get('DEFAULT_TIMEZONE', 'UTC')
    TIMEZONE_OFFSET = os.environ.get('TIMEZONE_OFFSET', '+00:00')  # Format: +05:30 for IST
    
    # Feature Flags
    # Set to False to temporarily disable Microsoft Calendar integration
    # This prevents tenant-wide event notifications when using company tenant ID
    MICROSOFT_ENABLED = os.environ.get('MICROSOFT_ENABLED', 'false').lower() == 'true'