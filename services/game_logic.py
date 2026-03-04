"""
CF Survivor Pool - Game Logic Service
======================================
Core business logic: result processing, auto-picks, team eligibility.
"""

import logging

from flask import current_app
from sqlalchemy import func

from extensions import db
from models import User, Team, Week, Game, Pick
from timezone_utils import (
    get_current_time, get_utc_time, make_aware, deadline_has_passed,
)
from display_utils import is_week_playoff, get_cfp_eliminated_teams

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Team eligibility (consolidates the duplicated logic from app.py)
# ---------------------------------------------------------------------------

def get_game_for_team(week_id, team_id):
    """Return the Game in this week that involves the given team."""
    return Game.query.filter_by(week_id=week_id).filter(
        db.or_(Game.home_team_id == team_id, Game.away_team_id == team_id)
    ).first()


def get_used_team_ids(user_id, week, *, exclude_current=True):
    """Return set of team IDs the user has already picked in the current phase."""
    q = db.session.query(Pick.team_id).join(Week)

    if is_week_playoff(week):
        q = q.filter(Week.is_playoff_week == True)
    else:
        q = q.filter(Week.is_playoff_week == False)

    q = q.filter(Pick.user_id == user_id)
    if exclude_current:
        q = q.filter(Pick.week_id != week.id)

    return {t[0] for t in q.all()}


# ---------------------------------------------------------------------------
# Result processing
# ---------------------------------------------------------------------------

def process_week_results(week_id):
    """Process pick results and update user lives. Includes revival rule."""
    week = db.session.get(Week, week_id)
    picks = Pick.query.filter_by(week_id=week_id).all()

    # Track active users who had 1 life at START of week (for revival rule)
    active_users = User.query.filter_by(is_eliminated=False).all()
    active_user_ids = {user.id for user in active_users}
    users_with_one_life_before = [
        user.id for user in active_users if user.lives_remaining == 1
    ]

    for pick in picks:
        game = Game.query.filter_by(week_id=week_id).filter(
            db.or_(
                Game.home_team_id == pick.team_id,
                Game.away_team_id == pick.team_id,
            ),
            Game.home_team_won != None,  # noqa: E711
        ).first()

        if game:
            if pick.team_id == game.home_team_id:
                pick.is_correct = game.home_team_won
            else:
                pick.is_correct = not game.home_team_won

            if not pick.is_correct:
                user = pick.user
                user.lives_remaining -= 1
                if user.lives_remaining <= 0:
                    user.is_eliminated = True
                    user.lives_remaining = 0

        pick.user.calculate_cumulative_spread()

    db.session.commit()

    # Revival rule: if ALL users who had 1 life before this week lost, revive them
    if users_with_one_life_before:
        one_lifers = User.query.filter(
            User.id.in_(users_with_one_life_before)
        ).all()
        if all(u.lives_remaining == 0 for u in one_lifers):
            for user in one_lifers:
                user.lives_remaining = 1
                user.is_eliminated = False
            db.session.commit()
            logger.info(
                "REVIVAL RULE ACTIVATED: Week %s - %d users revived",
                week.week_number,
                len(one_lifers),
            )


# ---------------------------------------------------------------------------
# Auto-picks
# ---------------------------------------------------------------------------

def process_autopicks(week_id):
    """Process auto-picks for users who missed the deadline."""
    week = db.session.get(Week, week_id)
    deadline = make_aware(week.deadline)

    if not deadline_has_passed(deadline):
        return {"processed": False, "reason": "Deadline not yet passed"}

    active_users = User.query.filter_by(is_eliminated=False).all()
    existing_picks = Pick.query.filter_by(week_id=week_id).all()
    users_with_picks = {pick.user_id for pick in existing_picks}

    users_needing_autopick = [
        u for u in active_users if u.id not in users_with_picks
    ]

    if not users_needing_autopick:
        return {"processed": True, "autopicks": 0, "reason": "All active users have picks"}

    autopicks_made = []
    autopicks_failed = []

    current_time = get_current_time()
    games = [
        g for g in Game.query.filter_by(week_id=week_id).all()
        if not g.game_time or make_aware(g.game_time) > current_time
    ]

    cfp_eliminated_names = set()
    if is_week_playoff(week):
        cfp_eliminated_names = get_cfp_eliminated_teams()

    for user in users_needing_autopick:
        used_team_ids = get_used_team_ids(user.id, week)

        best_team = None
        best_spread = None
        best_favoritism = -999

        for game in games:
            # Check home team
            if game.home_team and game.home_team_id not in used_team_ids:
                if is_week_playoff(week) and game.home_team.name in cfp_eliminated_names:
                    continue
                home_favoritism = -game.home_team_spread
                if 0 < home_favoritism <= 16:
                    if home_favoritism > best_favoritism:
                        best_favoritism = home_favoritism
                        best_spread = game.home_team_spread
                        best_team = game.home_team

            # Check away team
            if game.away_team and game.away_team_id not in used_team_ids:
                if is_week_playoff(week) and game.away_team.name in cfp_eliminated_names:
                    continue
                away_favoritism = game.home_team_spread
                if 0 < away_favoritism <= 16:
                    if away_favoritism > best_favoritism:
                        best_favoritism = away_favoritism
                        best_spread = -game.home_team_spread
                        best_team = game.away_team

        # Fallback: pick the smallest underdog
        if not best_team:
            smallest_underdog = None
            smallest_underdog_points = 999

            for game in games:
                if game.home_team and game.home_team_id not in used_team_ids:
                    if is_week_playoff(week) and game.home_team.name in cfp_eliminated_names:
                        continue
                    if game.home_team_spread > 0 and game.home_team_spread < smallest_underdog_points:
                        smallest_underdog_points = game.home_team_spread
                        smallest_underdog = game.home_team
                        best_spread = game.home_team_spread

                if game.away_team and game.away_team_id not in used_team_ids:
                    if is_week_playoff(week) and game.away_team.name in cfp_eliminated_names:
                        continue
                    away_spread = -game.home_team_spread
                    if away_spread > 0 and away_spread < smallest_underdog_points:
                        smallest_underdog_points = away_spread
                        smallest_underdog = game.away_team
                        best_spread = away_spread

            best_team = smallest_underdog

        if best_team:
            auto_pick = Pick(
                user_id=user.id,
                week_id=week_id,
                team_id=best_team.id,
                created_at=get_utc_time(),
            )
            db.session.add(auto_pick)
            user.calculate_cumulative_spread()

            if best_spread and best_spread < 0:
                favoritism_text = f"favored by {-best_spread} points"
            elif best_spread and best_spread > 0:
                favoritism_text = f"underdog by {best_spread} points"
            else:
                favoritism_text = "pick'em"

            autopicks_made.append({
                "user": user.username,
                "team": best_team.name,
                "spread": best_spread,
                "description": favoritism_text,
            })
            logger.info("Auto-pick: %s -> %s (%s)", user.username, best_team.name, favoritism_text)
        else:
            autopicks_failed.append({
                "user": user.username,
                "reason": "No eligible teams available",
            })
            logger.warning("Auto-pick failed: %s - No eligible teams", user.username)

    if autopicks_made:
        db.session.commit()

    return {
        "processed": True,
        "autopicks": len(autopicks_made),
        "failed": len(autopicks_failed),
        "details": autopicks_made,
        "failures": autopicks_failed,
    }


def check_and_process_autopicks():
    """Check all active weeks and process autopicks if past deadline."""
    weeks = Week.query.filter_by(is_complete=False).all()
    results = []
    for week in weeks:
        deadline = make_aware(week.deadline)
        if deadline_has_passed(deadline):
            result = process_autopicks(week.id)
            if result["processed"] and result["autopicks"] > 0:
                results.append(
                    f"Week {week.week_number}: {result['autopicks']} auto-picks made"
                )
    return results
