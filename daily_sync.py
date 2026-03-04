"""Daily sync orchestrator for the CFB Survivor pool.

Checks the day of the week and runs the appropriate automation:
  - Monday:  run_setup() — create next week, import games, activate
  - Tuesday: run_spread_update() — lock spreads with latest odds
  - Saturday/Sunday/Monday: run_scores() — fetch and process scores

Schedule on PythonAnywhere: run daily at 14:00 UTC (8:00 AM CT) and 18:00 UTC (12:00 PM CT).
"""

import logging
import os
import sys
from datetime import datetime

from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from services.automation import run_setup, run_spread_update, run_scores

logger = logging.getLogger(__name__)

app = create_app()

CHICAGO_TZ = ZoneInfo('America/Chicago')


def _log_result(label, result):
    """Log a result dict at the appropriate level based on status."""
    details = result.get('details', str(result))
    if result.get('status') == 'error':
        logger.error("%s FAILED: %s", label, details)
    else:
        logger.info("%s: %s", label, details)


def main():
    now = datetime.now(CHICAGO_TZ)
    weekday = now.weekday()  # 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
    day_name = now.strftime('%A')

    logger.info("[daily_sync] %s (%s)", now.strftime('%Y-%m-%d %I:%M %p %Z'), day_name)

    with app.app_context():
        try:
            # Monday: setup new week + score check for previous week
            if weekday == 0:
                logger.info("Running: setup + scores")
                _log_result("setup", run_setup())
                _log_result("scores", run_scores())

            # Tuesday: lock spreads
            elif weekday == 1:
                logger.info("Running: spread update")
                _log_result("spreads", run_spread_update())

            # Saturday/Sunday: fetch scores
            elif weekday in (5, 6):
                logger.info("Running: scores")
                _log_result("scores", run_scores())

            else:
                logger.info("No automated actions for %s", day_name)
        except Exception:
            logger.exception("Daily sync failed")
            raise


if __name__ == "__main__":
    main()
