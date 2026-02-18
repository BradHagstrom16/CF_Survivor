"""Utilities for one-off database schema maintenance."""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import NoSuchTableError

logger = logging.getLogger(__name__)


def _ensure_column(app, db, table, column, col_type, *, reporter=None):
    """Generic helper to add a column if it doesn't exist."""
    report = reporter or logger.info

    with app.app_context():
        inspector = inspect(db.engine)
        try:
            columns = {col["name"] for col in inspector.get_columns(table)}
        except NoSuchTableError:
            report(f"{table} table does not exist yet; skipping {column} check.")
            return False

        if column in columns:
            return True

        report(f"Adding {column} column to {table} table...")
        try:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        except Exception as exc:
            report(f"Failed to add {column} column: {exc}")
            return False

        return True


def ensure_team_national_title_odds_column(app, db, *, reporter=None):
    """Ensure the Team table has a national_title_odds column."""
    return _ensure_column(app, db, "team", "national_title_odds", "VARCHAR(16)", reporter=reporter)


def ensure_user_is_admin_column(app, db, *, reporter=None):
    """Ensure the User table has an is_admin column and set B1G_Brad as admin."""
    report = reporter or logger.info
    added = _ensure_column(app, db, "user", "is_admin", "BOOLEAN DEFAULT 0", reporter=reporter)

    if added:
        with app.app_context():
            try:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "UPDATE user SET is_admin = 1 WHERE username IN ('admin', 'B1G_Brad')"
                    ))
                report("Set is_admin=True for admin accounts.")
            except Exception as exc:
                report(f"Failed to set admin flags: {exc}")

    return added


def ensure_user_display_name_column(app, db, *, reporter=None):
    """Ensure the User table has a display_name column and seed admin display name."""
    report = reporter or logger.info
    added = _ensure_column(app, db, "user", "display_name", "VARCHAR(80)", reporter=reporter)

    if added:
        with app.app_context():
            try:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "UPDATE user SET display_name = 'B1G_Brad' WHERE username = 'admin' AND display_name IS NULL"
                    ))
                report("Seeded display_name for admin account.")
            except Exception as exc:
                report(f"Failed to seed display_name: {exc}")

    return added


def ensure_game_automation_columns(app, db, *, reporter=None):
    """Ensure the Game table has columns for automation (scores, event ID, spread lock)."""
    _ensure_column(app, db, "game", "api_event_id", "VARCHAR(64)", reporter=reporter)
    _ensure_column(app, db, "game", "home_score", "INTEGER", reporter=reporter)
    _ensure_column(app, db, "game", "away_score", "INTEGER", reporter=reporter)
    _ensure_column(app, db, "game", "spread_locked_at", "DATETIME", reporter=reporter)
