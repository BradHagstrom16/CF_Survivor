# send_reminders.py
"""Daily reminder script for the CFB Survivor pool.

Run every day at 09:59 AM America/Chicago.
  • Friday   → 25‑hour warning
  • Saturday → 1‑hour warning
"""

import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pytz

from app import app
from models import User, Week, Pick

CHICAGO = pytz.timezone("America/Chicago")


def current_week():
    """Return the active week with a timezone‑aware deadline."""
    with app.app_context():
        week = Week.query.filter_by(is_active=True).first()
        if week and week.deadline.tzinfo is None:
            week.deadline = CHICAGO.localize(week.deadline)
        return week


def users_without_picks(week):
    """Active users who have not submitted a pick for the supplied week."""
    with app.app_context():
        active_users = User.query.filter_by(is_eliminated=False).all()
        picked_ids = {p.user_id for p in Pick.query.filter_by(week_id=week.id)}
        return [u for u in active_users if u.id not in picked_ids]


def send_email(to_addr: str, subject: str, body: str):
    """Send a plain‑text email using credentials from environment vars."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    from_addr = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]

    msg = MIMEText(body)
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(from_addr, password)
        server.send_message(msg)


def main():
    now = datetime.now(CHICAGO)
    if now.weekday() not in (4, 5):           # 4 = Friday, 5 = Saturday
        return

    week = current_week()
    if not week or now > week.deadline:
        return

    if now.weekday() == 4 and week.deadline.weekday() != 5:
        return  # Friday check: only send if deadline is Saturday
    if now.weekday() == 5 and week.deadline.date() != now.date():
        return  # Saturday check: only send if deadline is today

    recipients = users_without_picks(week)
    if not recipients:
        return

    hours_left = int((week.deadline - now).total_seconds() // 3600)
    pool_url = os.environ.get("POOL_URL", "https://example.com")

    for user in recipients:
        body = (
            f"Hi {user.username},\n\n"
            f"You still need to make your Week {week.week_number} pick.\n"
            f"Deadline: {week.deadline.strftime('%A %I:%M %p %Z')}\n"
            f"Time remaining: {hours_left} hour(s)\n\n"
            f"Make your pick now: {pool_url}/pick/{week.week_number}\n\n"
            f"Good luck!\n"
        )
        subject = f"CFB Survivor Week {week.week_number} reminder"
        send_email(user.email, subject, body)


if __name__ == "__main__":
    main()
