"""Standalone wrapper to run weekly setup (create week + import games + activate).

Run via cron or manually:
    python weekly_setup.py
"""

import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from services.automation import run_setup

logger = logging.getLogger(__name__)

app = create_app()


def main():
    with app.app_context():
        try:
            result = run_setup()
            print(f"[weekly_setup] {result.get('details', result)}")
        except Exception:
            logger.exception("Weekly setup failed")
            raise


if __name__ == "__main__":
    main()
