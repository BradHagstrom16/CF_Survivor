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


def main():
    now = datetime.now(CHICAGO_TZ)
    weekday = now.weekday()  # 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
    day_name = now.strftime('%A')

    print(f"\n[daily_sync] {now.strftime('%Y-%m-%d %I:%M %p %Z')} ({day_name})")

    with app.app_context():
        try:
            # Monday: setup new week + score check for previous week
            if weekday == 0:
                print("Running: setup + scores")
                result = run_setup()
                print(f"  setup: {result.get('details', result)}")
                result = run_scores()
                print(f"  scores: {result.get('details', result)}")

            # Tuesday: lock spreads
            elif weekday == 1:
                print("Running: spread update")
                result = run_spread_update()
                print(f"  spreads: {result.get('details', result)}")

            # Saturday/Sunday: fetch scores
            elif weekday in (5, 6):
                print("Running: scores")
                result = run_scores()
                print(f"  scores: {result.get('details', result)}")

            else:
                print(f"No automated actions for {day_name}")
        except Exception:
            logger.exception("Daily sync failed")
            raise


if __name__ == "__main__":
    main()
