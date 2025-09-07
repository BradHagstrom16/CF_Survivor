"""Daily reminder script for the CFB Survivor pool.

Run every day at 09:59 AM America/Chicago.
  • Friday   → 25-hour warning
  • Saturday → 1-hour warning
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pytz

# Add project path for PythonAnywhere
project_home = '/home/B1GBrad/CF_Survivor'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment for imports
os.environ['ENVIRONMENT'] = 'production'

from app import app
from models import User, Week, Pick

# Import email configuration
try:
    from email_config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, POOL_URL
    CONFIG_LOADED = True
except ImportError:
    print("ERROR: email_config.py not found!")
    print("Create email_config.py with EMAIL_ADDRESS and EMAIL_PASSWORD")
    CONFIG_LOADED = False
    # Fallback values
    EMAIL_ADDRESS = ""
    EMAIL_PASSWORD = ""
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    POOL_URL = "https://b1gbrad.pythonanywhere.com"

CHICAGO = pytz.timezone("America/Chicago")


def current_week():
    """Return the active week with a timezone-aware deadline."""
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
    """Send a plain-text email."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("ERROR: Email credentials not configured!")
        return False
    
    msg = MIMEText(body)
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_addr
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email sent to {to_addr}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_addr}: {e}")
        return False


def main():
    now = datetime.now(CHICAGO)
    weekday = now.weekday()
    
    print(f"\n{'='*60}")
    print(f"Reminder Check: {now.strftime('%A, %B %d, %Y at %I:%M %p %Z')}")
    print(f"{'='*60}")
    
    if not CONFIG_LOADED:
        print("Cannot proceed without email configuration")
        return
    
    # Only run on Friday (4) or Saturday (5)
    if weekday not in (4, 5):
        print(f"Today is {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][weekday]} - no reminders")
        return

    week = current_week()
    if not week:
        print("No active week found")
        return
        
    if now > week.deadline:
        print(f"Deadline for Week {week.week_number} has passed")
        return

    # Friday: only send if deadline is Saturday
    if weekday == 4 and week.deadline.weekday() != 5:
        print("Friday but deadline is not Saturday")
        return
        
    # Saturday: only send if deadline is today
    if weekday == 5 and week.deadline.date() != now.date():
        print("Saturday but deadline is not today")
        return

    recipients = users_without_picks(week)
    if not recipients:
        print(f"All users have picks for Week {week.week_number}")
        return

    hours_left = int((week.deadline - now).total_seconds() // 3600)
    reminder_type = "25-hour" if weekday == 4 else "1-hour FINAL"
    
    print(f"Sending {reminder_type} reminders for Week {week.week_number}")
    print(f"Recipients: {len(recipients)} users")
    
    success_count = 0
    for user in recipients:
        body = f"""Hi {user.username},

You still need to make your Week {week.week_number} pick!

Deadline: {week.deadline.strftime('%A at %I:%M %p %Z')}
Time remaining: {hours_left} hour(s)

Make your pick now: {POOL_URL}/pick/{week.week_number}

Your status:
• Lives remaining: {user.lives_remaining}
• Cumulative spread: {user.cumulative_spread:.1f}

{'This is your FINAL reminder!' if weekday == 5 else 'You will get one more reminder tomorrow morning.'}

Good luck!
"""
        
        if weekday == 5:  # Saturday - FINAL
            subject = f"🚨 FINAL: Week {week.week_number} pick due in 1 hour!"
        else:  # Friday
            subject = f"📅 Week {week.week_number} pick due tomorrow"
            
        if send_email(user.email, subject, body):
            success_count += 1
    
    print(f"\nSummary: {success_count}/{len(recipients)} emails sent successfully")


if __name__ == "__main__":
    main()