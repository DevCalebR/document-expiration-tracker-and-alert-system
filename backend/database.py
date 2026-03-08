import logging
from datetime import datetime
from pathlib import Path
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

logger = logging.getLogger(__name__)


connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
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
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
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


def run_migrations():
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


def init_db():
    run_migrations_flag = os.getenv("RUN_MIGRATIONS_ON_STARTUP", "True") == "True"
    if run_migrations_flag:
        try:
            run_migrations()
            return
        except Exception:
            logger.exception("database_migration_failed")
            if settings.APP_ENV in {"staging", "production"}:
                raise
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
