"""Utility script to run auto-pick processing outside of request handling.

Run via cron or manually:
    python run_autopicks.py
"""

import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from services.game_logic import check_and_process_autopicks

logger = logging.getLogger(__name__)

app = create_app()


def main() -> None:
    """Process auto-picks for any weeks past their deadline."""
    with app.app_context():
        try:
            results = check_and_process_autopicks()
            if results:
                logger.info("Auto-picks processed successfully:")
                for entry in results:
                    logger.info("  %s", entry)
            else:
                logger.info("No auto-picks were required.")
        except Exception:
            logger.exception("Auto-pick processing failed")
            raise


if __name__ == "__main__":
    main()
