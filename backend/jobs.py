import logging
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from database import SessionLocal, Document, DocumentDate, User
from email_service import send_email
from processing import process_documents
from config import settings

logger = logging.getLogger(__name__)


def process_documents_job(user_id: int, filenames: List[str]) -> Dict:
    db: Session = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.user_id == user_id, Document.stored_filename.in_(filenames))
            .all()
        )
        found = {doc.stored_filename for doc in docs}
        missing = [fname for fname in filenames if fname not in found]

        summary = process_documents(db, docs)
        for fname in missing:
            summary.append({"filename": fname, "stored_filename": fname, "error": "File not found"})

        user = db.query(User).filter(User.id == user_id).first()
        if user:
            from auth import log_audit

            log_audit(db, user.username, "process", f"Processed {len(summary)} files")

        result = {
            "status": "success",
            "files_processed": len(summary),
            "summary": summary,
        }
        logger.info("processing_complete", extra={"user_id": user_id, "files": len(summary)})
        return result
    finally:
        db.close()


def send_expiration_alerts_job() -> Dict:
    db: Session = SessionLocal()
    now = datetime.utcnow()
    sent = 0
    skipped = 0
    try:
        expiring = (
            db.query(DocumentDate, Document, User)
            .filter(
                DocumentDate.document_id == Document.id,
                Document.user_id == User.id,
                DocumentDate.days_until_expiration.isnot(None),
                DocumentDate.days_until_expiration >= 0,
                DocumentDate.days_until_expiration <= settings.ALERT_DAYS,
            )
            .all()
        )

        for date_row, doc, user in expiring:
            if date_row.last_alerted_at and (now - date_row.last_alerted_at).days < 1:
                skipped += 1
                continue
            if not user.email:
                skipped += 1
                continue

            result = send_email(
                to_email=user.email,
                subject="DocExpire Alert: Document Expiring Soon",
                body=(
                    f"Hello {user.full_name},\n\n"
                    f"Your document \"{doc.original_filename}\" has a date "
                    f"expiring in {date_row.days_until_expiration} day(s).\n\n"
                    f"Date detected: {date_row.date_raw}\n\n"
                    "Please review and take action.\n\n"
                    "— DocExpire System"
                ),
            )
            if not result.sent:
                skipped += 1
                continue

            date_row.last_alerted_at = now
            sent += 1

        db.commit()
        logger.info("alerts_sent", extra={"sent": sent, "skipped": skipped})
        return {"sent": sent, "skipped": skipped}
    finally:
        db.close()
