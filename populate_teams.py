from app import app, db
from models import Team

# All 49 teams from your AP Top 25 preseason poll
teams_data = [
    'Texas', 'Penn State', 'Ohio State', 'Clemson', 'Georgia', 'Notre Dame', 
    'Oregon', 'Alabama', 'LSU', 'Miami', 'Arizona State', 'Illinois', 'South Carolina', 
    'Michigan', 'Florida', 'SMU', 'Kansas State', 'Oklahoma', 'Texas A&M', 'Indiana', 'Ole Miss', 
    'Iowa State', 'Texas Tech', 'Tennessee', 'Boise State', 'BYU', 'Utah', 'Baylor', 'Louisville', 'USC', 'Georgia Tech', 'Missouri', 
    'Tulane', 'Nebraska', 'UNLV', 'Toledo', 'Auburn', 'James Madison', 'Memphis', 'Florida State', 'Duke', 'Liberty', 'Navy', 'Iowa', 
    'TCU', 'Pittsburgh', 'Army', 'Colorado', 'Louisiana-Lafayette'

]

def populate_teams():
    """Add all teams to the database"""
    with app.app_context():
        # Check if teams already exist
        existing_count = Team.query.count()
        if existing_count > 0:
            print(f"Database already has {existing_count} teams. Skipping population.")
            return
        
        # Add each team
        for team_name in teams_data:
            team = Team(name=team_name)
            db.session.add(team)
            print(f"Added: {team_name}")
        
        # Commit all teams to database
        db.session.commit()
        print(f"\nSuccessfully added {len(teams_data)} teams to the database!")

if __name__ == "__main__":
    populate_teams()