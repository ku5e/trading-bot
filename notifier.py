"""
Thin email notifier — imported by strategies so they can send per-action alerts
without creating a circular dependency on scheduler.py.
"""

import smtplib
import logging
from email.mime.text import MIMEText
import config

log = logging.getLogger(__name__)


def send_email(subject, body):
    if not config.EMAIL_SMTP or not config.EMAIL_TO:
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM or config.EMAIL_USER or "trading-bot@ku5e.com"
    msg["To"] = config.EMAIL_TO
    try:
        with smtplib.SMTP(config.EMAIL_SMTP, config.EMAIL_PORT) as server:
            if config.EMAIL_PASS:
                server.starttls()
                server.login(config.EMAIL_USER, config.EMAIL_PASS)
            server.send_message(msg)
        log.info(f"[email] sent: {subject}")
    except Exception as e:
        log.error(f"[email] failed: {e}")


def action(subject, body):
    """Send a per-action alert. Subject is prefixed with [BOT ACTION]."""
    send_email(f"[BOT ACTION] {subject}", body)
