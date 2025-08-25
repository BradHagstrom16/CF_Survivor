"""
NCAA Football API Game Importer
This script imports games from The Odds API with intelligent filtering and team matching.
It handles both tracked teams (your 49) and their opponents who might not be in your pool.
"""

import requests
import json
from datetime import datetime, timedelta
from app import app, db
from models import Team, Week, Game

class NCAAFootballAPIImporter:
    """
    Manages the import of college football games from The Odds API.
    This class handles everything from fetching data to intelligently filtering
    games based on your survivor pool rules.
    """
    
    def __init__(self):
        # Your API key is hardcoded here for convenience
        self.api_key = "97cb8b654ed9acfd64eeb7e6e5837ed7"
        self.base_url = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds"
        
        # This mapping translates the API's full team names to your database names
        # Think of it as a translation dictionary between two different naming conventions
        self.team_name_map = {
            'Texas Longhorns': 'Texas',
            'Penn State Nittany Lions': 'Penn State',
            'Ohio State Buckeyes': 'Ohio State',
            'Clemson Tigers': 'Clemson',
            'Georgia Bulldogs': 'Georgia',
            'Notre Dame Fighting Irish': 'Notre Dame',
            'Oregon Ducks': 'Oregon',
            'Alabama Crimson Tide': 'Alabama',
            'LSU Tigers': 'LSU',
            'Miami Hurricanes': 'Miami',
            'Arizona State Sun Devils': 'Arizona State',
            'Illinois Fighting Illini': 'Illinois',
            'South Carolina Gamecocks': 'South Carolina',
            'Michigan Wolverines': 'Michigan',
            'Florida Gators': 'Florida',
            'SMU Mustangs': 'SMU',
            'Kansas State Wildcats': 'Kansas State',
            'Oklahoma Sooners': 'Oklahoma',
            'Texas A&M Aggies': 'Texas A&M',
            'Indiana Hoosiers': 'Indiana',
            'Ole Miss Rebels': 'Ole Miss',
            'Iowa State Cyclones': 'Iowa State',
            'Texas Tech Red Raiders': 'Texas Tech',
            'Tennessee Volunteers': 'Tennessee',
            'Boise State Broncos': 'Boise State',
            'BYU Cougars': 'BYU',
            'Utah Utes': 'Utah',
            'Baylor Bears': 'Baylor',
            'Louisville Cardinals': 'Louisville',
            'USC Trojans': 'USC',
            'Georgia Tech Yellow Jackets': 'Georgia Tech',
            'Missouri Tigers': 'Missouri',
            'Tulane Green Wave': 'Tulane',
            'Nebraska Cornhuskers': 'Nebraska',
            'UNLV Rebels': 'UNLV',
            'Toledo Rockets': 'Toledo',
            'Auburn Tigers': 'Auburn',
            'James Madison Dukes': 'James Madison',
            'Memphis Tigers': 'Memphis',
            'Florida State Seminoles': 'Florida State',
            'Duke Blue Devils': 'Duke',
            'Liberty Flames': 'Liberty',
            'Navy Midshipmen': 'Navy',
            'Iowa Hawkeyes': 'Iowa',
            'TCU Horned Frogs': 'TCU',
            'Pittsburgh Panthers': 'Pittsburgh',
            'Army Black Knights': 'Army',
            'Colorado Buffaloes': 'Colorado',
            'Louisiana Ragin Cajuns': 'Louisiana-Lafayette'
        }
        
        # Create a set of tracked teams for quick lookup
        # This helps us quickly identify if a team is in your pool
        self.tracked_teams = set(self.team_name_map.values())
    
    def fetch_games_for_date_range(self, start_date, end_date):
        """
        Fetches games from the API for a specific date range.
        
        The API returns games with odds from various bookmakers. We'll prefer
        DraftKings but use others if needed. The date filtering happens on the
        API side, which is more efficient than fetching everything and filtering locally.
        """
        # Build the API request parameters
        params = {
            'apiKey': self.api_key,
            'regions': 'us',  # US bookmakers only
            'markets': 'spreads',  # We need point spreads
            'oddsFormat': 'american',  # American odds format
            'commenceTimeFrom': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'commenceTimeTo': end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        print(f"\nFetching games from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        
        try:
            response = requests.get(self.base_url, params=params)
            
            if response.status_code == 200:
                games = response.json()
                
                # The API tells us how many requests we have left
                remaining = response.headers.get('x-requests-remaining', 'unknown')
                used = response.headers.get('x-requests-used', 'unknown')
                
                print(f"Successfully fetched {len(games)} games")
                print(f"API usage: {used} used, {remaining} remaining this month")
                
                return games
            else:
                print(f"API request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except Exception as e:
            print(f"Error fetching from API: {e}")
            return []
    
    def extract_spread_from_game(self, game_data):
        """
        Extracts the point spread from a game's bookmaker data.
        
        We prefer DraftKings for consistency, but will use the first available
        bookmaker if DraftKings doesn't have odds for this game. The spread
        is returned as a tuple: (home_spread, away_spread, bookmaker_used)
        """
        bookmakers = game_data.get('bookmakers', [])
        
        if not bookmakers:
            return (0.0, 0.0, None)
        
        # First, try to find DraftKings
        draftkings = None
        fallback = None
        
        for bookmaker in bookmakers:
            if bookmaker.get('key') == 'draftkings':
                draftkings = bookmaker
                break
            elif not fallback:  # Store first bookmaker as fallback
                fallback = bookmaker
        
        # Use DraftKings if available, otherwise use fallback
        selected_bookmaker = draftkings or fallback
        bookmaker_name = selected_bookmaker.get('title', 'Unknown')
        
        # Extract spreads from the selected bookmaker
        markets = selected_bookmaker.get('markets', [])
        
        for market in markets:
            if market.get('key') == 'spreads':
                outcomes = market.get('outcomes', [])
                
                # The API provides spreads for both teams
                home_spread = 0.0
                away_spread = 0.0
                
                for outcome in outcomes:
                    team_name = outcome.get('name')
                    point = outcome.get('point', 0)
                    
                    if team_name == game_data.get('home_team'):
                        home_spread = float(point)
                    elif team_name == game_data.get('away_team'):
                        away_spread = float(point)
                
                # If we had to use a fallback bookmaker, note it
                if not draftkings and fallback:
                    return (home_spread, away_spread, f"Fallback: {bookmaker_name}")
                else:
                    return (home_spread, away_spread, None)
        
        return (0.0, 0.0, None)
    
    def should_import_game(self, game_data, home_spread, away_spread):
        """
        Determines if a game should be imported based on your rules.
        
        A game is imported if:
        1. At least one team is in your tracked list of 49 teams
        2. AND either:
           - No team is favored by more than 16 points, OR
           - A tracked team is the underdog (even if opponent is favored by >16)
        
        This ensures your users can pick any underdog, regardless of spread.
        """
        home_team = game_data.get('home_team')
        away_team = game_data.get('away_team')
        
        # Clean team names for checking against tracked teams
        home_clean = self.team_name_map.get(home_team, home_team)
        away_clean = self.team_name_map.get(away_team, away_team)
        
        home_tracked = home_clean in self.tracked_teams
        away_tracked = away_clean in self.tracked_teams
        
        # If neither team is tracked, skip this game entirely
        if not home_tracked and not away_tracked:
            return False, None
        
        # Check if any team is favored by more than 16
        if home_spread < -16:  # Home team favored by more than 16
            if away_tracked:  # Away team is tracked and is the underdog
                return True, None  # Import it, away team is selectable
            else:  # Away team not tracked, home team too favored
                return False, f"{home_team} favored by {abs(home_spread)} (>16 points)"
        
        if away_spread < -16:  # Away team favored by more than 16
            if home_tracked:  # Home team is tracked and is the underdog
                return True, None  # Import it, home team is selectable
            else:  # Home team not tracked, away team too favored
                return False, f"{away_team} favored by {abs(away_spread)} (>16 points)"
        
        # If we get here, spread is 16 or less, import the game
        return True, None
    
    def import_games_to_database(self, games_data, week_number):
        """
        Imports the filtered games into your database for the specified week.
        
        This method handles both tracked and non-tracked teams appropriately,
        storing team IDs when available or team names as strings when not.
        """
        with app.app_context():
            # Verify the week exists
            week = Week.query.filter_by(week_number=week_number).first()
            if not week:
                print(f"\n❌ Error: Week {week_number} doesn't exist in the database.")
                print("Please create the week in your admin interface first.")
                return False
            
            # Get all teams for matching
            all_teams = {team.name: team for team in Team.query.all()}
            
            imported = 0
            skipped = 0
            excluded_spreads = []
            fallback_bookmakers = []
            
            print(f"\nProcessing {len(games_data)} games for Week {week_number}...")
            print("-" * 50)
            
            for game_data in games_data:
                # Extract basic game info
                api_home_team = game_data.get('home_team')
                api_away_team = game_data.get('away_team')
                
                # Get spreads and check for fallback bookmaker
                home_spread, away_spread, bookmaker_note = self.extract_spread_from_game(game_data)
                
                if bookmaker_note:
                    fallback_bookmakers.append(f"{api_away_team} @ {api_home_team}: {bookmaker_note}")
                
                # Check if we should import this game
                should_import, exclusion_reason = self.should_import_game(game_data, home_spread, away_spread)
                
                if not should_import:
                    if exclusion_reason:
                        excluded_spreads.append(exclusion_reason)
                    skipped += 1
                    continue
                
                # Map team names to database entries
                home_clean = self.team_name_map.get(api_home_team, api_home_team)
                away_clean = self.team_name_map.get(api_away_team, api_away_team)
                
                home_team_obj = all_teams.get(home_clean)
                away_team_obj = all_teams.get(away_clean)
                
                # Parse game time
                commence_time = game_data.get('commence_time', '')
                if commence_time:
                    game_time = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                else:
                    game_time = datetime.now()
                
                # Check if game already exists
                # We need to check both ID-based and name-based matches
                existing_game = None
                
                if home_team_obj and away_team_obj:
                    # Both teams are tracked, check by IDs
                    existing_game = Game.query.filter_by(
                        week_id=week.id,
                        home_team_id=home_team_obj.id,
                        away_team_id=away_team_obj.id
                    ).first()
                
                if existing_game:
                    print(f"Already exists: {away_clean} @ {home_clean}")
                    continue
                
                # Create new game with appropriate fields
                new_game = Game(
                    week_id=week.id,
                    home_team_id=home_team_obj.id if home_team_obj else None,
                    away_team_id=away_team_obj.id if away_team_obj else None,
                    home_team_name=None if home_team_obj else api_home_team,
                    away_team_name=None if away_team_obj else api_away_team,
                    home_team_spread=home_spread,
                    game_time=game_time
                )
                
                db.session.add(new_game)
                imported += 1
                
                # Display what we imported
                home_display = home_clean if home_team_obj else f"{api_home_team} (untracked)"
                away_display = away_clean if away_team_obj else f"{api_away_team} (untracked)"
                print(f"✅ Added: {away_display} @ {home_display} | Spread: {home_spread:.1f}")
            
            # Commit all changes
            db.session.commit()
            
            # Display summary
            print("\n" + "=" * 50)
            print(f"Import Summary for Week {week_number}")
            print("=" * 50)
            print(f"✅ Successfully imported: {imported} games")
            print(f"⏭️  Skipped: {skipped} games")
            
            if fallback_bookmakers:
                print(f"\n⚠️  Used fallback bookmakers for {len(fallback_bookmakers)} games:")
                for fallback in fallback_bookmakers:
                    print(f"   - {fallback}")
            
            if excluded_spreads:
                print(f"\n🚫 Excluded {len(excluded_spreads)} games due to spread >16:")
                for exclusion in excluded_spreads:
                    print(f"   - {exclusion}")
            
            print("=" * 50)
            
            return True

def suggest_dates_for_week(week_number):
    """
    Suggests appropriate date ranges for each week of the college football season.
    
    Week 1 starts on Thursday, August 28, 2025. Each subsequent week starts
    7 days later. Most games are on Saturday, but we include a few days buffer.
    """
    # Week 1 starts Thursday, August 28, 2025
    week_1_start = datetime(2025, 8, 28)
    
    # Calculate start date for the requested week
    weeks_after_first = week_number - 1
    start_date = week_1_start + timedelta(days=weeks_after_first * 7)
    
    # End date is typically 4 days after start (Thursday through Sunday)
    end_date = start_date + timedelta(days=4)
    
    return start_date, end_date

def main():
    """
    Main function that orchestrates the import process.
    
    This provides a user-friendly interface for importing games week by week,
    with helpful date suggestions and clear feedback throughout the process.
    """
    print("\n" + "=" * 60)
    print("NCAA Football API Game Importer")
    print("=" * 60)
    
    # Get week number
    while True:
        week_input = input("\nEnter week number to import (1-15): ").strip()
        try:
            week_num = int(week_input)
            if 1 <= week_num <= 15:
                break
            else:
                print("Please enter a number between 1 and 15")
        except ValueError:
            print("Please enter a valid number")
    
    # Suggest dates for this week
    suggested_start, suggested_end = suggest_dates_for_week(week_num)
    
    print(f"\nDate range for Week {week_num}:")
    print(f"Suggested start: {suggested_start.strftime('%Y-%m-%d')}")
    print(f"Suggested end: {suggested_end.strftime('%Y-%m-%d')}")
    
    # Get actual dates (allow override of suggestions)
    start_input = input(f"\nEnter start date (YYYY-MM-DD) or press Enter for suggested [{suggested_start.strftime('%Y-%m-%d')}]: ").strip()
    if not start_input:
        start_date = suggested_start
    else:
        try:
            start_date = datetime.strptime(start_input, '%Y-%m-%d')
        except ValueError:
            print("Invalid date format, using suggested date")
            start_date = suggested_start
    
    end_input = input(f"Enter end date (YYYY-MM-DD) or press Enter for suggested [{suggested_end.strftime('%Y-%m-%d')}]: ").strip()
    if not end_input:
        end_date = suggested_end
    else:
        try:
            end_date = datetime.strptime(end_input, '%Y-%m-%d')
        except ValueError:
            print("Invalid date format, using suggested date")
            end_date = suggested_end
    
    # Create importer and fetch games
    importer = NCAAFootballAPIImporter()
    games = importer.fetch_games_for_date_range(start_date, end_date)
    
    if not games:
        print("\n❌ No games found for this date range.")
        print("This could mean:")
        print("  1. No games are scheduled for these dates")
        print("  2. The API doesn't have odds yet for these games")
        print("  3. There was an issue with the API request")
        return
    
    # Import games to database
    print(f"\nFound {len(games)} games from the API")
    confirm = input("Proceed with import? (y/n): ").strip().lower()
    
    if confirm == 'y':
        importer.import_games_to_database(games, week_num)
    else:
        print("Import cancelled")

if __name__ == "__main__":
    main()