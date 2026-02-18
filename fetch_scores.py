"""Standalone wrapper to fetch scores and auto-process completed weeks.

Run via cron or manually:
    python fetch_scores.py
"""

import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from services.automation import run_scores

logger = logging.getLogger(__name__)

app = create_app()


def main():
    with app.app_context():
        try:
            result = run_scores()
            print(f"[fetch_scores] {result.get('details', result)}")
        except Exception:
            logger.exception("Score fetch failed")
            raise


if __name__ == "__main__":
    main()
