"""Standalone wrapper to update/lock spreads for the active week.

Run via cron or manually:
    python update_spreads.py
"""

import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from services.automation import run_spread_update

logger = logging.getLogger(__name__)

app = create_app()


def main():
    with app.app_context():
        try:
            result = run_spread_update()
            print(f"[update_spreads] {result.get('details', result)}")
        except Exception:
            logger.exception("Spread update failed")
            raise


if __name__ == "__main__":
    main()
