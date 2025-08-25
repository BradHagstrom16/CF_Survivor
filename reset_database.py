"""
Database Reset Script
This script completely resets your survivor pool database,
clearing all data and starting fresh.
"""

from app import app, db
from models import User, Team, Week, Game, Pick
from populate_teams import teams_data
import os

def reset_database():
    """
    Completely resets the database:
    1. Drops all tables
    2. Recreates empty tables
    3. Repopulates teams
    """
    
    with app.app_context():
        print("=" * 50)
        print("DATABASE RESET SCRIPT")
        print("=" * 50)
        
        # Confirm the user wants to proceed
        print("\nThis will DELETE all data including:")
        print("  - All user accounts")
        print("  - All weeks and games")
        print("  - All picks")
        print("  - All teams (will be re-added)")
        
        confirm = input("\nAre you sure you want to reset? Type 'YES' to confirm: ")
        
        if confirm != 'YES':
            print("Reset cancelled.")
            return
        
        print("\nStarting reset process...")
        
        # Step 1: Drop all tables
        print("Dropping all tables...")
        db.drop_all()
        print("✓ All tables dropped")
        
        # Step 2: Recreate empty tables
        print("Creating fresh tables...")
        db.create_all()
        print("✓ Tables created")
        
        # Step 3: Repopulate teams
        print("Adding teams...")
        for team_name in teams_data:
            team = Team(name=team_name)
            db.session.add(team)
        
        db.session.commit()
        print(f"✓ {len(teams_data)} teams added")
        
        print("\n" + "=" * 50)
        print("RESET COMPLETE!")
        print("=" * 50)
        print("\nYour database is now fresh and ready.")
        print("Next steps:")
        print("  1. Create a new admin account")
        print("  2. Create Week 1 in the admin interface")
        print("  3. Import games for Week 1")
        print("  4. Invite your pool participants to register")

if __name__ == "__main__":
    reset_database()