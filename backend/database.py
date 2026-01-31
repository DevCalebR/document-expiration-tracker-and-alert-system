from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Email verification status
    verification_token = Column(String, nullable=True)  # Token for email verification
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    action = Column(String)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)

class CloudToken(Base):
    __tablename__ = "cloud_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    provider = Column(String)
    access_token = Column(Text)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    original_filename = Column(String)
    stored_filename = Column(String, unique=True, index=True)
    mime_type = Column(String)
    size_bytes = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    last_processed_at = Column(DateTime, nullable=True)

class DocumentDate(Base):
    __tablename__ = "document_dates"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True)
    date_raw = Column(String)
    date_iso = Column(String, nullable=True)
    detected_format = Column(String, nullable=True)
    is_expired = Column(Boolean, nullable=True)
    days_until_expiration = Column(Integer, nullable=True)
    last_alerted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    from auth import get_password_hash
    
    if settings.APP_DEBUG:
        # Default admin user (dev only)
        admin_exists = db.query(User).filter(User.username == "admin").first()
        if not admin_exists:
            admin = User(
                username="admin",
                email="admin@docexpire.local",
                full_name="Admin User",
                hashed_password=get_password_hash("admin"),
                role="admin",
                is_verified=True,
            )
            db.add(admin)
        
        # Default regular user (dev only)
        user_exists = db.query(User).filter(User.username == "user").first()
        if not user_exists:
            user = User(
                username="user",
                email="user@docexpire.local",
                full_name="Regular User",
                hashed_password=get_password_hash("user"),
                role="user",
                is_verified=True,
            )
            db.add(user)
    
    db.commit()
    db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
