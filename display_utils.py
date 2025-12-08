"""
Display utilities for consistent week name formatting across the app
Handles both regular season and playoff week displays
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
    Returns the list of teams eligible for playoff picks
    
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
        'get_playoff_teams': get_playoff_teams
    }
