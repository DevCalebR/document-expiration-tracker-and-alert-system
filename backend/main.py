from pytesseract import image_to_string
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from pydantic import BaseModel
from typing import List
import time
import os
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import secrets

from config import settings
from database import init_db, get_db, User, AuditLog, Document, DocumentDate
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    require_admin, log_audit, get_password_hash
)
from cloud_connectors import GoogleDriveConnector, DropboxConnector, OneDriveConnector
from ai_analyzer import AIAnalyzer
from email_service import send_email
from scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="DocExpire API - Enterprise Edition")
ai_analyzer = AIAnalyzer()

# Initialize database
init_db()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================
# MODELS
# ===========================

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str

class CloudImportRequest(BaseModel):
    provider: str
    file_ids: List[str]

class AIAnalyzeRequest(BaseModel):
    results: List[dict]

class VerifyEmailRequest(BaseModel):
    username: str
    token: str

# ===========================
# AUTHENTICATION
# ===========================

@app.post("/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    log_audit(db, user.username, "login", "User logged in")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@app.post("/auth/logout")
def logout(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    log_audit(db, current_user.username, "logout", "User logged out")
    return {"message": "Logged out successfully"}

# ===========================
# USER REGISTRATION
# ===========================

@app.post("/auth/register")
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    verification_token = secrets.token_urlsafe(32)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role="user",
        is_verified=False,
        verification_token=verification_token
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    verification_link = f"{settings.FRONTEND_URL}/verify-email?username={new_user.username}&token={verification_token}"
    subject = "Verify your DocExpire account"
    body = f"""Hello {new_user.full_name},

Please verify your email by clicking the link below:

{verification_link}

If you did not register, ignore this email.
"""
    send_email(new_user.email, subject, body)
    
    log_audit(db, new_user.username, "register", "New user registered")
    
    return {"status": "success", "message": "User registered. Verification email sent."}

@app.post("/auth/verify-email")
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"status": "success", "message": "Email already verified"}
    if user.verification_token != request.token:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    log_audit(db, user.username, "verify_email", "Email verified")
    
    return {"status": "success", "message": "Email verified successfully"}

# ===========================
# HEALTH & ROOT
# ===========================

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.1.0"}

@app.get("/")
def root():
    return {"message": "DocExpire API - Enterprise Edition"}

# ===========================
# FILE UPLOAD
# ===========================

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
    
    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {settings.MAX_FILE_SIZE_MB}MB")
    
    timestamp = int(time.time())
    safe_name = f"{timestamp}_{file.filename.replace(' ', '_')}"
    save_path = settings.UPLOAD_DIR / safe_name
    
    with open(save_path, "wb") as f:
        f.write(file_bytes)
    
    doc = Document(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=safe_name,
        mime_type=file.content_type,
        size_bytes=os.path.getsize(save_path),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    log_audit(db, current_user.username, "upload", f"Uploaded {file.filename}")
    
    return {
        "status": "success",
        "original_filename": file.filename,
        "saved_filename": safe_name,
        "saved_path": str(save_path),
        "mime_type": file.content_type,
        "size_bytes": os.path.getsize(save_path),
        "uploaded_at": timestamp,
    }

# ===========================
# OCR TEXT EXTRACTION
# ===========================

def extract_text_from_file(file_path: Path):
    if not file_path.exists():
        return None, "File not found"
    
    ext = file_path.suffix.lower()
    try:
        content = []
        
        if ext == ".pdf":
            pdf_pages = convert_from_path(str(file_path))
            pages = len(pdf_pages)
            for i, page in enumerate(pdf_pages, start=1):
                page_text = image_to_string(page)
                content.append({"page": i, "text": page_text.strip()})
        elif ext in [".png", ".jpg", ".jpeg"]:
            img = Image.open(file_path)
            page_text = image_to_string(img)
            content.append({"page": 1, "text": page_text.strip()})
            pages = 1
        else:
            return None, "Unsupported file type for OCR"
    except Exception as e:
        return None, str(e)
    
    return {"pages": pages, "content": content}, None

@app.get("/extract-text")
def extract_text_endpoint(
    filename: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.stored_filename == filename,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = settings.UPLOAD_DIR / filename
    text_data, error = extract_text_from_file(file_path)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return text_data

# ===========================
# DATE EXTRACTION
# ===========================

def extract_dates(text_content):
    results = []
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"
    ]
    
    matches = []
    for pattern in date_patterns:
        matches.extend(re.findall(pattern, text_content))
    
    for match in matches:
        iso_date = None
        detected_format = None
        for fmt_try in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                dt = datetime.strptime(match, fmt_try)
                iso_date = dt.date().isoformat()
                detected_format = fmt_try
                break
            except:
                continue
        
        if iso_date:
            today = datetime.today().date()
            days_until_expiration = (dt.date() - today).days
            is_expired = days_until_expiration < 0
        else:
            days_until_expiration = None
            is_expired = None
        
        results.append({
            "date_raw": match,
            "date_iso": iso_date,
            "detected_format": detected_format,
            "is_expired": is_expired,
            "days_until_expiration": days_until_expiration
        })
    
    return results

# ===========================
# PROCESS FILES
# ===========================

@app.get("/process")
def process_files(
    filenames: list[str] = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    summary = []
    
    for fname in filenames:
        doc = db.query(Document).filter(
            Document.stored_filename == fname,
            Document.user_id == current_user.id
        ).first()
        if not doc:
            summary.append({"filename": fname, "error": "File not found"})
            continue

        file_path = settings.UPLOAD_DIR / fname
        text_data, error = extract_text_from_file(file_path)
        if error:
            summary.append({"filename": fname, "error": error})
            continue
        
        full_text = " ".join([p["text"] for p in text_data["content"]])
        dates_found = extract_dates(full_text)

        db.query(DocumentDate).filter(DocumentDate.document_id == doc.id).delete()
        for result in dates_found:
            db.add(DocumentDate(
                document_id=doc.id,
                date_raw=result.get("date_raw"),
                date_iso=result.get("date_iso"),
                detected_format=result.get("detected_format"),
                is_expired=result.get("is_expired"),
                days_until_expiration=result.get("days_until_expiration")
            ))
        doc.last_processed_at = datetime.utcnow()
        db.commit()
        
        summary.append({
            "filename": fname,
            "pages_extracted": text_data["pages"],
            "dates_detected": len(dates_found),
            "results": dates_found
        })
    
    log_audit(db, current_user.username, "process", f"Processed {len(summary)} files")
    
    return {"status": "success", "files_processed": len(summary), "summary": summary}

# ===========================
# EXPIRATION ALERT ENDPOINTS (NEW)
# ===========================

@app.get("/documents/expiring-soon")
def get_expiring_documents(
    days: int = 7,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cutoff = days
    doc_dates = db.query(DocumentDate, Document).filter(
        DocumentDate.document_id == Document.id,
        Document.user_id == current_user.id,
        DocumentDate.days_until_expiration != None,
        DocumentDate.days_until_expiration >= 0,
        DocumentDate.days_until_expiration <= cutoff
    ).all()
    
    results = []
    for date_row, doc in doc_dates:
        results.append({
            "document": {
                "original_filename": doc.original_filename,
                "stored_filename": doc.stored_filename
            },
            "date_raw": date_row.date_raw,
            "date_iso": date_row.date_iso,
            "days_until_expiration": date_row.days_until_expiration
        })
    
    return {"days": days, "results": results}

# ===========================
# AI ANALYSIS
# ===========================

@app.post("/ai/analyze")
def analyze_with_ai(
    request: AIAnalyzeRequest,
    current_user: User = Depends(get_current_active_user)
):
    return ai_analyzer.analyze_dates(request.results)

# ===========================
# AUDIT LOGS (ADMIN)
# ===========================

@app.get("/audit/logs")
def get_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return {
        "logs": [
            {
                "username": log.username,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address
            }
            for log in logs
        ]
    }

# ===========================
# CLOUD FILES
# ===========================

@app.get("/cloud/{provider}/files")
def list_cloud_files(
    provider: str,
    current_user: User = Depends(get_current_active_user)
):
    if provider == "google_drive":
        files = GoogleDriveConnector.list_files(current_user.id)
    elif provider == "dropbox":
        files = DropboxConnector.list_files(current_user.id)
    elif provider == "onedrive":
        files = OneDriveConnector.list_files(current_user.id)
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    
    return {"files": files}

@app.post("/cloud/{provider}/import")
def import_cloud_files(
    provider: str,
    request: CloudImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if provider not in ["google_drive", "dropbox", "onedrive"]:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    
    imported = []
    for file_id in request.file_ids:
        timestamp = int(time.time())
        safe_name = f"{timestamp}_{file_id.replace(' ', '_')}"
        save_path = settings.UPLOAD_DIR / safe_name
        
        if provider == "google_drive":
            GoogleDriveConnector.download_file(current_user.id, file_id, save_path)
        elif provider == "dropbox":
            DropboxConnector.download_file(current_user.id, file_id, save_path)
        else:
            OneDriveConnector.download_file(current_user.id, file_id, save_path)
        
        doc = Document(
            user_id=current_user.id,
            original_filename=file_id,
            stored_filename=safe_name,
            mime_type="application/octet-stream",
            size_bytes=os.path.getsize(save_path),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        imported.append({
            "original_filename": file_id,
            "saved_filename": safe_name,
            "saved_path": str(save_path),
            "mime_type": "application/octet-stream",
            "size_bytes": os.path.getsize(save_path)
        })
    
    log_audit(db, current_user.username, "cloud_import", f"Imported {len(imported)} file(s) from {provider}")
    return {"status": "success", "imported_files": imported}

# ===========================
# FILE MANAGEMENT
# ===========================

@app.delete("/files/{filename}")
def delete_file(
    filename: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.stored_filename == filename,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = settings.UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink()
    
    db.query(DocumentDate).filter(DocumentDate.document_id == doc.id).delete()
    db.delete(doc)
    db.commit()
    
    log_audit(db, current_user.username, "delete", f"Deleted {doc.original_filename}")
    return {"status": "success"}

@app.post("/admin/test-email")
def test_email(
    current_user: User = Depends(require_admin)
):
    send_email(
        current_user.email,
        "DocExpire Test Email",
        "This is a test notification from DocExpire."
    )
    return {"status": "success", "message": "Test email sent"}

# ===========================
# STARTUP / SHUTDOWN (IMPORTANT)
# ===========================

@app.on_event("startup")
def on_startup():
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()
