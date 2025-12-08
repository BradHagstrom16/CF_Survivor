"""
Migration: Add Playoff Fields to Week Table
Adds support for playoff weeks with custom display names
"""

from app import app, db
from models import Week
from sqlalchemy import text

def migrate_playoff_fields():
    """Add is_playoff_week and round_name fields to Week table"""
    
    with app.app_context():
        print("=" * 60)
        print("PLAYOFF FIELDS MIGRATION")
        print("=" * 60)
        
        # Check if fields already exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('week')]
        
        needs_migration = False
        
        if 'is_playoff_week' not in columns:
            needs_migration = True
            print("\n✓ Need to add 'is_playoff_week' field")
        else:
            print("\n⚠ Field 'is_playoff_week' already exists")
        
        if 'round_name' not in columns:
            needs_migration = True
            print("✓ Need to add 'round_name' field")
        else:
            print("⚠ Field 'round_name' already exists")
        
        if not needs_migration:
            print("\n" + "=" * 60)
            print("Migration not needed - fields already exist!")
            print("=" * 60)
            return
        
        print("\n" + "-" * 60)
        print("This migration will:")
        print("1. Add 'is_playoff_week' column (Boolean, default False)")
        print("2. Add 'round_name' column (String, nullable)")
        print("3. Set all existing weeks to is_playoff_week=False")
        print("-" * 60)
        
        confirm = input("\nProceed with migration? Type 'YES' to confirm: ")
        
        if confirm != 'YES':
            print("Migration cancelled.")
            return
        
        print("\nStarting migration...")
        
        try:
            # Add is_playoff_week column
            if 'is_playoff_week' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE week ADD COLUMN is_playoff_week BOOLEAN DEFAULT 0"
                    ))
                    conn.commit()
                print("✓ Added 'is_playoff_week' column")
            
            # Add round_name column
            if 'round_name' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE week ADD COLUMN round_name VARCHAR(100)"
                    ))
                    conn.commit()
                print("✓ Added 'round_name' column")
            
            # Set defaults for existing weeks
            weeks = Week.query.all()
            for week in weeks:
                if not hasattr(week, 'is_playoff_week') or week.is_playoff_week is None:
                    week.is_playoff_week = False
            
            db.session.commit()
            print(f"✓ Set defaults for {len(weeks)} existing weeks")
            
            print("\n" + "=" * 60)
            print("MIGRATION COMPLETE!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Restart your Flask app")
            print("2. Create Week 16 and set is_playoff_week=True")
            print("3. Set round_name for special weeks:")
            print("   - Week 15: 'Conference Championship Week'")
            print("   - Week 16: 'CFP Round 1'")
            print("   - Week 17: 'CFP Quarterfinals'")
            print("   - Week 18: 'CFP Semifinals'")
            print("   - Week 19: 'CFP Championship'")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("Rolling back changes...")
            db.session.rollback()
            return False
        
        return True

def verify_migration():
    """Verify that migration was successful"""
    with app.app_context():
        print("\n" + "=" * 60)
        print("VERIFYING MIGRATION")
        print("=" * 60)
        
        inspector = db.inspect(db.engine)
        columns = {col['name']: col for col in inspector.get_columns('week')}
        
        # Check is_playoff_week
        if 'is_playoff_week' in columns:
            print("✓ Field 'is_playoff_week' exists")
            print(f"  Type: {columns['is_playoff_week']['type']}")
        else:
            print("❌ Field 'is_playoff_week' NOT FOUND")
        
        # Check round_name
        if 'round_name' in columns:
            print("✓ Field 'round_name' exists")
            print(f"  Type: {columns['round_name']['type']}")
        else:
            print("❌ Field 'round_name' NOT FOUND")
        
        # Check existing weeks
        weeks = Week.query.all()
        print(f"\n✓ Found {len(weeks)} existing weeks")
        print("\nWeek details:")
        for week in weeks:
            playoff_status = "PLAYOFF" if hasattr(week, 'is_playoff_week') and week.is_playoff_week else "Regular"
            round_name = getattr(week, 'round_name', None) or "(not set)"
            print(f"  Week {week.week_number}: {playoff_status} - {round_name}")
        
        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETE")
        print("=" * 60)

def set_week_display_names():
    """Helper to set display names for existing weeks"""
    with app.app_context():
        print("\n" + "=" * 60)
        print("SET DISPLAY NAMES FOR SPECIAL WEEKS")
        print("=" * 60)
        
        # Set Conference Championship Week display name
        week_15 = Week.query.filter_by(week_number=15).first()
        if week_15:
            week_15.round_name = "Conference Championship Week"
            print("✓ Set Week 15 display name: 'Conference Championship Week'")
        else:
            print("⚠ Week 15 not found - create it first")
        
        db.session.commit()
        print("\nDisplay names updated successfully!")
        print("\nFor playoff weeks (16-19), set round_name when creating them:")
        print("  Week 16: 'CFP Round 1'")
        print("  Week 17: 'CFP Quarterfinals'")
        print("  Week 18: 'CFP Semifinals'")
        print("  Week 19: 'CFP Championship'")
        print("=" * 60)

if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("PLAYOFF MIGRATION TOOL")
    print("=" * 60)
    print("1. Run Migration")
    print("2. Verify Migration")
    print("3. Set Display Names for Special Weeks")
    print("4. Exit")
    print("=" * 60)
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        migrate_playoff_fields()
    elif choice == '2':
        verify_migration()
    elif choice == '3':
        set_week_display_names()
    elif choice == '4':
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid option")
