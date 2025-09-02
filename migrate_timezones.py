"""
One-time migration to convert all naive datetimes to timezone-aware
Run this once to fix all existing data
"""

from app import app, db
from models import Week, Game, Pick
from timezone_utils import POOL_TZ, UTC_TZ
from sqlalchemy import text

def migrate_to_timezone_aware():
    """Convert all naive datetimes in database to timezone-aware"""
    
    with app.app_context():
        print("Starting timezone migration...")
        
        # Migrate Week deadlines and start_dates
        weeks = Week.query.all()
        for week in weeks:
            if week.deadline and week.deadline.tzinfo is None:
                # Assume existing naive times were meant to be in pool timezone
                week.deadline = POOL_TZ.localize(week.deadline)
                print(f"Migrated Week {week.week_number} deadline")
            
            if week.start_date and week.start_date.tzinfo is None:
                week.start_date = POOL_TZ.localize(week.start_date)
                print(f"Migrated Week {week.week_number} start_date")
        
        # Migrate Game times
        games = Game.query.all()
        for game in games:
            if game.game_time and game.game_time.tzinfo is None:
                # Assume game times were in pool timezone
                game.game_time = POOL_TZ.localize(game.game_time)
                print(f"Migrated game {game.id} time")
        
        # Migrate Pick created_at times
        picks = Pick.query.all()
        for pick in picks:
            if pick.created_at and pick.created_at.tzinfo is None:
                # Assume these were stored in UTC (default for most databases)
                pick.created_at = UTC_TZ.localize(pick.created_at)
                print(f"Migrated pick {pick.id} created_at")
        
        # Commit all changes
        db.session.commit()
        print("Timezone migration complete!")

if __name__ == "__main__":
    migrate_to_timezone_aware()