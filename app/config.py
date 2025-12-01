import os
from pathlib import Path


class Config:
    # Base directory
    BASE_DIR = Path(__file__).parent.parent
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{BASE_DIR / "instance" / "app.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Template configuration
    TEMPLATES_AUTO_RELOAD = True
    
    # File upload configuration
    UPLOAD_FOLDER = BASE_DIR / 'app' / 'static' / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    # Gemini AI configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # IoT configuration
    IOT_DEVICE_TIMEOUT = 300  # 5 minutes timeout for device heartbeat
