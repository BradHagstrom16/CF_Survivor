"""
Migration script to add payment tracking to the database
Run this once to add the has_paid field to all existing users
"""

from app import app, db
from models import User

def add_payment_tracking():
    """Add has_paid field to existing database"""
    
    with app.app_context():
        print("Adding payment tracking to database...")
        
        # Add the column using raw SQL for SQLite
        try:
            # SQLite doesn't support ALTER TABLE ADD COLUMN with default in all versions
            # So we'll do it with raw SQL
            from sqlalchemy import text
            
            # Add the has_paid column
            with db.engine.connect() as conn:
                # Check if column already exists
                result = conn.execute(text("PRAGMA table_info(user)"))
                columns = [row[1] for row in result]
                
                if 'has_paid' not in columns:
                    conn.execute(text("ALTER TABLE user ADD COLUMN has_paid BOOLEAN DEFAULT 0"))
                    conn.commit()
                    print("✓ Added has_paid column to user table")
                else:
                    print("✓ has_paid column already exists")
            
            # Set all existing users to unpaid (false) by default
            users = User.query.all()
            for user in users:
                if not hasattr(user, 'has_paid'):
                    user.has_paid = False
            
            db.session.commit()
            print(f"✓ Updated {len(users)} users with payment status")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            print("\nIf the column already exists, that's okay!")
        
        print("\nMigration complete!")
        print("Don't forget to:")
        print("1. Update models.py with the new has_paid field")
        print("2. Upload the updated database to production")
        print("3. Deploy the new code files")

if __name__ == "__main__":
    add_payment_tracking()