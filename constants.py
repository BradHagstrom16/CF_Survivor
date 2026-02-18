"""
CFB Survivor Pool - Shared Constants
======================================
Re-exports master team data from fbs_master_teams and defines season schedule constants.
"""

from fbs_master_teams import (
    FBS_MASTER_TEAMS,
    TEAM_NAME_MAP,
    TEAM_CONFERENCES,
    SHORT_TO_API,
)

# The Odds API sport key for NCAAF
SPORT_KEY = 'americanfootball_ncaaf'

# Base URL for The Odds API v4 NCAAF endpoints
API_BASE_URL = 'https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf'

# 2025-2026 season schedule configuration
SEASON_SCHEDULE = {
    # Date of the Thursday of Week 1 (Aug 28, 2025)
    'week_1_start': '2025-08-28',

    # Default deadline: Saturday at 11:00 AM Central
    'default_deadline_day': 'Saturday',
    'default_deadline_hour': 11,
    'default_deadline_minute': 0,

    # Regular season runs weeks 1-14
    'regular_season_weeks': 14,

    # Special weeks (Conference Championship Week and CFP rounds)
    'special_weeks': {
        15: {'name': 'Conference Championship Week', 'is_playoff': False},
        16: {'name': 'CFP First Round', 'is_playoff': True},
        17: {'name': 'CFP Quarterfinals', 'is_playoff': True},
        18: {'name': 'CFP Semifinals', 'is_playoff': True},
        19: {'name': 'CFP National Championship', 'is_playoff': True},
    },
}
