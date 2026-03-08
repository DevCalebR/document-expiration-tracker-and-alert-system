from pathlib import Path
from urllib.parse import urlparse
from typing import List, Optional
from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    # Application
    APP_ENV: str = Field("development", regex="^(development|staging|production|test)$")
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_SECRET_KEY: str = Field(..., min_length=32)
    SERVICE_NAME: str = "docexpire-api"
    SERVICE_VERSION: str = "2.1.0"

    # Database
    DATABASE_URL: str = "sqlite:///./docexpire.db"

    # JWT
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Frontend URL (for email verification links)
    FRONTEND_URL: str = "http://localhost:5173"

    # CORS / Hosts
    CORS_ALLOW_ORIGINS: List[str] = ["http://localhost:5173"]
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["Authorization", "Content-Type"]
    CORS_ALLOW_CREDENTIALS: bool = True
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "testserver"]

    # Redis / Queue
    REDIS_URL: str = "fakeredis://"
    RQ_QUEUE_NAME: str = "docexpire"
    RQ_JOB_TIMEOUT: int = 600
    RQ_RESULT_TTL: int = 3600
    RQ_ASYNC: bool = False

    # Observability
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | plain
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".png", ".jpg", ".jpeg"]

    # Object storage
    STORAGE_PROVIDER: str = "filesystem"  # filesystem | s3 | gcs | azure | memory
    STORAGE_BUCKET: str = ""
    STORAGE_PREFIX: str = "uploads"
    STORAGE_REGION: Optional[str] = None
    STORAGE_ENDPOINT_URL: Optional[str] = None
    STORAGE_ACCESS_KEY: Optional[str] = None
    STORAGE_SECRET_KEY: Optional[str] = None
    STORAGE_FILESYSTEM_ROOT: Optional[str] = None

    # Azure storage (uses STORAGE_BUCKET as container name)
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_URL: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = None

    # Temp storage for OCR/downloads
    TEMP_DIR_OVERRIDE: Optional[str] = None

    # Alerts
    ALERT_DAYS: int = 7
    ALERTS_ENABLED: bool = True
    ALERT_INTERVAL_HOURS: int = 24

    # Secure headers
    SECURE_HEADERS_ENABLED: bool = True
    SECURE_HEADERS_HSTS_SECONDS: int = 0
    SECURE_HEADERS_CSP: str = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

    # Email (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = None

    # OAuth providers (optional)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    DROPBOX_APP_KEY: Optional[str] = None
    DROPBOX_APP_SECRET: Optional[str] = None
    DROPBOX_REDIRECT_URI: Optional[str] = None

    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_REDIRECT_URI: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"

    # Anthropic API (optional)
    ANTHROPIC_API_KEY: Optional[str] = None

    # Secret encryption at rest
    TOKEN_ENCRYPTION_KEY: Optional[str] = None

    @validator(
        "CORS_ALLOW_ORIGINS",
        "CORS_ALLOW_METHODS",
        "CORS_ALLOW_HEADERS",
        "ALLOWED_HOSTS",
        "ALLOWED_EXTENSIONS",
        pre=True,
    )
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @validator("CORS_ALLOW_ORIGINS")
    def _validate_cors_origins(cls, value, values):
        if not value:
            raise ValueError("CORS_ALLOW_ORIGINS must not be empty")
        if values.get("APP_ENV") in {"staging", "production"} and "*" in value:
            raise ValueError("CORS_ALLOW_ORIGINS cannot include '*' in staging/production")
        return value

    @validator("ALLOWED_HOSTS")
    def _validate_allowed_hosts(cls, value, values):
        if not value:
            raise ValueError("ALLOWED_HOSTS must not be empty")
        if values.get("APP_ENV") in {"staging", "production"} and "*" in value:
            raise ValueError("ALLOWED_HOSTS cannot include '*' in staging/production")
        return value

    @validator("APP_DEBUG")
    def _validate_debug(cls, value, values):
        if value and values.get("APP_ENV") in {"staging", "production"}:
            raise ValueError("APP_DEBUG cannot be true in staging/production")
        return value

    @validator("APP_SECRET_KEY", "JWT_SECRET_KEY")
    def _validate_secrets(cls, value, values):
        if values.get("APP_ENV") in {"staging", "production"} and value.startswith("your-"):
            raise ValueError("Application secrets must be explicitly configured in staging/production")
        return value

    @validator("REDIS_URL")
    def _validate_redis_url(cls, value, values):
        if values.get("APP_ENV") in {"staging", "production"} and value.startswith("fakeredis://"):
            raise ValueError("fakeredis:// is not allowed in staging/production")
        return value

    @validator("TOKEN_ENCRYPTION_KEY", always=True)
    def _validate_token_encryption_key(cls, value, values):
        if values.get("APP_ENV") in {"staging", "production"} and not value:
            raise ValueError("TOKEN_ENCRYPTION_KEY is required in staging/production")
        return value

    @validator("STORAGE_PROVIDER")
    def _validate_storage_provider(cls, value):
        allowed = {"filesystem", "s3", "gcs", "azure", "memory"}
        provider = value.lower()
        if provider not in allowed:
            raise ValueError(f"Unsupported STORAGE_PROVIDER '{value}'")
        return provider

    @property
    def BASE_DIR(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def TEMP_DIR(self) -> Path:
        temp_dir = Path(self.TEMP_DIR_OVERRIDE) if self.TEMP_DIR_OVERRIDE else (self.BASE_DIR / "tmp")
        temp_dir.mkdir(exist_ok=True)
        return temp_dir

    @property
    def FILESYSTEM_STORAGE_ROOT(self) -> Path:
        root = (
            Path(self.STORAGE_FILESYSTEM_ROOT)
            if self.STORAGE_FILESYSTEM_ROOT
            else (self.BASE_DIR / "local_storage")
        )
        root.mkdir(parents=True, exist_ok=True)
        return root

    @property
    def FRONTEND_ORIGIN(self) -> str:
        parsed = urlparse(self.FRONTEND_URL)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return self.FRONTEND_URL

    class Config:
        env_file = str(Path(__file__).resolve().parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True

        @classmethod
        def parse_env_var(cls, field_name, raw_val):
            if field_name in {
                "CORS_ALLOW_ORIGINS",
                "CORS_ALLOW_METHODS",
                "CORS_ALLOW_HEADERS",
                "ALLOWED_HOSTS",
                "ALLOWED_EXTENSIONS",
            }:
                return [item.strip() for item in raw_val.split(",") if item.strip()]
            return raw_val


settings = Settings()
