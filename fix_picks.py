"""
Script to diagnose and fix pick results
Run this to identify and correct any picks that haven't been properly marked
"""

from app import app, db
from models import User, Team, Week, Game, Pick

def diagnose_picks(week_number=None):
    """Diagnose issues with pick results"""
    with app.app_context():
        if week_number:
            weeks = [Week.query.filter_by(week_number=week_number).first()]
        else:
            weeks = Week.query.filter_by(is_complete=True).all()
        
        for week in weeks:
            print(f"\n{'='*60}")
            print(f"Week {week.week_number} Diagnosis")
            print(f"{'='*60}")
            
            # Get all picks for this week
            picks = Pick.query.filter_by(week_id=week.id).all()
            games = Game.query.filter_by(week_id=week.id).all()
            
            # Group picks by team
            picks_by_team = {}
            for pick in picks:
                if pick.team_id not in picks_by_team:
                    picks_by_team[pick.team_id] = []
                picks_by_team[pick.team_id].append(pick)
            
            # Check each team's picks
            issues_found = False
            for team_id, team_picks in picks_by_team.items():
                # Check if all picks for the same team have the same result
                results = [p.is_correct for p in team_picks]
                if len(set(results)) > 1:  # Different results for same team!
                    issues_found = True
                    team = Team.query.get(team_id)
                    print(f"\n⚠️  ISSUE: {team.name} has inconsistent results:")
                    for p in team_picks:
                        print(f"   - {p.user.username}: {p.is_correct} (Pick ID: {p.id})")
                    
                    # Find the game to determine correct result
                    game = Game.query.filter_by(week_id=week.id).filter(
                        db.or_(Game.home_team_id == team_id, 
                               Game.away_team_id == team_id)
                    ).first()
                    
                    if game and game.home_team_won is not None:
                        if team_id == game.home_team_id:
                            correct_result = game.home_team_won
                        else:
                            correct_result = not game.home_team_won
                        
                        print(f"   ✓ Correct result should be: {correct_result}")
            
            if not issues_found:
                print("✅ No issues found with pick results")
            
            # Also check for picks with None result when game is complete
            pending_picks = Pick.query.filter_by(week_id=week.id, is_correct=None).all()
            if pending_picks and week.is_complete:
                print(f"\n⚠️  Found {len(pending_picks)} pending picks in completed week:")
                for p in pending_picks:
                    print(f"   - {p.user.username} picked {p.team.name}")

def fix_pick_results(week_number, dry_run=True):
    """Fix any incorrect pick results"""
    with app.app_context():
        week = Week.query.filter_by(week_number=week_number).first()
        if not week:
            print(f"Week {week_number} not found")
            return
        
        if not week.is_complete:
            print(f"Week {week_number} is not marked as complete")
            return
        
        print(f"\n{'='*60}")
        print(f"Fixing Week {week.week_number} Pick Results")
        print(f"{'='*60}")
        
        picks = Pick.query.filter_by(week_id=week.id).all()
        fixes_made = 0
        
        for pick in picks:
            # Find the game with this team
            game = Game.query.filter_by(week_id=week.id).filter(
                db.or_(Game.home_team_id == pick.team_id, 
                       Game.away_team_id == pick.team_id)
            ).first()
            
            if game and game.home_team_won is not None:
                # Determine what the result should be
                if pick.team_id == game.home_team_id:
                    should_be = game.home_team_won
                else:
                    should_be = not game.home_team_won
                
                # Check if it needs fixing
                if pick.is_correct != should_be:
                    print(f"FIX: {pick.user.username} - {pick.team.name}")
                    print(f"     Was: {pick.is_correct} -> Should be: {should_be}")
                    
                    if not dry_run:
                        pick.is_correct = should_be
                        fixes_made += 1
        
        if fixes_made > 0:
            if not dry_run:
                db.session.commit()
                print(f"\n✅ Fixed {fixes_made} picks")
                
                # Recalculate user lives and spreads
                print("Recalculating user stats...")
                users = User.query.all()
                for user in users:
                    # Count total incorrect picks
                    incorrect_picks = Pick.query.filter_by(
                        user_id=user.id,
                        is_correct=False
                    ).count()
                    
                    # Update lives
                    user.lives_remaining = max(0, 2 - incorrect_picks)
                    user.is_eliminated = (user.lives_remaining == 0)
                    
                    # Recalculate spread
                    user.calculate_cumulative_spread()
                
                db.session.commit()
                print("User stats updated")
            else:
                print(f"\n⚠️  Would fix {fixes_made} picks (dry run mode)")
                print("Run with dry_run=False to apply fixes")
        else:
            print("\n✅ No fixes needed")

def main():
    """Main function for running diagnostics and fixes"""
    print("\n" + "="*60)
    print("PICK RESULTS DIAGNOSTIC & FIX TOOL")
    print("="*60)
    
    while True:
        print("\n1. Diagnose all completed weeks")
        print("2. Diagnose specific week")
        print("3. Fix specific week results")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            diagnose_picks()
        
        elif choice == '2':
            week_num = input("Enter week number: ").strip()
            try:
                diagnose_picks(int(week_num))
            except ValueError:
                print("Invalid week number")
        
        elif choice == '3':
            week_num = input("Enter week number to fix: ").strip()
            try:
                week_num = int(week_num)
                print("\nRunning dry run first...")
                fix_pick_results(week_num, dry_run=True)
                
                confirm = input("\nApply fixes? (y/n): ").strip().lower()
                if confirm == 'y':
                    fix_pick_results(week_num, dry_run=False)
            except ValueError:
                print("Invalid week number")
        
        elif choice == '4':
            break
        
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()