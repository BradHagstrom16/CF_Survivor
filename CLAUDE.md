# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Available Tools & Plugins

The following Claude Code plugins are installed and enabled. Use them proactively to enhance development workflows and code quality rather than relying solely on training knowledge:

- **claude-code-setup** - Environment and project setup management
- **claude-md-management** - Markdown file handling and organization
- **code-review** - Automated code review and quality checks
- **code-simplifier** - Code refactoring and simplification
- **coderabbit** - AI-powered code analysis
- **commit-commands** - Git commit management and automation
- **context7** - Enhanced contextual awareness (includes MCP)
- **feature-dev** - Feature development workflows
- **frontend-design** - UI/UX design and styling assistance
- **playwright** - Browser automation and testing (includes MCP)
- **pr-review-toolkit** - Pull request review utilities
- **pyright-lsp** - Python language server and type checking
- **superpowers** - Advanced development capabilities

## Project Overview

CF Survivor Pool is a college football survivor pool web app. Players pick one team per week to win against the spread. Two lives, cumulative spread tiebreaker, single-use teams per regular season (resets for CFP), and full College Football Playoff support. Deployed on PythonAnywhere with SQLite.

## Commands

```bash
# Run development server
flask run                    # or: python app.py

# Database setup
flask init-db                # Create tables
python populate_teams.py     # One-time team initialization

# Unified CLI automation
flask cfb-sync --mode setup      # Create next week, import games, activate
flask cfb-sync --mode spreads    # Lock spreads with latest odds from The Odds API
flask cfb-sync --mode scores     # Fetch scores, auto-process completed weeks
flask cfb-sync --mode autopick   # Process auto-picks for past-deadline weeks
flask cfb-sync --mode remind     # Send email reminders (Fri/Sat only)
flask cfb-sync --mode status     # Print season summary

# Standalone cron scripts
python daily_sync.py         # Day-aware automation (Mon=setup, Tue=spreads, Sat/Sun=scores)
python fetch_scores.py       # Fetch and process scores
python update_spreads.py     # Update/lock spreads for active week
python weekly_setup.py       # Create next week + import games + activate
python run_autopicks.py      # Process auto-picks
python send_reminders.py     # Email pick reminders
python weekly_backup.py      # Automated weekly database backup
python import_games.py       # Interactive game import from The Odds API
```

No test suite exists. No linter is configured.

## Database Migrations

```bash
# Generate a new migration after changing models
flask db migrate -m "description of change"

# Apply pending migrations
flask db upgrade

# Rollback one migration
flask db downgrade

# Show current migration version
flask db current
```

**Important:** After any change to `models.py`, always run `flask db migrate` to generate a migration, review it, then `flask db upgrade` to apply it. Never use raw SQL to modify the schema.

## Architecture

**Flask app factory** (`create_app()` in `app.py`) with blueprints and a services layer:

- `app.py` — App factory, extensions init, CLI commands, error handlers. Entry point.
- `models.py` — SQLAlchemy models: `User`, `Team`, `Week`, `Game`, `Pick`.
- `extensions.py` — Centralized extension instances: `db`, `login_manager`, `csrf`, `limiter`, `migrate`.
- `config.py` — Environment-based config classes (`development`/`production`/`testing`). `ENVIRONMENT` env var selects config.
- `constants.py` — Re-exports from `fbs_master_teams.py`; `SPORT_KEY`, `API_BASE_URL`, `SEASON_SCHEDULE`.
- `timezone_utils.py` — All timezone helpers: `POOL_TZ`, `deadline_has_passed()`, `make_aware()`, `to_pool_time()`.
- `display_utils.py` — Week display names, CFP team helpers, template context injection.
- `db_maintenance.py` — Legacy schema migration helpers using raw SQL (kept for reference; Alembic now manages schema changes).

**Routes (blueprints):**
- `routes/auth.py` — Login, register, logout, change password.
- `routes/main.py` — Standings (`/`), pick submission (`/pick/<week>`), my picks, weekly results.
- `routes/admin.py` — Dashboard, week/game management, mark results, users, payments, teams, score fetching.

**Services:**
- `services/game_logic.py` — `process_week_results()`, `process_autopicks()`, `get_used_team_ids()`. Core business logic.
- `services/automation.py` — `run_setup()`, `run_spread_update()`, `run_scores()`, `run_status()`. CLI orchestration.
- `services/score_fetcher.py` — `ScoreFetcher` class. The Odds API integration for scores.

**Frontend:** Jinja2 templates with Bootstrap 5.3. No build step. Custom CSS in `static/css/style.css`.

## Critical Domain Logic

**Game Rules:**
- 49 teams from preseason AP Top 25 and surrounding teams
- Two lives per player — incorrect pick against the spread loses a life
- Single use — each team picked once per regular season; resets for CFP
- 16-point cap — teams favored by 16.5+ are ineligible
- Auto-picks — miss deadline and system picks biggest available favorite (<=16 pts)
- Cumulative spread tiebreaker — lower is better (favorites add, underdogs subtract)

**Revival Rule (`process_week_results()` in `services/game_logic.py`):**
- If every remaining 1-life player loses in the same week, all are revived to 1 life

**CFP Phase:**
- `Week.is_playoff_week=True` — team usage resets; teams eliminated from CFP are blocked
- `display_utils.py` tracks CFP eliminations via game results

**Pick Resolution:**
- Picks are correct/incorrect based on `Game.home_team_won` — the ATS winner
- Losing a pick decrements `User.lives_remaining`; reaching 0 sets `User.is_eliminated = True`

## Key Conventions

- All timestamps use `datetime.now(timezone.utc)` (not deprecated `utcnow()`)
- Pool timezone is `America/Chicago` (Central Time), stored as `POOL_TZ` in `timezone_utils.py`
- Deadlines stored as naive datetimes in SQLite (assumed Central Time)
- Timezone: `zoneinfo.ZoneInfo` (not pytz) — use `.replace(tzinfo=tz)` not `.localize()`
- ORM style: SQLAlchemy 2.0 — use `db.session.get(Model, id)` and `db.get_or_404(Model, id)`
- ORM safety: never mutate ORM attributes for display — use transient attrs (`game._aware_time`, `week._aware_deadline`)
- Template context: `display_utils.py` injects `get_week_display_name`, `get_week_short_label`, `is_week_playoff`, `format_deadline` globally
- Helper: `get_game_for_team(week_id, team_id)` in `services/game_logic.py` — finds a team's game
- Helper: `Game.get_spread_for_team(team_id)` — returns spread from team's perspective
- Flask-Limiter rate-limits login to 10/min
- CSRF via Flask-WTF on all forms; AJAX calls include `X-CSRFToken` header
- Open redirect prevention: login rejects absolute URLs in `next` param
- Admin routes use custom `@admin_required` decorator (checks both auth and admin flag)

## Environment Variables

```
ENVIRONMENT=development|production|testing   # Selects config class
SECRET_KEY=...                               # Flask session secret
DATABASE_URL=sqlite:///picks.db              # SQLAlchemy DB URI
POOL_TIMEZONE=America/Chicago                # Timezone for all deadlines
ENTRY_FEE=25                                 # Entry fee in dollars
ODDS_API_KEY=...                             # The Odds API key
EMAIL_ADDRESS=...                            # Gmail for reminders
EMAIL_PASSWORD=...                           # Gmail app-specific password
SMTP_SERVER=smtp.gmail.com                   # SMTP server
SMTP_PORT=587                                # SMTP port
POOL_URL=https://b1gbrad.pythonanywhere.com  # Public URL for email links
```

## Scheduled Tasks (PythonAnywhere)

| Time | Script | Purpose |
|------|--------|---------|
| Friday 09:59 CT | `send_reminders.py` | 25-hour warning emails |
| Saturday 09:59 CT | `send_reminders.py` | 1-hour final warning emails |
| Saturday 11:05 CT | `run_autopicks.py` | Process auto-picks after deadline |
| Sunday 00:00 CT | `weekly_backup.py` | Automated database backup |
