import html
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

try:
    import sentry_sdk
except Exception:
    sentry_sdk = None

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ai_analyzer import AIAnalyzer
from auth import (
    authenticate_user,
    create_access_token,
    create_oauth_state,
    decode_oauth_state,
    get_current_active_user,
    get_password_hash,
    log_audit,
    require_admin,
    serialize_user,
)
from cloud_connectors import (
    CloudConnectionError,
    CloudProviderNotConfiguredError,
    CloudProviderNotConnectedError,
    DropboxConnector,
    GoogleDriveConnector,
    OneDriveConnector,
    disconnect_provider,
    get_provider_status,
    provider_is_configured,
)
from config import settings
from database import AuditLog, Document, DocumentDate, User, get_db, init_db
from email_service import (
    EmailDeliveryError,
    EmailNotConfiguredError,
    email_is_configured,
    send_email,
)
from health import dependency_status
from job_queue import enqueue_job, fetch_job, get_queue, get_queue_mode
from jobs import process_documents_job, send_expiration_alerts_job
from logging_config import setup_logging
from middleware import LoggingMiddleware, RequestIdMiddleware
from processing import extract_dates, extract_text_from_file
from security import SecurityHeadersMiddleware
from storage import StorageError, build_object_key, create_temp_file, get_storage_client

setup_logging()
logger = logging.getLogger(__name__)

if settings.SENTRY_DSN and sentry_sdk:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )

app = FastAPI(title="DocExpire API")
ai_analyzer = AIAnalyzer()
init_db()

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

PROVIDER_CONNECTORS = {
    "google_drive": GoogleDriveConnector,
    "dropbox": DropboxConnector,
    "onedrive": OneDriveConnector,
}
CALLBACK_PROVIDER_ALIASES = {
    "google": "google_drive",
    "google_drive": "google_drive",
    "dropbox": "dropbox",
    "microsoft": "onedrive",
    "onedrive": "onedrive",
}
UPLOAD_MIME_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/jpg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str
    full_name: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=8, max_length=200)


class CloudFileSelection(BaseModel):
    id: str
    name: Optional[str] = None


class CloudImportRequest(BaseModel):
    provider: Optional[str] = None
    file_ids: List[str] = Field(default_factory=list)
    files: List[CloudFileSelection] = Field(default_factory=list)


class AIAnalyzeRequest(BaseModel):
    results: List[dict]


class VerifyEmailRequest(BaseModel):
    username: str
    token: str


class ProcessRequest(BaseModel):
    filenames: List[str]


def _normalize_provider(provider: str) -> str:
    normalized = CALLBACK_PROVIDER_ALIASES.get(provider)
    if not normalized:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    return normalized


def _get_provider_connector(provider: str):
    normalized = _normalize_provider(provider)
    return normalized, PROVIDER_CONNECTORS[normalized]


def _cloud_exception_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, CloudProviderNotConfiguredError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, CloudProviderNotConnectedError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


def _manual_verification_allowed() -> bool:
    return settings.APP_ENV in {"development", "test"}


def _verification_link(user: User) -> str:
    return f"{settings.FRONTEND_URL}/verify-email?username={user.username}&token={user.verification_token}"


def _serialize_document(doc: Document) -> dict:
    return {
        "original_filename": doc.original_filename,
        "saved_filename": doc.stored_filename,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "last_processed_at": doc.last_processed_at.isoformat() if doc.last_processed_at else None,
    }


def _oauth_callback_response(success: bool, provider: str, message: str) -> HTMLResponse:
    payload = json.dumps(
        {
            "type": "docexpire:cloud-oauth",
            "success": success,
            "provider": provider,
            "message": message,
        }
    )
    frontend_origin = json.dumps(settings.FRONTEND_ORIGIN)
    safe_message = html.escape(message)
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>DocExpire Cloud Connection</title>
  </head>
  <body style="font-family: sans-serif; padding: 24px;">
    <p>{safe_message}</p>
    <p>You can close this window.</p>
    <script>
      const payload = {payload};
      if (window.opener) {{
        window.opener.postMessage(payload, {frontend_origin});
        window.close();
      }}
    </script>
  </body>
</html>"""
    )


def _selected_cloud_files(payload: CloudImportRequest) -> List[CloudFileSelection]:
    if payload.files:
        return payload.files
    return [CloudFileSelection(id=file_id, name=file_id) for file_id in payload.file_ids]


def _validate_upload(file: UploadFile, file_bytes: bytes) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File is empty")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext or 'missing'}")

    if file.content_type not in UPLOAD_MIME_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    if ext not in UPLOAD_MIME_EXTENSIONS[file.content_type]:
        raise HTTPException(
            status_code=400,
            detail=f"Filename extension {ext} does not match content type {file.content_type}",
        )

    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {settings.MAX_FILE_SIZE_MB}MB")


def _build_processing_summary(db: Session, current_user: User, filenames: List[str]) -> dict:
    summary = []

    for fname in filenames:
        doc = (
            db.query(Document)
            .filter(Document.stored_filename == fname, Document.user_id == current_user.id)
            .first()
        )
        if not doc:
            summary.append({"filename": fname, "stored_filename": fname, "error": "File not found"})
            continue

        storage = get_storage_client()
        temp_path = create_temp_file(Path(doc.original_filename).suffix or Path(doc.stored_filename).suffix)
        try:
            try:
                storage.download_to_path(doc.stored_filename, temp_path)
            except StorageError as exc:
                summary.append(
                    {
                        "filename": doc.original_filename,
                        "stored_filename": doc.stored_filename,
                        "error": str(exc),
                    }
                )
                continue

            text_data, error = extract_text_from_file(temp_path)
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass

        if error:
            summary.append(
                {
                    "filename": doc.original_filename,
                    "stored_filename": doc.stored_filename,
                    "error": error,
                }
            )
            continue

        full_text = " ".join(page["text"] for page in text_data["content"])
        dates_found = extract_dates(full_text)

        db.query(DocumentDate).filter(DocumentDate.document_id == doc.id).delete()
        for result in dates_found:
            db.add(
                DocumentDate(
                    document_id=doc.id,
                    date_raw=result.get("date_raw"),
                    date_iso=result.get("date_iso"),
                    detected_format=result.get("detected_format"),
                    is_expired=result.get("is_expired"),
                    days_until_expiration=result.get("days_until_expiration"),
                )
            )
        doc.last_processed_at = datetime.utcnow()
        db.commit()

        summary.append(
            {
                "filename": doc.original_filename,
                "stored_filename": doc.stored_filename,
                "pages_extracted": text_data["pages"],
                "dates_detected": len(dates_found),
                "results": dates_found,
            }
        )

    log_audit(db, current_user.username, "process", f"Processed {len(summary)} file(s)")
    return {"status": "success", "files_processed": len(summary), "summary": summary}


@app.post("/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )
    log_audit(db, user.username, "login", "User logged in")
    return {"access_token": access_token, "token_type": "bearer", "user": serialize_user(user)}


@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_active_user)):
    return {"user": serialize_user(current_user)}


@app.post("/auth/logout")
def logout(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    log_audit(db, current_user.username, "logout", "User logged out")
    return {"message": "Logged out successfully"}


@app.post("/auth/register")
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter((User.username == user_data.username) | (User.email == user_data.email))
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    if settings.APP_ENV in {"staging", "production"} and not email_is_configured():
        raise HTTPException(
            status_code=503,
            detail="SMTP must be configured before registration is enabled in this environment.",
        )

    verification_token = secrets.token_urlsafe(32)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role="user",
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(new_user)
    db.flush()

    verification_link = _verification_link(new_user)
    try:
        email_result = send_email(
            new_user.email,
            "Verify your DocExpire account",
            (
                f"Hello {new_user.full_name},\n\n"
                "Please verify your email by clicking the link below:\n\n"
                f"{verification_link}\n\n"
                "If you did not register, ignore this email.\n"
            ),
            raise_on_failure=settings.APP_ENV in {"staging", "production"},
        )
    except EmailNotConfiguredError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc))
    except EmailDeliveryError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc))

    if not email_result.sent and not _manual_verification_allowed():
        db.rollback()
        raise HTTPException(status_code=502, detail=email_result.detail)

    db.commit()
    db.refresh(new_user)
    log_audit(db, new_user.username, "register", "New user registered")

    response = {
        "status": "success",
        "message": "User registered. Verification email sent."
        if email_result.sent
        else "User registered. SMTP is not configured, so use the verification link below.",
        "email_delivery": {
            "configured": email_is_configured(),
            "sent": email_result.sent,
            "detail": email_result.detail,
        },
    }
    if not email_result.sent and _manual_verification_allowed():
        response["verification_url"] = verification_link
    return response


@app.post("/auth/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"status": "success", "message": "Email already verified"}
    if user.verification_token != payload.token:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    user.is_verified = True
    user.verification_token = None
    db.commit()
    log_audit(db, user.username, "verify_email", "Email verified")
    return {"status": "success", "message": "Email verified successfully"}


@app.get("/health")
def health():
    return readiness()


@app.get("/healthz")
def liveness():
    return {"status": "ok", "version": settings.SERVICE_VERSION, "service": settings.SERVICE_NAME}


@app.get("/readyz")
def readiness():
    deps = dependency_status()
    all_ok = all(item["status"] == "ok" for item in deps.values())
    payload = {
        "status": "ok" if all_ok else "degraded",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "dependencies": deps,
    }
    return JSONResponse(status_code=200 if all_ok else 503, content=payload)


@app.get("/")
def root():
    return {
        "message": "DocExpire API",
        "environment": settings.APP_ENV,
        "queue_mode": get_queue_mode(),
        "storage_provider": settings.STORAGE_PROVIDER,
    }


@app.get("/files")
def list_documents(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return {"files": [_serialize_document(doc) for doc in docs]}


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    file_bytes = await file.read()
    _validate_upload(file, file_bytes)

    timestamp = int(time.time())
    safe_filename = Path(file.filename).name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    object_key = build_object_key(current_user.id, f"{timestamp}_{safe_filename}")

    storage = get_storage_client()
    try:
        storage.upload_bytes(object_key, file_bytes, content_type=file.content_type)
    except StorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    doc = Document(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=object_key,
        mime_type=file.content_type,
        size_bytes=len(file_bytes),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    ip_address = request.client.host if request and request.client else None
    log_audit(db, current_user.username, "upload", f"Uploaded {file.filename}", ip_address=ip_address)

    return {
        "status": "success",
        "original_filename": file.filename,
        "saved_filename": object_key,
        "mime_type": file.content_type,
        "size_bytes": len(file_bytes),
        "uploaded_at": timestamp,
    }


@app.get("/extract-text")
def extract_text_endpoint(
    filename: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.stored_filename == filename, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    storage = get_storage_client()
    temp_path = create_temp_file(Path(doc.original_filename).suffix or Path(doc.stored_filename).suffix)
    try:
        try:
            storage.download_to_path(doc.stored_filename, temp_path)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        text_data, error = extract_text_from_file(temp_path)
        if error:
            raise HTTPException(status_code=400, detail=error)
        return text_data
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass


@app.get("/process")
def process_files(
    filenames: List[str] = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not filenames:
        raise HTTPException(status_code=400, detail="At least one filename is required")
    return _build_processing_summary(db, current_user, filenames)


@app.post("/process/async")
def process_files_async(
    payload: ProcessRequest,
    current_user: User = Depends(get_current_active_user),
):
    if not payload.filenames:
        raise HTTPException(status_code=400, detail="At least one filename is required")

    job = enqueue_job(process_documents_job, current_user.id, payload.filenames)
    job.meta["user_id"] = current_user.id
    job.save_meta()
    return {"job_id": job.id, "status": job.get_status()}


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str, current_user: User = Depends(get_current_active_user)):
    job = fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_user_id = job.meta.get("user_id") if job.meta else None
    if job_user_id is not None and job_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    response = {
        "job_id": job.id,
        "status": job.get_status(),
        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        "result": job.return_value() if hasattr(job, "return_value") else job.result,
    }
    if job.is_failed:
        response["error"] = job.exc_info
    return response


@app.get("/documents/expiring-soon")
def get_expiring_documents(
    days: int = 7,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    doc_dates = (
        db.query(DocumentDate, Document)
        .filter(
            DocumentDate.document_id == Document.id,
            Document.user_id == current_user.id,
            DocumentDate.days_until_expiration.isnot(None),
            DocumentDate.days_until_expiration >= 0,
            DocumentDate.days_until_expiration <= days,
        )
        .all()
    )
    return {
        "days": days,
        "results": [
            {
                "document": {
                    "original_filename": doc.original_filename,
                    "stored_filename": doc.stored_filename,
                },
                "date_raw": date_row.date_raw,
                "date_iso": date_row.date_iso,
                "days_until_expiration": date_row.days_until_expiration,
            }
            for date_row, doc in doc_dates
        ],
    }


@app.post("/ai/analyze")
def analyze_with_ai(
    payload: AIAnalyzeRequest,
    current_user: User = Depends(get_current_active_user),
):
    return ai_analyzer.analyze_dates(payload.results)


@app.get("/audit/logs")
def get_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return {
        "logs": [
            {
                "username": log.username,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address,
            }
            for log in logs
        ]
    }


@app.get("/admin/status")
def admin_status(current_user: User = Depends(require_admin)):
    deps = dependency_status()
    queue_info = {"mode": get_queue_mode()}
    try:
        from rq.registry import DeferredJobRegistry, FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry

        queue = get_queue()
        queue_info.update(
            {
                "queued": queue.count,
                "started": StartedJobRegistry(queue=queue).count,
                "finished": FinishedJobRegistry(queue=queue).count,
                "failed": FailedJobRegistry(queue=queue).count,
                "deferred": DeferredJobRegistry(queue=queue).count,
            }
        )
    except Exception as exc:
        queue_info["error"] = str(exc)

    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.APP_ENV,
        "dependencies": deps,
        "queue": queue_info,
        "email": {"configured": email_is_configured()},
        "cloud": {
            provider: {"configured": provider_is_configured(provider)}
            for provider in PROVIDER_CONNECTORS
        },
    }


@app.post("/admin/alerts/run")
def run_alerts(current_user: User = Depends(require_admin)):
    job = enqueue_job(send_expiration_alerts_job)
    job.meta["user_id"] = current_user.id
    job.save_meta()
    return {"job_id": job.id, "status": job.get_status()}


@app.post("/admin/test-email")
def test_email(current_user: User = Depends(require_admin)):
    try:
        result = send_email(
            current_user.email,
            "DocExpire Test Email",
            "This is a test notification from DocExpire.",
            raise_on_failure=True,
        )
        return {"status": "success", "message": result.detail}
    except EmailNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/cloud/providers")
def list_cloud_providers(current_user: User = Depends(get_current_active_user)):
    return {
        "providers": [get_provider_status(current_user.id, provider) for provider in PROVIDER_CONNECTORS]
    }


@app.get("/cloud/{provider}/auth-url")
def get_cloud_auth_url(provider: str, current_user: User = Depends(get_current_active_user)):
    normalized_provider, connector = _get_provider_connector(provider)
    try:
        auth_url = connector.get_auth_url(
            current_user.id,
            state=create_oauth_state(current_user.id, normalized_provider),
        )
    except Exception as exc:
        raise _cloud_exception_to_http(exc)
    return {"provider": normalized_provider, "auth_url": auth_url}


@app.get("/cloud/{provider}/files")
def list_cloud_files(provider: str, current_user: User = Depends(get_current_active_user)):
    normalized_provider, connector = _get_provider_connector(provider)
    try:
        files = connector.list_files(current_user.id)
    except Exception as exc:
        raise _cloud_exception_to_http(exc)
    return {"provider": normalized_provider, "files": files}


@app.post("/cloud/{provider}/import")
def import_cloud_files(
    provider: str,
    payload: CloudImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    normalized_provider, connector = _get_provider_connector(provider)
    selected_files = _selected_cloud_files(payload)
    if not selected_files:
        raise HTTPException(status_code=400, detail="Select at least one file to import")

    imported = []
    storage = get_storage_client()
    for selection in selected_files:
        display_name = selection.name or selection.id
        safe_source_name = Path(display_name).name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        object_key = build_object_key(current_user.id, f"{int(time.time())}_{safe_source_name}")
        temp_path = create_temp_file(Path(display_name).suffix or Path(selection.id).suffix)

        try:
            connector.download_file(current_user.id, selection.id, temp_path)
            file_bytes = temp_path.read_bytes()
            storage.upload_bytes(object_key, file_bytes, content_type="application/octet-stream")
            size_bytes = len(file_bytes)
        except Exception as exc:
            raise _cloud_exception_to_http(exc)
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass

        doc = Document(
            user_id=current_user.id,
            original_filename=display_name,
            stored_filename=object_key,
            mime_type="application/octet-stream",
            size_bytes=size_bytes,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        imported.append(_serialize_document(doc))

    log_audit(db, current_user.username, "cloud_import", f"Imported {len(imported)} file(s) from {normalized_provider}")
    return {"status": "success", "imported_files": imported}


@app.delete("/cloud/{provider}/connection")
def disconnect_cloud_provider(provider: str, current_user: User = Depends(get_current_active_user)):
    normalized_provider = _normalize_provider(provider)
    deleted = disconnect_provider(current_user.id, normalized_provider)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cloud connection not found")
    return {"status": "success", "message": f"Disconnected {normalized_provider}"}


@app.get("/auth/{provider}/callback", response_class=HTMLResponse)
@app.get("/cloud/{provider}/callback", response_class=HTMLResponse)
def cloud_oauth_callback(
    provider: str,
    state: str,
    code: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    normalized_provider = _normalize_provider(provider)
    if error:
        message = error_description or error
        return _oauth_callback_response(False, normalized_provider, message)

    if not code:
        return _oauth_callback_response(False, normalized_provider, "Missing OAuth authorization code.")

    try:
        oauth_state = decode_oauth_state(state)
    except JWTError:
        return _oauth_callback_response(False, normalized_provider, "Invalid or expired OAuth state.")

    state_provider = oauth_state.get("provider")
    state_user_id = oauth_state.get("sub")
    if state_provider != normalized_provider or not state_user_id:
        return _oauth_callback_response(False, normalized_provider, "OAuth state does not match the provider.")

    connector = PROVIDER_CONNECTORS[normalized_provider]
    try:
        connector.handle_callback(code, int(state_user_id))
    except Exception as exc:
        logger.exception("cloud_oauth_callback_failed", extra={"provider": normalized_provider})
        return _oauth_callback_response(False, normalized_provider, str(exc))

    user = db.query(User).filter(User.id == int(state_user_id)).first()
    if user:
        log_audit(db, user.username, "cloud_connect", f"Connected {normalized_provider}")
    return _oauth_callback_response(True, normalized_provider, f"{normalized_provider} connected successfully.")


@app.delete("/files/{filename:path}")
def delete_file(
    filename: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.stored_filename == filename, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    storage = get_storage_client()
    try:
        storage.delete(doc.stored_filename)
    except StorageError:
        logger.warning("storage_delete_failed", extra={"filename": doc.stored_filename})

    db.query(DocumentDate).filter(DocumentDate.document_id == doc.id).delete()
    db.delete(doc)
    db.commit()
    log_audit(db, current_user.username, "delete", f"Deleted {doc.original_filename}")
    return {"status": "success"}
