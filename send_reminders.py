"""Daily reminder script for the CFB Survivor pool.

Run every day at 09:59 AM America/Chicago.
  - Friday   -> 25-hour warning
  - Saturday -> 1-hour warning
"""

import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText

from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from models import User, Week, Pick

logger = logging.getLogger(__name__)

app = create_app()

CHICAGO = ZoneInfo("America/Chicago")


def current_week():
    """Return the active week with a timezone-aware deadline."""
    with app.app_context():
        week = Week.query.filter_by(is_active=True).first()
        if week:
            week._aware_deadline = week.deadline.replace(tzinfo=CHICAGO) if week.deadline else None
        return week


def users_without_picks(week):
    """Active users who have not submitted a pick for the supplied week."""
    with app.app_context():
        active_users = User.query.filter_by(is_eliminated=False).all()
        picked_ids = {p.user_id for p in Pick.query.filter_by(week_id=week.id)}
        return [u for u in active_users if u.id not in picked_ids]


def send_email(to_addr, subject, body):
    """Send a plain-text email using config from the app."""
    with app.app_context():
        email_address = app.config.get('EMAIL_ADDRESS', '')
        email_password = app.config.get('EMAIL_PASSWORD', '')
        smtp_server = app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = app.config.get('SMTP_PORT', 587)

    if not email_address or not email_password:
        logger.error("Email credentials not configured!")
        return False

    msg = MIMEText(body)
    msg["From"] = email_address
    msg["To"] = to_addr
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)
        logger.info("Email sent to %s", to_addr)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_addr, e)
        return False


def main():
    now = datetime.now(CHICAGO)
    weekday = now.weekday()

    print(f"\nReminder Check: {now.strftime('%A, %B %d, %Y at %I:%M %p %Z')}")

    # Only run on Friday (4) or Saturday (5)
    if weekday not in (4, 5):
        print(f"Today is {now.strftime('%A')} - no reminders")
        return

    week = current_week()
    if not week:
        print("No active week found")
        return

    if now > week._aware_deadline:
        print(f"Deadline for Week {week.week_number} has passed")
        return

    if weekday == 4 and week._aware_deadline.weekday() != 5:
        print("Friday but deadline is not Saturday")
        return

    if weekday == 5 and week._aware_deadline.date() != now.date():
        print("Saturday but deadline is not today")
        return

    recipients = users_without_picks(week)
    if not recipients:
        print(f"All users have picks for Week {week.week_number}")
        return

    hours_left = int((week._aware_deadline - now).total_seconds() // 3600)
    reminder_type = "25-hour" if weekday == 4 else "1-hour FINAL"

    with app.app_context():
        pool_url = app.config.get('POOL_URL', 'https://b1gbrad.pythonanywhere.com')

    print(f"Sending {reminder_type} reminders for Week {week.week_number}")
    print(f"Recipients: {len(recipients)} users")

    success_count = 0
    for user in recipients:
        body = f"""Hi {user.username},

You still need to make your Week {week.week_number} pick!

Deadline: {week._aware_deadline.strftime('%A at %I:%M %p %Z')}
Time remaining: {hours_left} hour(s)

Make your pick now: {pool_url}/pick/{week.week_number}

Your status:
- Lives remaining: {user.lives_remaining}
- Cumulative spread: {user.cumulative_spread:.1f}

{'This is your FINAL reminder!' if weekday == 5 else 'You will get one more reminder tomorrow morning.'}

Good luck!
"""

        if weekday == 5:
            subject = f"FINAL: Week {week.week_number} pick due in 1 hour!"
        else:
            subject = f"Week {week.week_number} pick due tomorrow"

        if send_email(user.email, subject, body):
            success_count += 1

    print(f"\nSummary: {success_count}/{len(recipients)} emails sent successfully")


if __name__ == "__main__":
    main()
