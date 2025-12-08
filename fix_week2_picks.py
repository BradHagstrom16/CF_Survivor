"""
Script to change Week 2 auto-picks from Louisville to Memphis
for specific users: Johnny p, atm, shane_sup
"""

from app import app, db
from models import User, Team, Week, Pick

def fix_week2_autopicks():
    """Change Week 2 picks from Louisville to Memphis for specified users"""
    
    with app.app_context():
        print("\n" + "="*60)
        print("FIXING WEEK 2 AUTO-PICKS")
        print("="*60)
        
        # Find the users
        usernames = ["Johnny p", "atm", "shane_sup"]
        users_to_fix = []
        
        for username in usernames:
            user = User.query.filter_by(username=username).first()
            if user:
                users_to_fix.append(user)
                print(f"✓ Found user: {username}")
            else:
                print(f"✗ User not found: {username}")
        
        if not users_to_fix:
            print("\n❌ No users found to fix!")
            return
        
        # Find Week 2
        week2 = Week.query.filter_by(week_number=2).first()
        if not week2:
            print("\n❌ Week 2 not found!")
            return
        print(f"\n✓ Found Week 2 (ID: {week2.id})")
        
        # Find Louisville and Memphis teams
        louisville = Team.query.filter_by(name="Louisville").first()
        memphis = Team.query.filter_by(name="Memphis").first()
        
        if not louisville:
            print("❌ Louisville team not found!")
            return
        if not memphis:
            print("❌ Memphis team not found!")
            return
            
        print(f"✓ Found Louisville (ID: {louisville.id})")
        print(f"✓ Found Memphis (ID: {memphis.id})")
        
        # Process each user
        print("\n" + "-"*60)
        print("Processing picks...")
        print("-"*60)
        
        changes_made = []
        
        for user in users_to_fix:
            # Find their Week 2 pick
            pick = Pick.query.filter_by(
                user_id=user.id,
                week_id=week2.id
            ).first()
            
            if not pick:
                print(f"\n❌ {user.username}: No Week 2 pick found")
                continue
            
            if pick.team_id == louisville.id:
                # Change to Memphis
                old_team = pick.team.name
                pick.team_id = memphis.id
                
                print(f"\n✓ {user.username}:")
                print(f"  Changed from: {old_team}")
                print(f"  Changed to: {memphis.name}")
                
                changes_made.append({
                    'user': user.username,
                    'old_team': old_team,
                    'new_team': memphis.name
                })
                
            elif pick.team_id == memphis.id:
                print(f"\n✓ {user.username}: Already has Memphis (no change needed)")
            else:
                current_team = pick.team.name
                print(f"\n⚠️  {user.username}: Has {current_team} (not Louisville)")
        
        if not changes_made:
            print("\n❌ No changes needed - no users had Louisville")
            return
        
        # Show summary
        print("\n" + "="*60)
        print("SUMMARY OF CHANGES")
        print("="*60)
        
        for change in changes_made:
            print(f"• {change['user']}: {change['old_team']} → {change['new_team']}")
        
        # Confirm changes
        print("\n" + "-"*60)
        confirm = input(f"Apply these {len(changes_made)} changes? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            # Commit changes
            db.session.commit()
            print("✅ Changes saved to database!")
            
            # Recalculate cumulative spreads
            print("\nRecalculating cumulative spreads...")
            for user in users_to_fix:
                user.calculate_cumulative_spread()
            db.session.commit()
            print("✅ Cumulative spreads updated!")
            
            print("\n" + "="*60)
            print("✅ ALL CHANGES COMPLETE!")
            print("="*60)
            
            # Show final status
            print("\nFinal Week 2 picks:")
            for user in users_to_fix:
                pick = Pick.query.filter_by(user_id=user.id, week_id=week2.id).first()
                if pick:
                    print(f"  {user.username}: {pick.team.name}")
                    
        else:
            print("\n❌ Changes cancelled - no modifications made")

def main():
    """Main function"""
    print("CFB SURVIVOR POOL - FIX WEEK 2 AUTO-PICKS")
    print("This will change Louisville picks to Memphis for:")
    print("  • Johnny p")
    print("  • atm")
    print("  • shane_sup")
    
    fix_week2_autopicks()

if __name__ == "__main__":
    main()