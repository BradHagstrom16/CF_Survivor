"""Utility script to run auto-pick processing outside of request handling."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("ENVIRONMENT", "production")

from app import app, check_and_process_autopicks  # noqa: E402


def main() -> None:
    """Process auto-picks for any weeks past their deadline."""
    with app.app_context():
        try:
            results = check_and_process_autopicks()
            if results:
                print("Auto-picks processed successfully:")
                for entry in results:
                    app.logger.info(entry)
                    print(f"  • {entry}")
            else:
                message = "No auto-picks were required."
                app.logger.info(message)
                print(message)
        except Exception:
            app.logger.exception("Auto-pick processing failed")
            raise


if __name__ == "__main__":
    main()