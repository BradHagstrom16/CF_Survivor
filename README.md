# CFB Survivor Pool

A Flask web application for managing a college football survivor pool. Players pick one team per week to win against the spread, with two lives, cumulative spread tiebreaking, and full College Football Playoff support.

**Live at:** [b1gbrad.pythonanywhere.com](https://b1gbrad.pythonanywhere.com)

## Game Rules

- **49 teams** from the preseason AP Top 25 and surrounding teams
- **Two lives** per player — lose a pick against the spread and you lose a life
- **Single use** — each team can only be picked once per regular season (resets for playoffs)
- **Spread tiebreaker** — cumulative spread tracks how safely you pick (lower is better)
- **16-point cap** — teams favored by 16.5+ are ineligible unless the underdog is also tracked
- **Auto-picks** — miss the deadline and the system picks the biggest available favorite
- **Playoff revival** — if every remaining 1-life player loses in the same week, all are revived
- **Playoff team reset** — regular season team usage resets for playoff weeks; teams eliminated from the CFP become unavailable

## Tech Stack

- **Python 3.13** / **Flask 3.1** with Blueprints
- **SQLite** via Flask-SQLAlchemy
- **Flask-Login** for authentication
- **Flask-WTF** / CSRFProtect for form security
- **Flask-Limiter** for rate limiting
- **Bootstrap 5.3** for the frontend
- **The Odds API** for game spreads and championship odds
- **PythonAnywhere** for hosting

## Project Structure

```
CF_Survivor/
├── app.py                  # App factory (create_app)
├── wsgi.py                 # WSGI entry point for PythonAnywhere
├── config.py               # Config classes (dev/prod/test)
├── extensions.py           # db, login_manager, csrf, limiter
├── models.py               # User, Team, Week, Game, Pick
├── timezone_utils.py       # Central timezone helpers
├── display_utils.py        # Week/playoff display helpers
├── db_maintenance.py       # Schema migration helpers
├── routes/
│   ├── auth.py             # Login, register, logout, change password
│   ├── main.py             # Standings, pick, my picks, results
│   └── admin.py            # Dashboard, weeks, games, results, users, payments
├── services/
│   └── game_logic.py       # Results processing, auto-picks, eligibility
├── templates/
│   ├── base.html
│   ├── index.html          # Standings page
│   ├── pick.html           # Pick submission
│   ├── my_picks.html       # Personal pick history
│   ├── weekly_results.html
│   ├── login.html
│   ├── register.html
│   ├── change_password.html
│   ├── errors/
│   │   ├── 404.html
│   │   └── 500.html
│   └── admin/
│       ├── dashboard.html
│       ├── create_week.html
│       ├── manage_games.html
│       ├── mark_results.html
│       ├── users.html
│       └── payments.html
├── static/css/style.css
├── import_games.py         # Fetch games & spreads from The Odds API
├── send_reminders.py       # Email reminder cron script
├── run_autopicks.py        # Auto-pick cron script
├── backup_database.py      # Backup manager
├── weekly_backup.py        # Cron backup wrapper
├── populate_teams.py       # One-time team initialization
├── manage_production.py    # Deployment workflow helper
├── .env.example            # Environment variable reference
├── requirements.txt
└── .gitignore
```

## Local Development Setup

```bash
# Clone and enter the project
git clone https://github.com/yourusername/CF_Survivor.git
cd CF_Survivor

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# Edit .env with your SECRET_KEY and other settings

# Initialize database and populate teams
flask init-db
python populate_teams.py

# Run the dev server
python app.py
# Visit http://localhost:5000
```

## Configuration

All configuration is via environment variables (loaded from `.env`). See `.env.example` for the full list:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | Flask session secret |
| `ENVIRONMENT` | `default` | `development`, `production`, or `testing` |
| `DATABASE_URL` | `sqlite:///picks.db` | SQLAlchemy database URI |
| `POOL_TIMEZONE` | `America/Chicago` | Timezone for all deadlines |
| `ENTRY_FEE` | `25` | Entry fee in dollars |
| `ODDS_API_KEY` | (required for imports) | [The Odds API](https://the-odds-api.com) key |
| `EMAIL_ADDRESS` | — | Gmail address for reminders |
| `EMAIL_PASSWORD` | — | Gmail app-specific password |
| `SMTP_SERVER` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `POOL_URL` | `https://b1gbrad.pythonanywhere.com` | Public URL for email links |

## Admin Weekly Routine

1. **Create the week** — Admin > Create Week. Set week number, start date, and deadline (typically Saturday 11:00 AM CT).

2. **Import games** — Run `python import_games.py`. Enter the week number and date range. The script fetches spreads from The Odds API (prefers DraftKings) and filters to tracked teams.

3. **Activate the week** — Admin > Dashboard > Activate. Only one week can be active at a time.

4. **Wait for the deadline** — Reminders go out Friday at 9:59 AM (25-hour warning) and Saturday at 9:59 AM (1-hour final warning).

5. **Process auto-picks** — After the deadline, run `python run_autopicks.py` or use the admin dashboard button. The system picks the biggest available favorite for anyone who missed the deadline.

6. **Mark results** — After games finish, Admin > Mark Results. Select home/away winner for each game, then submit. The system automatically processes picks, updates lives, and handles eliminations/revival.

7. **Repeat** — Create the next week and start again.

## PythonAnywhere Deployment

1. Upload code via git or the Files interface
2. Create a virtual environment: `mkvirtualenv --python=/usr/bin/python3.13 cfb`
3. Install: `pip install -r requirements.txt`
4. Set the WSGI file to point to `wsgi.py`:
   ```python
   import sys
   path = '/home/b1gbrad/cfb-survivor-pool'
   if path not in sys.path:
       sys.path.insert(0, path)
   from wsgi import app as application
   ```
5. Set environment variables in the WSGI file or via `.env`
6. Initialize database: `flask init-db && python populate_teams.py`
7. Reload the web app

### Scheduled Tasks (PythonAnywhere)

| Time | Script | Purpose |
|------|--------|---------|
| Friday 09:59 | `send_reminders.py` | 25-hour warning emails |
| Saturday 09:59 | `send_reminders.py` | 1-hour final warning emails |
| Saturday 11:05 | `run_autopicks.py` | Process auto-picks after deadline |
| Sunday 00:00 | `weekly_backup.py` | Automated database backup |

## Troubleshooting

**Database not found** — Run `flask init-db` then `python populate_teams.py`.

**Import games failing** — Check your `ODDS_API_KEY` in `.env` and verify remaining API quota at the-odds-api.com dashboard.

**Email reminders not sending** — Use a Gmail [app-specific password](https://myaccount.google.com/apppasswords), not your regular password. Verify `EMAIL_ADDRESS` and `EMAIL_PASSWORD` in `.env`.

**Timezone issues** — All deadlines use America/Chicago (Central Time). Python 3.9+ `zoneinfo` module is used (no external dependency).
