"""
Smart Daily Email Reminder System for CFB Survivor Pool
Runs DAILY at 9:59 AM Central but only sends emails on Fridays and Saturdays
Perfect for PythonAnywhere free tier (1 scheduled task)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Load your Flask app context
from app import app, db
from models import User, Week, Pick

# Load environment variables
load_dotenv()

EMAIL_ADDRESS=bhagstrom0@gmail.com \
EMAIL_PASSWORD=fake password \
/usr/bin/python3 /home/BIGBrad/CF_Survivor/send_reminders_daily.py


class SmartDailyReminder:
    def __init__(self):
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.pool_name = "CFB Survivor Pool"
        self.pool_url = os.getenv('POOL_URL', 'https://B1GBrad.pythonanywhere.com')
        
        # Timezone
        self.chicago_tz = pytz.timezone('America/Chicago')
        
    def should_send_reminders(self):
        """
        Determine if today is a day we should send reminders
        Returns: ('25hour', week) for Friday, ('1hour', week) for Saturday, or (None, None)
        """
        now = datetime.now(self.chicago_tz)
        weekday = now.weekday()  # Monday=0, Friday=4, Saturday=5
        
        with app.app_context():
            # Get current active week
            current_week = Week.query.filter_by(is_active=True).first()
            
            if not current_week:
                print("No active week found")
                return None, None
            
            # Check if deadline has passed
            deadline = current_week.deadline
            if deadline.tzinfo is None:
                deadline = self.chicago_tz.localize(deadline)
            
            if now > deadline:
                print(f"Deadline for Week {current_week.week_number} has already passed")
                return None, None
            
            # Check what day it is
            if weekday == 4:  # Friday
                # Verify deadline is tomorrow (Saturday)
                deadline_day = deadline.weekday()
                if deadline_day == 5:  # Saturday
                    print(f"✅ It's Friday! Sending 25-hour reminder for Week {current_week.week_number}")
                    return '25hour', current_week
                else:
                    print(f"It's Friday but deadline is not Saturday (it's {deadline.strftime('%A')})")
                    return None, None
                    
            elif weekday == 5:  # Saturday
                # Verify deadline is today
                if deadline.date() == now.date():
                    print(f"✅ It's Saturday! Sending 1-hour FINAL reminder for Week {current_week.week_number}")
                    return '1hour', current_week
                else:
                    print(f"It's Saturday but deadline is not today (it's {deadline.strftime('%B %d')})")
                    return None, None
            else:
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                print(f"It's {day_names[weekday]} - no reminders to send today")
                return None, None
    
    def get_users_without_picks(self, week):
        """Get all active users who haven't made a pick for the given week"""
        with app.app_context():
            # Get all active users
            active_users = User.query.filter_by(is_eliminated=False).all()
            
            # Get users who have already picked
            existing_picks = Pick.query.filter_by(week_id=week.id).all()
            users_with_picks = [pick.user_id for pick in existing_picks]
            
            # Find users without picks
            users_without_picks = [
                user for user in active_users 
                if user.id not in users_with_picks
            ]
            
            print(f"Found {len(users_without_picks)} users without picks for Week {week.week_number}")
            
            return users_without_picks
    
    def calculate_hours_until_deadline(self, deadline):
        """Calculate hours remaining until deadline"""
        current_time = datetime.now(self.chicago_tz)
        if deadline.tzinfo is None:
            deadline = self.chicago_tz.localize(deadline)
        
        time_diff = deadline - current_time
        hours = int(time_diff.total_seconds() / 3600)
        minutes = int((time_diff.total_seconds() % 3600) / 60)
        
        if hours > 0:
            return f"{hours} hours and {minutes} minutes"
        else:
            return f"{minutes} minutes"
    
    def send_reminder_email(self, user, week, reminder_type, server):
        """Send reminder email to a single user using an active SMTP server"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            
            # Email subject based on reminder type
            if reminder_type == '1hour':
                msg['Subject'] = f"🚨 FINAL REMINDER: Week {week.week_number} Pick Due in 1 Hour!"
            else:  # 25hour
                msg['Subject'] = f"📅 Reminder: Week {week.week_number} Pick Due Tomorrow at 10:59 AM"
            
            msg['From'] = self.email_address
            msg['To'] = user.email

             # Ensure deadline is timezone-aware
            deadline = week.deadline
            if deadline.tzinfo is None:
                deadline = self.chicago_tz.localize(deadline)

            
            # Calculate time remaining
            time_remaining = self.calculate_hours_until_deadline(deadline)
            deadline_str = deadline.strftime('%B %d at %I:%M %p %Z')
            
            # Create HTML email body
            if reminder_type == '1hour':
                html_body = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                        .content {{ background-color: #f8f9fa; padding: 20px; margin-top: 20px; }}
                        .button {{ display: inline-block; padding: 12px 30px; background-color: #dc3545; 
                                  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .warning {{ color: #dc3545; font-weight: bold; font-size: 18px; }}
                        .footer {{ margin-top: 20px; padding: 20px; background-color: #343a40; color: white; text-align: center; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🚨 FINAL REMINDER - 1 HOUR LEFT! 🚨</h1>
                            <h2>{self.pool_name}</h2>
                        </div>
                        
                        <div class="content">
                            <p>Hi <strong>{user.username}</strong>,</p>
                            
                            <p class="warning">⏰ Only 1 HOUR left to make your Week {week.week_number} pick!</p>
                            
                            <p><strong>Deadline:</strong> TODAY at 10:59 AM Central</p>
                            
                            <p>You haven't submitted your pick yet. Don't let the auto-pick system choose for you!</p>
                            
                            <center>
                                <a href="{self.pool_url}/pick/{week.week_number}" class="button">
                                    MAKE YOUR PICK NOW
                                </a>
                            </center>
                            
                            <p><strong>Remember:</strong></p>
                            <ul>
                                <li>You have {user.lives_remaining} lives remaining</li>
                                <li>Auto-pick will select the most favored available team if you don't pick</li>
                                <li>Once your team's game starts, your pick is locked</li>
                            </ul>
                            
                            <p style="color: #dc3545; font-weight: bold;">
                                This is your FINAL reminder - pick now or get auto-picked!
                            </p>
                        </div>
                        
                        <div class="footer">
                            <p>Good luck! 🏈</p>
                            <p><a href="{self.pool_url}" style="color: white;">{self.pool_url}</a></p>
                        </div>
                    </div>
                </body>
                </html>
                """
            else:  # 25hour reminder
                html_body = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                        .content {{ background-color: #f8f9fa; padding: 20px; margin-top: 20px; }}
                        .button {{ display: inline-block; padding: 12px 30px; background-color: #28a745; 
                                  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .footer {{ margin-top: 20px; padding: 20px; background-color: #343a40; color: white; text-align: center; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>📅 Week {week.week_number} Pick Reminder</h1>
                            <h2>{self.pool_name}</h2>
                        </div>
                        
                        <div class="content">
                            <p>Hi <strong>{user.username}</strong>,</p>
                            
                            <p>This is your 25-hour reminder that you haven't made your pick for <strong>Week {week.week_number}</strong> yet.</p>
                            
                            <p><strong>Deadline:</strong> Tomorrow (Saturday) at 10:59 AM Central<br>
                            <strong>Time Remaining:</strong> About 25 hours</p>
                            
                            <center>
                                <a href="{self.pool_url}/pick/{week.week_number}" class="button">
                                    Make Your Pick
                                </a>
                            </center>
                            
                            <p><strong>Your Status:</strong></p>
                            <ul>
                                <li>Lives Remaining: {user.lives_remaining}</li>
                                <li>Cumulative Spread: {user.cumulative_spread:.1f}</li>
                            </ul>
                            
                            <p>Don't forget - you'll get one more reminder tomorrow morning!</p>
                        </div>
                        
                        <div class="footer">
                            <p>Good luck this week! 🏈</p>
                            <p><a href="{self.pool_url}" style="color: white;">{self.pool_url}</a></p>
                        </div>
                    </div>
                </body>
                </html>
                """
            
            # Create plain text version
            text_body = f"""
            {self.pool_name} - Week {week.week_number} Reminder
            
            Hi {user.username},
            
            You haven't made your Week {week.week_number} pick yet!
            
            Deadline: {deadline_str}
            Time Remaining: {time_remaining}
            
            Make your pick now: {self.pool_url}/pick/{week.week_number}
            
            Your Status:
            - Lives Remaining: {user.lives_remaining}
            - Cumulative Spread: {user.cumulative_spread:.1f}
            
            Don't forget - auto-pick will choose for you if you miss the deadline!
            
            Good luck!
            """
            
            # Attach parts
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email using existing server connection
            server.send_message(msg)
            
            print(f"✅ Reminder sent to {user.username} ({user.email})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {user.username}: {e}")
            return False
    
    def run_daily_check(self):
        """Main function that runs every day at 9:59 AM Central"""
        print("\n" + "="*60)
        print("DAILY REMINDER CHECK")
        print(f"Time: {datetime.now(self.chicago_tz).strftime('%A, %B %d, %Y at %I:%M %p %Z')}")
        print("="*60)
        
        # Check if we should send reminders today
        reminder_type, week = self.should_send_reminders()
        
        if not reminder_type:
            print("No reminders to send today. Exiting.")
            self.log_activity("No reminders", 0, 0, None)
            return
        
        # Check email configuration
        if not self.email_address or not self.email_password:
            print("❌ Email not configured! Add EMAIL_ADDRESS and EMAIL_PASSWORD to .env file")
            return
        
        # Get users without picks
        users_without_picks = self.get_users_without_picks(week)
        
        if not users_without_picks:
            print(f"All users have made their picks for Week {week.week_number}")
            self.log_activity(reminder_type, 0, 0, week.week_number)
            return
        
        # Send emails
        success_count = 0
        fail_count = 0
        
        # Open a single SMTP connection for all emails
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.email_address, self.email_password)

            for user in users_without_picks:
                if self.send_reminder_email(user, week, reminder_type, server):
                    success_count += 1
                else:
                    fail_count += 1
        
        # Summary
        print("\n" + "-"*60)
        print(f"SUMMARY:")
        print(f"Reminder Type: {reminder_type}")
        print(f"✅ Successfully sent: {success_count} emails")
        if fail_count > 0:
            print(f"❌ Failed: {fail_count} emails")
        print("="*60)
        
        # Log activity
        self.log_activity(reminder_type, success_count, fail_count, week.week_number)
    
    def log_activity(self, reminder_type, success, failed, week_number):
        """Log reminder activity to file"""
        log_dir = "reminder_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"reminders_{datetime.now().strftime('%Y%m')}.log")
        
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now(self.chicago_tz).strftime('%Y-%m-%d %A %I:%M %p')} | ")
            if week_number:
                f.write(f"Week {week_number} | {reminder_type} | ")
                f.write(f"Sent: {success} | Failed: {failed}\n")
            else:
                f.write(f"No reminders needed\n")

def main():
    """Main function"""
    reminder_system = SmartDailyReminder()
    
    reminder_system.run_daily_check()

if __name__ == "__main__":
    main()
