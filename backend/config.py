import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Application
    APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-key-change-in-production")
    APP_DEBUG = os.getenv("APP_DEBUG", "True") == "True"
    APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./docexpire.db")
    
    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    
    # Frontend URL (for email verification links)
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Google Drive
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    # Dropbox
    DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY", "")
    DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET", "")
    DROPBOX_REDIRECT_URI = os.getenv("DROPBOX_REDIRECT_URI", "http://localhost:8000/auth/dropbox/callback")
    
    # Microsoft OneDrive
    MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/auth/microsoft/callback")
    MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
    
    # Anthropic API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # File Upload
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", ".pdf,.png,.jpg,.jpeg").split(",")
    UPLOAD_DIR_OVERRIDE = os.getenv("UPLOAD_DIR", "")
    
    # Directories
    BASE_DIR = Path(__file__).resolve().parent
    UPLOAD_DIR = Path(UPLOAD_DIR_OVERRIDE) if UPLOAD_DIR_OVERRIDE else (BASE_DIR / "uploads")
    UPLOAD_DIR.mkdir(exist_ok=True)

    # Alerts
    ALERT_DAYS = int(os.getenv("ALERT_DAYS", "7"))

settings = Settings()
