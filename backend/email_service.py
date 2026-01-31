import smtplib
from email.message import EmailMessage
import os


def send_email(to_email: str, subject: str, body: str):
    """
    Sends an email using SMTP.
    Fails safely if email is not configured.
    """

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL")

    # If email is not configured, do not crash the app
    if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email]):
        print("Email not configured. Skipping email send.")
        return

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Email send failed: {e}")

