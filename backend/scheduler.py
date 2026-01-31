from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import SessionLocal, User, Document, DocumentDate
from email_service import send_email
from config import settings

scheduler = BackgroundScheduler()


def send_expiration_alerts():
    """
    Send expiration alerts for documents expiring soon.
    """
    db: Session = SessionLocal()
    now = datetime.utcnow()
    try:
        expiring = db.query(DocumentDate, Document, User).filter(
            DocumentDate.document_id == Document.id,
            Document.user_id == User.id,
            DocumentDate.days_until_expiration != None,
            DocumentDate.days_until_expiration >= 0,
            DocumentDate.days_until_expiration <= settings.ALERT_DAYS
        ).all()

        for date_row, doc, user in expiring:
            if date_row.last_alerted_at and (now - date_row.last_alerted_at).days < 1:
                continue
            if not user.email:
                continue

            send_email(
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
            date_row.last_alerted_at = now

        db.commit()
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            send_expiration_alerts,
            trigger="interval",
            days=1,
            next_run_time=datetime.utcnow() + timedelta(seconds=30),
            id="daily_expiration_alerts",
            replace_existing=True,
        )
        scheduler.start()
        print("Scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped")
