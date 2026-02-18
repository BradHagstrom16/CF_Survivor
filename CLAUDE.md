# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Golf Pick 'Em is a season-long PGA Tour fantasy league where users pick one golfer per tournament. Points equal actual prize money earned. Each golfer can only be used once per season. Deployed on PythonAnywhere with SQLite.

## Commands

```bash
# Run development server
flask run                    # or: python app.py

# Database setup
flask init-db                # Create tables
flask create-admin           # Interactive admin user creation

# API sync (requires SLASHGOLF_API_KEY env var)
flask sync-run --mode schedule    # Import season schedule (Mon only)
flask sync-run --mode field       # Sync tournament field + tee times (Tue/Wed)
flask sync-run --mode live        # Update leaderboard with projected earnings
flask sync-run --mode results     # Finalize results + process picks (Sun/Mon)
flask sync-run --mode earnings    # Retry earnings finalization for pending tournaments

# Process results manually (all completed tournaments)
flask process-results

# Import tournaments from hardcoded list (one-time bootstrap)
python import_tournaments.py
```

No test suite exists. No linter is configured.

## Architecture

**Single-process Flask app** — no blueprints, no API layer, no background workers. All server code lives in four Python files:

- `app.py` — Routes, view logic, Flask CLI commands, `process_tournament_results()`. Entry point.
- `models.py` — All SQLAlchemy models, `format_score_to_par()` (module-level), `get_current_time()`, `LEAGUE_TZ`. The `Pick.resolve_pick()` method contains the core WD/backup activation logic and earnings multipliers.
- `sync_api.py` — `SlashGolfAPI` (RapidAPI client), `TournamentSync` (sync orchestration), CLI commands registered via `register_sync_commands(app)`. Handles schedule/field/leaderboard/results/withdrawal syncing.
- `config.py` — Environment-based config classes. `FLASK_ENV` selects config; key settings: `SEASON_YEAR`, `SYNC_MODE` (free/standard), `ENTRY_FEE`.

**Supporting files:**
- `send_reminders.py` — Email notifications (picks open, deadline reminders, admin alerts). Called from `sync_api.py` after field sync and also runs standalone via scheduled task.
- `email_config.py` — SMTP credentials (gitignored, never committed).
- `import_tournaments.py` — One-time bootstrap script with hardcoded 2026 schedule.

**Frontend:** Jinja2 templates with Bootstrap 5. Tom Select for player dropdowns on `make_pick.html`. No build step.

## Critical Domain Logic

**Pick Resolution (`Pick.resolve_pick()` in models.py):**
- Primary WDs before completing Round 2 → backup activates, primary returns to pool
- Primary WDs after Round 2 → primary counts with 0 pts, backup stays unused
- Both WD before R2 → primary used (0 pts), backup returns to pool
- Team events (Zurich Classic): earnings // 2
- Majors: earnings * 1.5

**Tournament Status:**
- Transitions: `upcoming` → `active` → `complete`
- `update_status_from_time()` auto-sets `upcoming`/`active` based on dates, but **never** auto-sets `complete`
- Only `sync_api.py` sets `complete` after verifying API status is "Complete"/"Official"
- `results_finalized` flag tracks whether actual earnings (vs projected) have been fetched

**Season Player Usage:** `SeasonPlayerUsage` table tracks which players are locked. Populated by `resolve_pick()`, cleaned and rebuilt by `process_tournament_results()` in app.py (uses `begin_nested()` savepoints).

## Key Conventions

- All timestamps use `datetime.now(timezone.utc)` (not deprecated `utcnow()`)
- League timezone is `America/Chicago` (Central Time), stored as `LEAGUE_TZ` in models.py
- Pick deadlines stored in CT as naive datetimes in SQLite (timezone stripped after conversion)
- API responses use MongoDB-style number format (`{"$numberInt": "123"}`) — helper `_parse_api_number()` handles this
- `format_score_to_par()` is a module-level function in models.py (also exists as instance method on TournamentResult that delegates to it)
- Flask-Limiter rate-limits login to 10/min
- CSRF via Flask-WTF on all forms; AJAX calls include `X-CSRFToken` header
- Open redirect prevention: login rejects absolute URLs in `next` param

## Environment Variables

```
FLASK_ENV=development|production    # Selects config class
SECRET_KEY=...                      # Flask session secret
DATABASE_URL=sqlite:///...          # DB path (default: golf_pickem.db)
SLASHGOLF_API_KEY=...               # RapidAPI key for SlashGolf
SYNC_MODE=free|standard             # API tier (free limits syncs to conserve calls)
FIXED_DEADLINE_HOUR_CT=7            # Fallback deadline hour when tee times unavailable
```
