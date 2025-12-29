import os
import smtplib
from email.message import EmailMessage


class NotificationService:
    """
    Email notifications (non-critical).
    Booking logic must NOT depend on email sending.
    """

    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> bool:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)

        # If SMTP not configured, just log and return success (notifications are optional).
        if not smtp_host or not smtp_from:
            print(f"[NotificationService] SMTP not configured. Would email {to_email}: {subject}")
            return True

        msg = EmailMessage()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"[NotificationService] Failed to send email: {e}")
            return False


