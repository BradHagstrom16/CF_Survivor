"""Populate the database with the 49 tracked teams.

Run once after init-db:
    python populate_teams.py
"""

import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from extensions import db
from models import Team

logger = logging.getLogger(__name__)

app = create_app()

TEAMS = [
    'Texas', 'Penn State', 'Ohio State', 'Clemson', 'Georgia', 'Notre Dame',
    'Oregon', 'Alabama', 'LSU', 'Miami', 'Arizona State', 'Illinois',
    'South Carolina', 'Michigan', 'Florida', 'SMU', 'Kansas State', 'Oklahoma',
    'Texas A&M', 'Indiana', 'Ole Miss', 'Iowa State', 'Texas Tech', 'Tennessee',
    'Boise State', 'BYU', 'Utah', 'Baylor', 'Louisville', 'USC', 'Georgia Tech',
    'Missouri', 'Tulane', 'Nebraska', 'UNLV', 'Toledo', 'Auburn',
    'James Madison', 'Memphis', 'Florida State', 'Duke', 'Liberty', 'Navy',
    'Iowa', 'TCU', 'Pittsburgh', 'Army', 'Colorado', 'Louisiana-Lafayette',
]


def populate_teams():
    """Add all teams to the database if they don't already exist."""
    with app.app_context():
        existing_count = Team.query.count()
        if existing_count > 0:
            logger.info("Database already has %d teams. Skipping.", existing_count)
            return

        for name in TEAMS:
            db.session.add(Team(name=name))
            logger.info("Added: %s", name)

        db.session.commit()
        logger.info("Successfully added %d teams.", len(TEAMS))


if __name__ == "__main__":
    populate_teams()
