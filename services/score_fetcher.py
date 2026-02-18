"""
CFB Survivor Pool - Score Fetcher Service
==========================================
Fetches live/final scores from The Odds API, matches to Game records,
and auto-processes completed weeks.
"""

import logging

import requests
from flask import current_app

from extensions import db
from models import Week, Game, Team
from constants import API_BASE_URL, TEAM_NAME_MAP
from services.game_logic import process_week_results
from timezone_utils import deadline_has_passed, make_aware

logger = logging.getLogger(__name__)

# Reverse map: short display name -> set of API names that map to it
_SHORT_TO_API_NAMES = {}
for _api_name, _short in TEAM_NAME_MAP.items():
    _SHORT_TO_API_NAMES.setdefault(_short, set()).add(_api_name)


class ScoreFetcher:
    """Fetches scores from The Odds API and matches them to Game records."""

    def __init__(self):
        self.api_key = current_app.config.get('ODDS_API_KEY', '')
        self.scores_url = f"{API_BASE_URL}/scores"

    def fetch_scores_for_week(self, week_id):
        """Fetch scores from API and match to Game records for a given week.

        Returns a dict with:
            matched_completed: list of {game_id, home_team, away_team, home_score, away_score, match_method}
            matched_in_progress: list of same shape but game not yet finished
            unmatched: list of API events that couldn't be matched
            api_credits_remaining: int or None
            error: str or None
        """
        week = Week.query.get(week_id)
        if not week:
            return {'error': f'Week ID {week_id} not found'}

        if week.is_complete:
            return {'error': f'Week {week.week_number} is already complete'}

        deadline = make_aware(week.deadline)
        if not deadline_has_passed(deadline):
            return {'error': f'Week {week.week_number} deadline has not passed yet'}

        # Fetch scores from API
        params = {
            'apiKey': self.api_key,
            'daysFrom': 3,
        }

        try:
            response = requests.get(self.scores_url, params=params)
            if response.status_code != 200:
                return {'error': f'API returned status {response.status_code}'}
            api_events = response.json()
            credits_remaining = response.headers.get('x-requests-remaining')
        except Exception as e:
            return {'error': f'API request failed: {e}'}

        # Load games for this week
        games = Game.query.filter_by(week_id=week_id).all()

        # Build lookup dicts
        games_by_event_id = {}
        games_by_teams = {}
        for game in games:
            if game.api_event_id:
                games_by_event_id[game.api_event_id] = game
            home_name = game.get_home_team_display()
            away_name = game.get_away_team_display()
            if home_name and away_name:
                games_by_teams[(home_name, away_name)] = game

        matched_completed = []
        matched_in_progress = []
        unmatched = []

        for event in api_events:
            event_id = event.get('id')
            api_home = event.get('home_team', '')
            api_away = event.get('away_team', '')
            completed = event.get('completed', False)

            # Parse scores
            scores = event.get('scores')
            home_score = None
            away_score = None
            if scores:
                for score_entry in scores:
                    if score_entry.get('name') == api_home:
                        try:
                            home_score = int(score_entry.get('score', 0))
                        except (TypeError, ValueError):
                            home_score = None
                    elif score_entry.get('name') == api_away:
                        try:
                            away_score = int(score_entry.get('score', 0))
                        except (TypeError, ValueError):
                            away_score = None

            # Try to match by event_id first
            game = games_by_event_id.get(event_id)
            match_method = 'event_id' if game else None

            # Fallback: match by team names
            if not game:
                home_short = TEAM_NAME_MAP.get(api_home, api_home)
                away_short = TEAM_NAME_MAP.get(api_away, api_away)
                game = games_by_teams.get((home_short, away_short))
                if game:
                    match_method = 'team_name'

            if not game:
                # Check if either team is tracked (skip completely irrelevant games)
                home_short = TEAM_NAME_MAP.get(api_home, api_home)
                away_short = TEAM_NAME_MAP.get(api_away, api_away)
                tracked_teams = {g.get_home_team_display() for g in games} | {g.get_away_team_display() for g in games}
                if home_short in tracked_teams or away_short in tracked_teams:
                    unmatched.append({
                        'event_id': event_id,
                        'home_team': api_home,
                        'away_team': api_away,
                        'home_score': home_score,
                        'away_score': away_score,
                        'completed': completed,
                    })
                continue

            match_info = {
                'game_id': game.id,
                'home_team': game.get_home_team_display(),
                'away_team': game.get_away_team_display(),
                'home_score': home_score,
                'away_score': away_score,
                'match_method': match_method,
                'api_event_id': event_id,
            }

            if completed:
                matched_completed.append(match_info)
            else:
                matched_in_progress.append(match_info)

        return {
            'matched_completed': matched_completed,
            'matched_in_progress': matched_in_progress,
            'unmatched': unmatched,
            'api_credits_remaining': credits_remaining,
            'error': None,
        }

    def apply_scores_to_games(self, week_id, results):
        """Apply fetched score results to Game records.

        Args:
            week_id: The week ID
            results: List of match dicts from fetch_scores_for_week (matched_completed)

        Returns:
            dict with updated_count, skipped_count, tie_games
        """
        updated = 0
        skipped = 0
        tie_games = []

        for result in results:
            game = Game.query.get(result['game_id'])
            if not game:
                skipped += 1
                continue

            # Skip games already marked with a winner
            if game.home_team_won is not None:
                skipped += 1
                continue

            home_score = result.get('home_score')
            away_score = result.get('away_score')

            if home_score is None or away_score is None:
                skipped += 1
                continue

            game.home_score = home_score
            game.away_score = away_score

            # Save event ID if we matched by team name
            if result.get('api_event_id') and not game.api_event_id:
                game.api_event_id = result['api_event_id']

            if home_score == away_score:
                # Tie - flag for manual review, don't set winner
                tie_games.append({
                    'game_id': game.id,
                    'home_team': game.get_home_team_display(),
                    'away_team': game.get_away_team_display(),
                    'score': f'{home_score}-{away_score}',
                })
            else:
                game.home_team_won = home_score > away_score
                updated += 1

        db.session.commit()

        return {
            'updated_count': updated,
            'skipped_count': skipped,
            'tie_games': tie_games,
        }

    def auto_process_week(self, week_id):
        """Full pipeline: fetch scores -> apply -> process results if all games decided.

        Returns status dict with:
            status: 'completed' | 'partial' | 'already_complete' | 'error'
            details: description string
            fetch_results: raw fetch results
            apply_results: raw apply results (if applicable)
        """
        week = Week.query.get(week_id)
        if not week:
            return {'status': 'error', 'details': f'Week ID {week_id} not found'}

        if week.is_complete:
            return {'status': 'already_complete', 'details': f'Week {week.week_number} already complete'}

        # Step 1: Fetch scores
        fetch_results = self.fetch_scores_for_week(week_id)
        if fetch_results.get('error'):
            return {
                'status': 'error',
                'details': fetch_results['error'],
                'fetch_results': fetch_results,
            }

        # Step 2: Apply completed scores
        completed = fetch_results.get('matched_completed', [])
        if not completed:
            return {
                'status': 'partial',
                'details': f'No completed games found. In progress: {len(fetch_results.get("matched_in_progress", []))}',
                'fetch_results': fetch_results,
            }

        apply_results = self.apply_scores_to_games(week_id, completed)

        # Step 3: Check if all games are decided
        games = Game.query.filter_by(week_id=week_id).all()
        all_decided = all(g.home_team_won is not None for g in games)
        in_progress = fetch_results.get('matched_in_progress', [])
        unmatched = fetch_results.get('unmatched', [])
        ties = apply_results.get('tie_games', [])

        if ties:
            return {
                'status': 'partial',
                'details': f'Tie games require manual review: {len(ties)}',
                'fetch_results': fetch_results,
                'apply_results': apply_results,
            }

        if not all_decided:
            pending_count = sum(1 for g in games if g.home_team_won is None)
            return {
                'status': 'partial',
                'details': f'{apply_results["updated_count"]} games updated, {pending_count} still pending',
                'fetch_results': fetch_results,
                'apply_results': apply_results,
            }

        # All games decided - process results
        week.is_complete = True
        db.session.commit()
        process_week_results(week_id)

        return {
            'status': 'completed',
            'details': f'Week {week.week_number} fully processed. {apply_results["updated_count"]} games scored.',
            'fetch_results': fetch_results,
            'apply_results': apply_results,
        }
