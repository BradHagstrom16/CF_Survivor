"""
CFB Survivor Pool - Automation Service
========================================
Orchestrates weekly operations: setup, spread updates, score fetching,
and admin notifications.
"""

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from zoneinfo import ZoneInfo
import requests
from flask import current_app

from extensions import db
from models import Team, Week, Game
from constants import (
    API_BASE_URL, TEAM_NAME_MAP, SEASON_SCHEDULE,
)
from services.score_fetcher import ScoreFetcher
from timezone_utils import deadline_has_passed, make_aware

logger = logging.getLogger(__name__)

CHICAGO_TZ = ZoneInfo('America/Chicago')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def send_admin_email(subject, body):
    """Send an email to the admin using app config SMTP credentials."""
    email_address = current_app.config.get('EMAIL_ADDRESS', '')
    email_password = current_app.config.get('EMAIL_PASSWORD', '')
    smtp_server = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = current_app.config.get('SMTP_PORT', 587)

    if not email_address or not email_password:
        logger.warning("Email credentials not configured; skipping admin email.")
        return False

    msg = MIMEText(body)
    msg['From'] = email_address
    msg['To'] = email_address  # send to self (admin)
    msg['Subject'] = f'[CFB Survivor] {subject}'

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)
        logger.info("Admin email sent: %s", subject)
        return True
    except Exception as e:
        logger.error("Failed to send admin email: %s", e)
        return False


def _calculate_week_dates(week_number):
    """Compute start_date and deadline for a given week number.

    Returns (start_date, deadline) as timezone-aware Chicago datetimes.
    """
    week_1_start = datetime.strptime(SEASON_SCHEDULE['week_1_start'], '%Y-%m-%d')
    start_date = week_1_start + timedelta(weeks=week_number - 1)

    # Deadline: Saturday at configured hour
    deadline_hour = SEASON_SCHEDULE['default_deadline_hour']
    deadline_minute = SEASON_SCHEDULE['default_deadline_minute']

    # Find the Saturday of the week starting on Thursday
    days_until_saturday = (5 - start_date.weekday()) % 7
    saturday = start_date + timedelta(days=days_until_saturday)
    deadline = saturday.replace(hour=deadline_hour, minute=deadline_minute, second=0, microsecond=0)

    start_aware = start_date.replace(tzinfo=CHICAGO_TZ)
    deadline_aware = deadline.replace(tzinfo=CHICAGO_TZ)

    return start_aware, deadline_aware


def _get_special_week_info(week_number):
    """Return special week info if applicable.

    Returns dict with 'is_playoff' and 'round_name', or None for regular weeks.
    """
    special = SEASON_SCHEDULE.get('special_weeks', {}).get(week_number)
    if special:
        return {
            'is_playoff': special.get('is_playoff', False),
            'round_name': special.get('name'),
        }
    return None


# ---------------------------------------------------------------------------
# Main automation functions
# ---------------------------------------------------------------------------

def run_setup():
    """Create the next week, import games, and activate it.

    Idempotent: skips if the next week already exists and has games.
    Returns a status dict.
    """
    # Determine next week number
    last_week = Week.query.order_by(Week.week_number.desc()).first()
    next_week_num = (last_week.week_number + 1) if last_week else 1

    max_weeks = SEASON_SCHEDULE['regular_season_weeks']
    special_weeks = SEASON_SCHEDULE.get('special_weeks', {})
    max_week = max(max_weeks, max(special_weeks.keys()) if special_weeks else max_weeks)

    if next_week_num > max_week:
        return {'status': 'skipped', 'details': f'Season complete (max week {max_week})'}

    # Check if week already exists
    existing = Week.query.filter_by(week_number=next_week_num).first()
    if existing:
        game_count = Game.query.filter_by(week_id=existing.id).count()
        if game_count > 0:
            return {
                'status': 'skipped',
                'details': f'Week {next_week_num} already exists with {game_count} games',
            }

    # Calculate dates
    start_date, deadline = _calculate_week_dates(next_week_num)
    special = _get_special_week_info(next_week_num)
    is_playoff = special['is_playoff'] if special else False
    round_name = special['round_name'] if special else None

    # Create week if it doesn't exist
    if not existing:
        existing = Week(
            week_number=next_week_num,
            start_date=start_date,
            deadline=deadline,
            is_active=False,
            is_playoff_week=is_playoff,
            round_name=round_name,
        )
        db.session.add(existing)
        db.session.commit()
        logger.info("Created Week %d", next_week_num)

    # Import games (non-interactive)
    from import_games import NCAAFootballAPIImporter
    importer = NCAAFootballAPIImporter()

    # Calculate date range for API fetch
    start_naive = start_date.replace(tzinfo=None)
    end_naive = start_naive + timedelta(days=4)

    games = importer.fetch_games_for_date_range(start_naive, end_naive)
    if games:
        importer.import_games_to_database(games, next_week_num)
    game_count = Game.query.filter_by(week_id=existing.id).count()

    display_name = round_name or f'Week {next_week_num}'

    if game_count == 0:
        logger.error("Week %d created but has 0 games - NOT activating", next_week_num)
        return {
            'status': 'error',
            'details': f'{display_name} created but no games were imported. Week NOT activated.',
            'week_number': next_week_num,
            'game_count': 0,
        }

    # Activate the week (deactivate others)
    Week.query.update({'is_active': False})
    existing.is_active = True
    db.session.commit()

    return {
        'status': 'created',
        'details': f'{display_name} created with {game_count} games and activated',
        'week_number': next_week_num,
        'game_count': game_count,
    }


def run_spread_update():
    """Fetch latest odds and update spreads for the active week's games.

    Skips games where spread_locked_at is already set.
    Returns a status dict.
    """
    week = Week.query.filter_by(is_active=True).first()
    if not week:
        return {'status': 'skipped', 'details': 'No active week found'}

    if week.is_complete:
        return {'status': 'skipped', 'details': f'Week {week.week_number} is already complete'}

    games = Game.query.filter_by(week_id=week.id).all()
    if not games:
        return {'status': 'skipped', 'details': f'Week {week.week_number} has no games'}

    # Fetch odds from API
    api_key = current_app.config.get('ODDS_API_KEY', '')
    utc_tz = timezone.utc
    chicago_tz = CHICAGO_TZ

    # Build date range from the week's games
    game_times = [g.game_time for g in games if g.game_time]
    if not game_times:
        return {'status': 'skipped', 'details': 'No game times available'}

    earliest = min(game_times)
    latest = max(game_times)

    # Ensure timezone-aware for API
    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=chicago_tz)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=chicago_tz)

    start_utc = earliest.astimezone(utc_tz) - timedelta(hours=6)
    end_utc = latest.astimezone(utc_tz) + timedelta(hours=6)

    params = {
        'apiKey': api_key,
        'regions': 'us',
        'markets': 'spreads',
        'oddsFormat': 'american',
        'commenceTimeFrom': start_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'commenceTimeTo': end_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    try:
        url = f"{API_BASE_URL}/odds"
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            return {'status': 'error', 'details': f'API returned status {response.status_code}'}
        api_events = response.json()
        credits_remaining = response.headers.get('x-requests-remaining', 'unknown')
    except Exception as e:
        return {'status': 'error', 'details': f'API request failed: {e}'}

    # Build event lookup
    events_by_id = {e.get('id'): e for e in api_events}
    events_by_teams = {}
    for e in api_events:
        home_short = TEAM_NAME_MAP.get(e.get('home_team', ''), e.get('home_team', ''))
        away_short = TEAM_NAME_MAP.get(e.get('away_team', ''), e.get('away_team', ''))
        events_by_teams[(home_short, away_short)] = e

    updated = 0
    locked = 0
    now = datetime.now(timezone.utc)

    for game in games:
        if game.spread_locked_at:
            locked += 1
            continue

        # Match API event
        event = None
        if game.api_event_id:
            event = events_by_id.get(game.api_event_id)

        if not event:
            home_name = game.get_home_team_display()
            away_name = game.get_away_team_display()
            event = events_by_teams.get((home_name, away_name))

        if not event:
            continue

        # Extract spread
        bookmakers = event.get('bookmakers', [])
        draftkings = None
        fallback = None
        for bm in bookmakers:
            if bm.get('key') == 'draftkings':
                draftkings = bm
                break
            elif not fallback:
                fallback = bm

        selected = draftkings or fallback
        if not selected:
            continue

        for market in selected.get('markets', []):
            if market.get('key') == 'spreads':
                for outcome in market.get('outcomes', []):
                    if outcome.get('name') == event.get('home_team'):
                        new_spread = float(outcome.get('point', 0))
                        game.home_team_spread = new_spread
                        game.spread_locked_at = now
                        updated += 1
                        break
                break

    db.session.commit()

    return {
        'status': 'updated',
        'details': f'{updated} spreads updated, {locked} already locked',
        'api_credits_remaining': credits_remaining,
        'updated': updated,
        'locked': locked,
    }


def run_scores():
    """Find incomplete weeks past deadline and auto-process scores.

    Returns a status dict with results for each week processed.
    """
    weeks = Week.query.filter_by(is_complete=False).all()
    results = []

    for week in weeks:
        deadline = make_aware(week.deadline)
        if not deadline_has_passed(deadline):
            continue

        fetcher = ScoreFetcher()
        result = fetcher.auto_process_week(week.id)
        results.append({
            'week_number': week.week_number,
            **result,
        })

    if not results:
        summary = 'No incomplete weeks past deadline'
    else:
        lines = []
        for r in results:
            lines.append(f"Week {r['week_number']}: {r['status']} - {r['details']}")
        summary = '\n'.join(lines)

    # Send admin email with summary
    if results:
        try:
            send_admin_email(
                'Score Sync Results',
                f'Score sync completed at {datetime.now(CHICAGO_TZ).strftime("%Y-%m-%d %I:%M %p CT")}\n\n{summary}',
            )
        except Exception as e:
            logger.warning("Failed to send admin email: %s", e)

    return {
        'status': 'processed' if results else 'skipped',
        'details': summary,
        'week_results': results,
    }


def run_status():
    """Print season summary info.

    Returns a status dict with season overview.
    """
    weeks = Week.query.order_by(Week.week_number).all()
    active_week = Week.query.filter_by(is_active=True).first()

    from models import User, Pick
    total_users = User.query.count()
    active_users = User.query.filter_by(is_eliminated=False).count()

    total_games = Game.query.count()
    total_picks = Pick.query.count()
    complete_weeks = sum(1 for w in weeks if w.is_complete)

    lines = [
        f"Season Overview",
        f"  Weeks created: {len(weeks)}",
        f"  Weeks complete: {complete_weeks}",
        f"  Active week: {active_week.week_number if active_week else 'None'}",
        f"  Total games: {total_games}",
        f"  Total picks: {total_picks}",
        f"  Total users: {total_users} ({active_users} active)",
    ]

    return {
        'status': 'ok',
        'details': '\n'.join(lines),
        'active_week': active_week.week_number if active_week else None,
        'total_weeks': len(weeks),
        'complete_weeks': complete_weeks,
        'total_users': total_users,
        'active_users': active_users,
        'total_games': total_games,
    }
