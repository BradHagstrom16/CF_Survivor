"""
NCAA Football API Game Importer
Imports games from The Odds API with intelligent filtering and team matching.
All times are properly converted to Central timezone.
"""

import logging
import os
import sys

from zoneinfo import ZoneInfo
import requests
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from extensions import db
from db_maintenance import ensure_team_national_title_odds_column
from models import Team, Week, Game
from constants import TEAM_NAME_MAP, API_BASE_URL

logger = logging.getLogger(__name__)

app = create_app()


class NCAAFootballAPIImporter:
    """Manages the import of college football games from The Odds API."""

    def __init__(self):
        with app.app_context():
            self.api_key = app.config.get('ODDS_API_KEY', '')
        self.base_url = f"{API_BASE_URL}/odds"
        self.championship_url = (
            "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf_championship_winner/odds"
        )

        self.utc_tz = timezone.utc
        self.chicago_tz = ZoneInfo('America/Chicago')

        self.team_name_map = TEAM_NAME_MAP

        # Build tracked teams dynamically from the Team table
        with app.app_context():
            self.tracked_teams = {t.name for t in Team.query.all()}

    def fetch_games_for_date_range(self, start_date, end_date):
        start_utc = start_date.replace(tzinfo=self.chicago_tz).astimezone(self.utc_tz)
        end_utc = end_date.replace(hour=23, minute=59, tzinfo=self.chicago_tz).astimezone(self.utc_tz)

        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'spreads',
            'oddsFormat': 'american',
            'commenceTimeFrom': start_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'commenceTimeTo': end_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

        print(f"\nFetching games from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            if response.status_code == 200:
                games = response.json()
                remaining = response.headers.get('x-requests-remaining', 'unknown')
                used = response.headers.get('x-requests-used', 'unknown')
                print(f"Fetched {len(games)} games. API: {used} used, {remaining} remaining")
                return games
            else:
                print(f"API request failed: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching from API: {e}")
            return []

    @staticmethod
    def _format_american_odds(price):
        try:
            price_int = int(price)
        except (TypeError, ValueError):
            return None
        return f"+{price_int}" if price_int > 0 else str(price_int)

    def fetch_championship_odds(self):
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'outrights',
            'oddsFormat': 'american',
        }
        try:
            response = requests.get(self.championship_url, params=params, timeout=30)
        except Exception as exc:
            print(f"Error fetching championship odds: {exc}")
            return {}, None

        if response.status_code != 200:
            print(f"Championship odds request failed: {response.status_code}")
            return {}, None

        data = response.json()
        if not data:
            return {}, None

        bookmakers = data[0].get('bookmakers', [])
        if not bookmakers:
            return {}, None

        draftkings = None
        fallback = None
        for bm in bookmakers:
            if bm.get('key') == 'draftkings':
                draftkings = bm
                break
            if not fallback:
                fallback = bm

        selected = draftkings or fallback
        if not selected:
            return {}, None

        fallback_title = fallback.get('title') if not draftkings and fallback else None

        outcomes = []
        for market in selected.get('markets', []):
            if market.get('key') == 'outrights':
                outcomes = market.get('outcomes', [])
                break

        odds_map = {}
        for outcome in outcomes:
            api_name = outcome.get('name')
            price = outcome.get('price')
            canonical = self.team_name_map.get(api_name, api_name)
            if canonical in self.tracked_teams and price is not None:
                formatted = self._format_american_odds(price)
                if formatted:
                    odds_map[canonical] = formatted

        return odds_map, fallback_title

    def update_championship_odds(self):
        if not ensure_team_national_title_odds_column(app, db):
            return

        odds_map, fallback_title = self.fetch_championship_odds()
        if not odds_map:
            print("No national championship odds updated.")
            return

        with app.app_context():
            teams = Team.query.all()
            updated = 0
            cleared = 0
            for team in teams:
                new_value = odds_map.get(team.name)
                if new_value is None:
                    if team.national_title_odds is not None:
                        team.national_title_odds = None
                        cleared += 1
                elif new_value != team.national_title_odds:
                    team.national_title_odds = new_value
                    updated += 1
            db.session.commit()

        print(f"Championship odds: {len(odds_map)} received, {updated} updated, {cleared} cleared"
              + (f" (fallback: {fallback_title})" if fallback_title else ""))

    def extract_spread_from_game(self, game_data):
        bookmakers = game_data.get('bookmakers', [])
        if not bookmakers:
            return (0.0, 0.0, None)

        draftkings = None
        fallback = None
        for bm in bookmakers:
            if bm.get('key') == 'draftkings':
                draftkings = bm
                break
            elif not fallback:
                fallback = bm

        selected = draftkings or fallback
        bm_name = selected.get('title', 'Unknown')

        for market in selected.get('markets', []):
            if market.get('key') == 'spreads':
                home_spread = 0.0
                away_spread = 0.0
                for outcome in market.get('outcomes', []):
                    point = float(outcome.get('point', 0))
                    if outcome.get('name') == game_data.get('home_team'):
                        home_spread = point
                    elif outcome.get('name') == game_data.get('away_team'):
                        away_spread = point
                note = f"Fallback: {bm_name}" if not draftkings and fallback else None
                return (home_spread, away_spread, note)

        return (0.0, 0.0, None)

    def should_import_game(self, game_data, home_spread, away_spread):
        home_team = game_data.get('home_team')
        away_team = game_data.get('away_team')
        home_clean = self.team_name_map.get(home_team, home_team)
        away_clean = self.team_name_map.get(away_team, away_team)
        home_tracked = home_clean in self.tracked_teams
        away_tracked = away_clean in self.tracked_teams

        if not home_tracked and not away_tracked:
            return False, None

        if home_spread < -16:
            if away_tracked:
                return True, None
            return False, f"{home_team} favored by {abs(home_spread)} (>16)"

        if away_spread < -16:
            if home_tracked:
                return True, None
            return False, f"{away_team} favored by {abs(away_spread)} (>16)"

        return True, None

    def import_games_to_database(self, games_data, week_number):
        with app.app_context():
            week = Week.query.filter_by(week_number=week_number).first()
            if not week:
                print(f"\nError: Week {week_number} doesn't exist. Create it in admin first.")
                return False

            all_teams = {t.name: t for t in Team.query.all()}
            imported = 0
            skipped = 0
            excluded = []
            fallbacks = []

            print(f"\nProcessing {len(games_data)} games for Week {week_number}...")

            for gd in games_data:
                api_home = gd.get('home_team')
                api_away = gd.get('away_team')
                hs, aws, bm_note = self.extract_spread_from_game(gd)
                if bm_note:
                    fallbacks.append(f"{api_away} @ {api_home}: {bm_note}")

                ok, reason = self.should_import_game(gd, hs, aws)
                if not ok:
                    if reason:
                        excluded.append(reason)
                    skipped += 1
                    continue

                hc = self.team_name_map.get(api_home, api_home)
                ac = self.team_name_map.get(api_away, api_away)
                ht = all_teams.get(hc)
                at = all_teams.get(ac)

                ct = gd.get('commence_time', '')
                if ct:
                    gt_utc = datetime.fromisoformat(ct.replace('Z', '+00:00'))
                    if gt_utc.tzinfo is None:
                        gt_utc = gt_utc.replace(tzinfo=self.utc_tz)
                    gt_chi = gt_utc.astimezone(self.chicago_tz)
                else:
                    gt_chi = datetime.now(self.chicago_tz)

                if ht and at:
                    existing = Game.query.filter_by(
                        week_id=week.id, home_team_id=ht.id, away_team_id=at.id,
                    ).first()
                    if existing:
                        print(f"  Already exists: {ac} @ {hc}")
                        continue

                game = Game(
                    week_id=week.id,
                    home_team_id=ht.id if ht else None,
                    away_team_id=at.id if at else None,
                    home_team_name=None if ht else api_home,
                    away_team_name=None if at else api_away,
                    home_team_spread=hs,
                    game_time=gt_chi,
                    api_event_id=gd.get('id'),
                )
                db.session.add(game)
                imported += 1
                td = gt_chi.strftime('%m/%d %I:%M %p CT')
                print(f"  Added: {ac} @ {hc} | {td} | Spread: {hs:.1f}")

            db.session.commit()
            print(f"\nImported: {imported} | Skipped: {skipped}")
            if fallbacks:
                print(f"Fallback bookmakers: {len(fallbacks)}")
            if excluded:
                print(f"Excluded (spread >16): {len(excluded)}")
            return True


def suggest_dates_for_week(week_number):
    week_1_start = datetime(2025, 8, 28)
    start = week_1_start + timedelta(days=(week_number - 1) * 7)
    return start, start + timedelta(days=4)


def main():
    print("\n" + "=" * 60)
    print("NCAA Football API Game Importer")
    print("=" * 60)

    while True:
        week_input = input("\nEnter week number to import (1-15): ").strip()
        try:
            week_num = int(week_input)
            if 1 <= week_num <= 15:
                break
            print("Please enter a number between 1 and 15")
        except ValueError:
            print("Please enter a valid number")

    sug_start, sug_end = suggest_dates_for_week(week_num)
    print(f"\nSuggested: {sug_start.strftime('%Y-%m-%d')} to {sug_end.strftime('%Y-%m-%d')}")

    si = input(f"Start date [{sug_start.strftime('%Y-%m-%d')}]: ").strip()
    start_date = datetime.strptime(si, '%Y-%m-%d') if si else sug_start

    ei = input(f"End date [{sug_end.strftime('%Y-%m-%d')}]: ").strip()
    end_date = datetime.strptime(ei, '%Y-%m-%d') if ei else sug_end

    importer = NCAAFootballAPIImporter()
    importer.update_championship_odds()
    games = importer.fetch_games_for_date_range(start_date, end_date)

    if not games:
        print("\nNo games found for this date range.")
        return

    print(f"\nFound {len(games)} games from the API")
    if input("Proceed with import? (y/n): ").strip().lower() == 'y':
        importer.import_games_to_database(games, week_num)
    else:
        print("Import cancelled")


if __name__ == "__main__":
    main()
