# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

College football survivor pool web app (Flask/SQLite). Players pick one team per week to win against the spread, with two lives and cumulative spread tiebreaking. Hosted on PythonAnywhere.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (http://localhost:5000)
python app.py

# Initialize database and populate teams
flask init-db
python populate_teams.py

# Import games from The Odds API (interactive — prompts for week number and dates)
python import_games.py

# Run auto-picks after deadline
python run_autopicks.py

# Send email reminders
python send_reminders.py
```

There is no test suite in this project.

## Architecture

**App factory pattern** — `create_app(config_name)` in `app.py`. Config classes (dev/prod/test) in `config.py`. Extensions (db, login_manager, csrf, limiter) initialized in `extensions.py`.

**Blueprints:**
- `routes/auth.py` — login (rate-limited), register, logout, password change
- `routes/main.py` — standings, pick submission, results, pick history
- `routes/admin.py` — week/game/result management, user admin (all routes use `@admin_required`)

**Service layer** — `services/game_logic.py` contains all business logic: result processing, auto-picks, team eligibility. Models in `models.py` are data-only (User, Team, Week, Game, Pick).

**Template context** — `app.py` injects display helpers and timezone functions via `@app.context_processor`. Display helpers live in `display_utils.py`.

**WSGI entry** — `wsgi.py` for PythonAnywhere production deployment.

## Key Conventions

- **Timezone**: `timezone_utils.py` is the single source for all timezone operations (America/Chicago). Use `get_current_time()`, `deadline_has_passed()`, `safe_is_after()`, `to_pool_time()`. Never use raw `datetime.now()`.
- **Admin checks**: Use `current_user.is_admin` (boolean column on User model), never hardcoded usernames.
- **Passwords**: Use `user.set_password()` / `user.check_password()` — never hash directly.
- **CSRF**: All forms must include `{{ csrf_token() }}` or `{{ form.hidden_tag() }}`. CSRFProtect is global.
- **Scripts**: All operational scripts use `from app import create_app` to get an app context.
- **Schema migrations**: Handled in `db_maintenance.py` with graceful column-add functions (no Alembic).
- **Team eligibility**: Teams are single-use per regular season; usage resets for playoff weeks. Teams favored by 16.5+ are capped. Eliminated CFP teams become unavailable.
- **Pick constraint**: `Pick(user_id, week_id)` has a unique constraint — one pick per user per week.

## Game Rules (Business Logic Reference)

- 49 tracked teams, two lives per player
- Auto-picks select the biggest available favorite (capped at 16 points) for users who miss the deadline
- Revival rule: if ALL remaining 1-life players lose in the same week, all are revived
- Cumulative spread (lower = better) is the tiebreaker
