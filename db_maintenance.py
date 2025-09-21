"""Utilities for one-off database schema maintenance."""

from typing import Callable, Optional

from sqlalchemy import inspect, text
from sqlalchemy.exc import NoSuchTableError


def ensure_team_national_title_odds_column(app, db, *, reporter: Optional[Callable[[str], None]] = None) -> bool:
    """Ensure the Team table has a national_title_odds column.

    Returns ``True`` when the column exists (either already present or added
    successfully) and ``False`` if the table is missing or the ALTER fails.
    """

    report = reporter or print

    with app.app_context():
        inspector = inspect(db.engine)

        try:
            columns = {col["name"] for col in inspector.get_columns("team")}
        except NoSuchTableError:
            report("Team table does not exist yet; skipping odds column check.")
            return False

        if "national_title_odds" in columns:
            return True

        report("Adding national_title_odds column to Team table...")

        try:
            with db.engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE team ADD COLUMN national_title_odds VARCHAR(16)")
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            report(f"Failed to add national_title_odds column: {exc}")
            return False

        return True