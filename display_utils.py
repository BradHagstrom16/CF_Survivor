"""
Display utilities for consistent week name formatting across the app
Handles both regular season and playoff week displays, plus CFP elimination tracking
"""

def get_week_display_name(week):
    """
    Get the full display name for a week
    
    Returns:
        - "Week 1" through "Week 14" for regular season
        - "Conference Championship Week" for week 15
        - "CFP Round 1", "CFP Quarterfinals", etc. for playoff weeks
    
    Args:
        week: Week object from database
    
    Returns:
        str: Full display name
    """
    if not week:
        return "Unknown Week"
    
    # Check if week has a custom round_name set
    if hasattr(week, 'round_name') and week.round_name:
        return week.round_name
    
    # Default to "Week X" for weeks without custom names
    return f"Week {week.week_number}"


def get_week_short_label(week):
    """
    Get the short label for a week (used in navigation buttons)
    
    Returns:
        - "W1" through "W14" for regular season
        - "CCW" for week 15 (Conference Championship Week)
        - "R1", "QF", "SF", "F" for playoff rounds
    
    Args:
        week: Week object from database
    
    Returns:
        str: Short label
    """
    if not week:
        return "?"
    
    # Check if it has a custom round_name
    if hasattr(week, 'round_name') and week.round_name:
        round_name = week.round_name
        
        # Map full names to short labels
        label_map = {
            "Conference Championship Week": "CCW",
            "CFP Round 1": "R1",
            "CFP Quarterfinals": "QF",
            "CFP Semifinals": "SF",
            "CFP Championship": "F"
        }
        
        return label_map.get(round_name, f"W{week.week_number}")
    
    # Default to "WX" format
    return f"W{week.week_number}"


def get_playoff_teams():
    """
    Returns the list of teams eligible for playoff picks (the initial 12-team field)
    
    Returns:
        list: List of playoff team names
    """
    return [
        'Ohio State',
        'Georgia', 
        'Oregon',
        'Alabama',
        'Miami',
        'Oklahoma',
        'Texas A&M',
        'Indiana',
        'Ole Miss',
        'Texas Tech',
        'Tulane',
        'James Madison'
    ]


def get_cfp_eliminated_teams():
    """
    Returns team names that have been eliminated from the CFP (lost a playoff game).
    
    A team is eliminated if they lost in any game during a playoff week 
    where results have been recorded.
    
    Returns:
        set: Set of eliminated team names
    """
    # Import here to avoid circular imports
    from extensions import db
    from models import Game, Week, Team
    
    eliminated = set()
    
    # Get all playoff weeks with completed games
    playoff_games = db.session.query(Game).join(Week).filter(
        Week.is_playoff_week == True,
        Game.home_team_won != None  # Result has been recorded
    ).all()
    
    for game in playoff_games:
        if game.home_team_won:
            # Home team won, away team is eliminated
            if game.away_team:
                eliminated.add(game.away_team.name)
            elif game.away_team_name:
                eliminated.add(game.away_team_name)
        else:
            # Away team won, home team is eliminated
            if game.home_team:
                eliminated.add(game.home_team.name)
            elif game.home_team_name:
                eliminated.add(game.home_team_name)
    
    return eliminated


def get_cfp_active_teams():
    """
    Returns playoff teams that are still in contention (not eliminated).
    
    Returns:
        list: List of active team names
    """
    all_playoff_teams = set(get_playoff_teams())
    eliminated = get_cfp_eliminated_teams()
    
    return list(all_playoff_teams - eliminated)


def get_cfp_teams_in_week(week):
    """
    Returns the team names that have a game scheduled in a specific playoff week.
    
    Args:
        week: Week object from database
    
    Returns:
        set: Set of team names playing this week
    """
    if not week:
        return set()
    
    # Import here to avoid circular imports
    from models import Game
    
    teams_playing = set()
    
    games = Game.query.filter_by(week_id=week.id).all()
    
    for game in games:
        if game.home_team:
            teams_playing.add(game.home_team.name)
        elif game.home_team_name:
            teams_playing.add(game.home_team_name)
        
        if game.away_team:
            teams_playing.add(game.away_team.name)
        elif game.away_team_name:
            teams_playing.add(game.away_team_name)
    
    return teams_playing


def get_cfp_teams_on_bye(week):
    """
    Returns active playoff teams that don't have a game in a specific week (on bye).
    
    Args:
        week: Week object from database
    
    Returns:
        list: List of team names on bye this week
    """
    if not week:
        return []
    
    active_teams = set(get_cfp_active_teams())
    teams_playing = get_cfp_teams_in_week(week)
    
    return list(active_teams - teams_playing)


def get_cfp_available_teams_for_user(user_id, week):
    """
    Returns playoff teams available for a specific user to pick in a specific week.
    
    A team is available if:
    - In the 12-team playoff roster
    - NOT eliminated (hasn't lost a CFP game)
    - Has a game scheduled this week (not on bye)
    - User hasn't picked them in a previous CFP week
    
    Args:
        user_id: The user's ID
        week: Week object for the current week
    
    Returns:
        list: List of Team objects available to pick
    """
    if not week:
        return []
    
    # Import here to avoid circular imports
    from extensions import db
    from models import Team, Pick, Week as WeekModel
    
    # Get base sets
    playoff_team_names = set(get_playoff_teams())
    eliminated_names = get_cfp_eliminated_teams()
    teams_playing_names = get_cfp_teams_in_week(week)
    
    # Get teams user has already picked in CFP
    used_in_cfp = db.session.query(Pick.team_id).join(WeekModel).filter(
        Pick.user_id == user_id,
        WeekModel.is_playoff_week == True,
        Pick.week_id != week.id  # Exclude current week
    ).all()
    used_team_ids = {t[0] for t in used_in_cfp}
    
    # Build available list
    available_teams = []
    all_teams = Team.query.all()
    
    for team in all_teams:
        # Must be a playoff team
        if team.name not in playoff_team_names:
            continue
        
        # Must not be eliminated
        if team.name in eliminated_names:
            continue
        
        # Must be playing this week (not on bye)
        if team.name not in teams_playing_names:
            continue
        
        # Must not have been used by this user in CFP
        if team.id in used_team_ids:
            continue
        
        available_teams.append(team)
    
    return available_teams


def is_week_playoff(week):
    """
    Check if a week is a playoff week
    
    Args:
        week: Week object from database
    
    Returns:
        bool: True if playoff week, False otherwise
    """
    if not week:
        return False
    
    # Check the is_playoff_week flag
    if hasattr(week, 'is_playoff_week'):
        return week.is_playoff_week
    
    # Fallback: check week number (16+ are playoffs)
    return week.week_number >= 16


def format_week_for_title(week):
    """
    Format week name for page titles and headers
    Examples: "Week 5", "Conference Championship Week", "CFP Round 1"
    
    Args:
        week: Week object from database
    
    Returns:
        str: Formatted week name for titles
    """
    return get_week_display_name(week)


def format_week_for_navigation(week):
    """
    Format week name for navigation buttons
    Examples: "W5", "CCW", "R1"
    
    Args:
        week: Week object from database
    
    Returns:
        str: Formatted week name for navigation
    """
    return get_week_short_label(week)


# Template helper functions (to be injected into Jinja2 context)
def get_display_helpers():
    """
    Returns a dictionary of helper functions to inject into template context
    
    Usage in app.py:
        @app.context_processor
        def inject_display_helpers():
            return get_display_helpers()
    """
    return {
        'get_week_display_name': get_week_display_name,
        'get_week_short_label': get_week_short_label,
        'is_week_playoff': is_week_playoff,
        'format_week_for_title': format_week_for_title,
        'format_week_for_navigation': format_week_for_navigation,
        'get_playoff_teams': get_playoff_teams,
        'get_cfp_eliminated_teams': get_cfp_eliminated_teams,
        'get_cfp_active_teams': get_cfp_active_teams,
        'get_cfp_teams_on_bye': get_cfp_teams_on_bye,
    }
