"""
CF Survivor Pool - Main Routes
================================
Public/user routes: standings, picks, results.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import User, Team, Week, Game, Pick
from constants import TEAM_CONFERENCES
from timezone_utils import (
    get_current_time, get_utc_time, make_aware, deadline_has_passed,
    format_deadline, to_pool_time, safe_is_after, POOL_TZ_NAME,
)
from display_utils import (
    get_week_display_name, get_week_short_label, is_week_playoff,
    get_playoff_teams, get_cfp_eliminated_teams, get_cfp_active_teams,
    get_cfp_teams_on_bye, get_cfp_teams_in_week,
)
from services.game_logic import get_used_team_ids, get_game_for_team

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    current_week = Week.query.filter_by(is_active=True).first()

    user_pick = None
    user_pick_spread = None
    games_by_team = {}

    if current_week:
        # Bulk-load all games for the current week into a lookup dict
        for game in Game.query.filter_by(week_id=current_week.id).all():
            if game.home_team_id:
                games_by_team[game.home_team_id] = game
            if game.away_team_id:
                games_by_team[game.away_team_id] = game

    if current_week and current_user.is_authenticated:
        user_pick = Pick.query.filter_by(
            user_id=current_user.id, week_id=current_week.id
        ).first()
        if user_pick:
            game = games_by_team.get(user_pick.team_id)
            if game:
                if user_pick.team_id == game.home_team_id:
                    user_pick_spread = game.home_team_spread
                else:
                    user_pick_spread = -game.home_team_spread

    week_picks = {}
    show_picks = False
    if current_week:
        deadline = make_aware(current_week.deadline)
        show_picks = deadline_has_passed(deadline)

        if show_picks:
            all_picks = Pick.query.filter_by(week_id=current_week.id).all()
            for pick in all_picks:
                game = games_by_team.get(pick.team_id)
                if game:
                    if pick.team_id == game.home_team_id:
                        spread = game.home_team_spread
                    else:
                        spread = -game.home_team_spread
                    week_picks[pick.user_id] = f"{pick.team.name} ({spread:+.1f})"
                else:
                    week_picks[pick.user_id] = pick.team.name

    # Standings sorted by lives desc, spread asc (lower is better)
    users = User.query.filter_by(is_eliminated=False).order_by(
        User.lives_remaining.desc(),
        User.cumulative_spread.asc(),
    ).all()

    eliminated_users = User.query.filter_by(is_eliminated=True).all()

    # Championship detection
    champion_picks = []
    champion_correct = 0
    weeks_played = 0

    if len(users) == 1 and len(eliminated_users) > 0:
        champion = users[0]
        champion_picks = (
            Pick.query.filter_by(user_id=champion.id)
            .join(Week)
            .order_by(Week.week_number)
            .all()
        )
        champion_correct = sum(1 for p in champion_picks if p.is_correct is True)
        weeks_played = Week.query.filter_by(is_complete=True).count()

        # Bulk-load games for all champion pick weeks
        champion_week_ids = {p.week_id for p in champion_picks}
        champion_games_by_team = {}
        for game in Game.query.filter(Game.week_id.in_(champion_week_ids)).all():
            if game.home_team_id:
                champion_games_by_team[(game.week_id, game.home_team_id)] = game
            if game.away_team_id:
                champion_games_by_team[(game.week_id, game.away_team_id)] = game

        for pick in champion_picks:
            game = champion_games_by_team.get((pick.week_id, pick.team_id))
            if game:
                if pick.team_id == game.home_team_id:
                    pick.spread = game.home_team_spread
                else:
                    pick.spread = -game.home_team_spread
            else:
                pick.spread = None

    total_participants = User.query.count()
    entry_fee = current_app.config.get('ENTRY_FEE', 25)
    prize_pool = total_participants * entry_fee

    return render_template(
        'index.html',
        current_week=current_week,
        user_pick=user_pick,
        user_pick_spread=user_pick_spread,
        users=users,
        eliminated_users=eliminated_users,
        week_picks=week_picks,
        show_picks=show_picks,
        format_deadline=format_deadline,
        timezone=POOL_TZ_NAME,
        champion_picks=champion_picks,
        champion_correct=champion_correct,
        weeks_played=weeks_played,
        total_participants=total_participants,
        prize_pool=prize_pool,
    )


@main_bp.route('/pick/<int:week_number>', methods=['GET', 'POST'])
@login_required
def make_pick(week_number):
    current_time = get_current_time()

    if current_user.is_eliminated:
        flash('Sorry, you have been eliminated from the pool.', 'error')
        return redirect(url_for('main.index'))

    week = Week.query.filter_by(week_number=week_number).first_or_404()

    if deadline_has_passed(week.deadline):
        flash('The deadline for this week has passed.', 'error')
        return redirect(url_for('main.index'))

    existing_pick = Pick.query.filter_by(
        user_id=current_user.id, week_id=week.id
    ).first()

    pick_locked = False
    if existing_pick:
        existing_game = get_game_for_team(week.id, existing_pick.team_id)

        if existing_game and existing_game.game_time:
            if safe_is_after(current_time, existing_game.game_time):
                pick_locked = True

    cfp_eliminated_names = set()
    if is_week_playoff(week):
        cfp_eliminated_names = get_cfp_eliminated_teams()

    if request.method == 'POST':
        if pick_locked:
            flash('Your pick is locked - that game has already started.', 'error')
        else:
            try:
                team_id = int(request.form.get('team_id', ''))
            except (ValueError, TypeError):
                flash('Invalid team selection.', 'error')
                return redirect(url_for('main.make_pick', week_number=week_number))

            team = db.session.get(Team, team_id)
            if not team:
                flash('Invalid team selection.', 'error')
                return redirect(url_for('main.make_pick', week_number=week_number))

            new_team_game = get_game_for_team(week.id, team_id)

            if new_team_game and new_team_game.game_time:
                if safe_is_after(current_time, new_team_game.game_time):
                    flash('Cannot pick this team - their game has already started.', 'error')
                    return redirect(url_for('main.make_pick', week_number=week_number))

            if is_week_playoff(week):
                team = db.session.get(Team, team_id)
                if team and team.name in cfp_eliminated_names:
                    flash('Cannot pick this team - they have been eliminated from the playoffs.', 'error')
                    return redirect(url_for('main.make_pick', week_number=week_number))

            used_team_ids = get_used_team_ids(current_user.id, week)

            if team_id in used_team_ids:
                phase_name = "playoff rounds" if is_week_playoff(week) else "previous weeks"
                flash(f'You have already used this team in {phase_name}.', 'error')
                return redirect(url_for('main.make_pick', week_number=week_number))

            utc_now = get_utc_time()
            if existing_pick:
                existing_pick.team_id = team_id
                existing_pick.created_at = utc_now
                flash('Pick updated successfully!', 'success')
            else:
                new_pick = Pick(
                    user_id=current_user.id,
                    week_id=week.id,
                    team_id=team_id,
                    created_at=utc_now,
                )
                db.session.add(new_pick)
                flash('Pick submitted successfully!', 'success')

            current_user.calculate_cumulative_spread()
            db.session.commit()

            return redirect(url_for('main.index'))

    # GET: build eligible teams
    games = Game.query.filter_by(week_id=week.id).all()
    for game in games:
        game._aware_time = make_aware(game.game_time)

    used_team_ids = get_used_team_ids(current_user.id, week)

    eligible_teams = []
    teams_added = set()

    for game in games:
        if game.home_team and game.home_team.id not in used_team_ids and game.home_team.id not in teams_added:
            if is_week_playoff(week) and game.home_team.name in cfp_eliminated_names:
                continue
            if game.home_team_spread >= -16:
                can_pick = not safe_is_after(current_time, game._aware_time)
                if can_pick:
                    eligible_teams.append(game.home_team)
                    teams_added.add(game.home_team.id)

        if game.away_team and game.away_team.id not in used_team_ids and game.away_team.id not in teams_added:
            if is_week_playoff(week) and game.away_team.name in cfp_eliminated_names:
                continue
            away_spread = -game.home_team_spread
            if away_spread >= -16:
                can_pick = not safe_is_after(current_time, game._aware_time)
                if can_pick:
                    eligible_teams.append(game.away_team)
                    teams_added.add(game.away_team.id)

    # Build team→spread lookup for the dropdown display
    team_spreads = {}
    for game in games:
        if game.home_team_id:
            team_spreads[game.home_team_id] = game.home_team_spread
        if game.away_team_id:
            team_spreads[game.away_team_id] = -game.home_team_spread

    return render_template(
        'pick.html',
        week=week,
        games=games,
        eligible_teams=eligible_teams,
        existing_pick=existing_pick,
        format_deadline=format_deadline,
        current_time=current_time,
        pick_locked=pick_locked,
        team_spreads=team_spreads,
    )


@main_bp.route('/my-picks')
@login_required
def my_picks():
    current_week = Week.query.filter_by(is_active=True).first()
    in_cfp = current_week and is_week_playoff(current_week)

    user_picks = (
        Pick.query.filter_by(user_id=current_user.id)
        .join(Week)
        .order_by(Week.week_number)
        .all()
    )

    for pick in user_picks:
        pick.week_display = {
            'display_name': get_week_display_name(pick.week),
            'short_label': get_week_short_label(pick.week),
            'badge_type': 'playoff' if is_week_playoff(pick.week) else (
                'conference' if pick.week.week_number == 15 else None
            ),
        }

        game = get_game_for_team(pick.week_id, pick.team_id)
        if game:
            pick.spread_data = {'team_spread': game.get_spread_for_team(pick.team_id)}
        else:
            pick.spread_data = None

    all_teams = Team.query.order_by(Team.name).all()

    if in_cfp:
        relevant_picks = [p for p in user_picks if is_week_playoff(p.week)]
        phase_description = "CFP Phase"
    else:
        relevant_picks = [p for p in user_picks if not is_week_playoff(p.week)]
        phase_description = "Regular Season"

    used_team_ids = [pick.team_id for pick in relevant_picks]

    used_teams = []
    available_teams = []
    teams_by_conference = {}

    cfp_eliminated_teams = []
    cfp_teams_on_bye = []

    if in_cfp:
        eliminated_names = get_cfp_eliminated_teams()
        teams_playing_this_week = get_cfp_teams_in_week(current_week)
        playoff_team_names = set(get_playoff_teams())

        for team in all_teams:
            if team.name not in playoff_team_names:
                continue
            if team.id in used_team_ids:
                for pick in relevant_picks:
                    if pick.team_id == team.id:
                        used_teams.append({
                            'team': team,
                            'week': pick.week.week_number,
                            'week_display': pick.week_display['display_name'],
                            'is_correct': pick.is_correct,
                        })
                        break
            elif team.name in eliminated_names:
                cfp_eliminated_teams.append(team)
            elif team.name not in teams_playing_this_week:
                cfp_teams_on_bye.append(team)
            else:
                available_teams.append(team)
    else:
        playoff_team_names = get_playoff_teams()
        for team in all_teams:
            if team.id in used_team_ids:
                for pick in relevant_picks:
                    if pick.team_id == team.id:
                        used_teams.append({
                            'team': team,
                            'week': pick.week.week_number,
                            'week_display': pick.week_display['display_name'],
                            'is_correct': pick.is_correct,
                        })
                        break
            else:
                available_teams.append(team)
                conference = TEAM_CONFERENCES.get(team.name, 'Unknown')
                if conference not in teams_by_conference:
                    teams_by_conference[conference] = []
                teams_by_conference[conference].append(team)

    all_conferences = set()
    conferences_with_teams = 0
    conference_status = {}
    conference_warnings = []

    if not in_cfp:
        for conf in TEAM_CONFERENCES.values():
            if conf != 'Independent':
                all_conferences.add(conf)

        for conf in sorted(all_conferences):
            team_count = len(teams_by_conference.get(conf, []))
            conference_status[conf] = {'count': team_count}
            if team_count > 0:
                conferences_with_teams += 1
            if conf != 'Independent':
                if team_count == 1:
                    team_name = teams_by_conference[conf][0].name
                    conference_warnings.append(f"Only {team_name} remaining for {conf} championship")
                elif team_count == 0:
                    conference_warnings.append(f"No teams available for {conf} championship")

    total_picks = len(user_picks)
    correct_picks = sum(1 for p in user_picks if p.is_correct is True)
    incorrect_picks = sum(1 for p in user_picks if p.is_correct is False)
    pending_picks = sum(1 for p in user_picks if p.is_correct is None)
    total_conferences = len(all_conferences)

    current_week_display = None
    if current_week:
        current_week_display = {
            'display_name': get_week_display_name(current_week),
            'short_label': get_week_short_label(current_week),
            'badge_type': 'playoff' if is_week_playoff(current_week) else (
                'conference' if current_week.week_number == 15 else None
            ),
            'progress_text': get_week_display_name(current_week),
        }

    return render_template(
        'my_picks.html',
        user_picks=user_picks,
        used_teams=used_teams,
        available_teams=available_teams,
        teams_by_conference=teams_by_conference,
        conference_status=conference_status,
        conference_warnings=conference_warnings,
        conferences_with_teams=conferences_with_teams,
        total_conferences=total_conferences,
        current_week=current_week,
        current_week_display=current_week_display,
        in_cfp=in_cfp,
        phase_description=phase_description,
        total_picks=total_picks,
        correct_picks=correct_picks,
        incorrect_picks=incorrect_picks,
        pending_picks=pending_picks,
        cfp_eliminated_teams=cfp_eliminated_teams,
        cfp_teams_on_bye=cfp_teams_on_bye,
    )


@main_bp.route('/weekly_results')
@main_bp.route('/results/week/<int:week_number>')
def weekly_results(week_number=None):
    current_time = get_current_time()

    all_weeks = Week.query.order_by(Week.week_number).all()
    viewable_weeks = []
    for w in all_weeks:
        deadline = make_aware(w.deadline)
        if deadline_has_passed(deadline):
            viewable_weeks.append(w)

    if week_number is None:
        if viewable_weeks:
            week_number = viewable_weeks[-1].week_number
        else:
            flash('No weekly results available yet. Check back after the first week deadline.', 'info')
            return redirect(url_for('main.index'))

    week = Week.query.filter_by(week_number=week_number).first_or_404()
    deadline = make_aware(week.deadline)

    if current_time <= deadline:
        flash(
            f'Week {week_number} results will be available after the deadline: '
            f'{week.deadline.strftime("%B %d at %I:%M %p")}',
            'warning',
        )
        return redirect(url_for('main.index'))

    picks = (
        Pick.query.filter_by(week_id=week.id)
        .join(User)
        .order_by(func.lower(User.username))
        .all()
    )
    for pick in picks:
        pick._pool_created_at = to_pool_time(pick.created_at)
        pick.is_autopick = safe_is_after(pick._pool_created_at, week.deadline)

    games = Game.query.filter_by(week_id=week.id).all()
    game_results = {}
    for game in games:
        if game.home_team:
            game_results[game.home_team_id] = {
                'opponent': game.get_away_team_display(),
                'won': game.home_team_won if game.home_team_won is not None else None,
                'was_home': True,
                'spread': game.home_team_spread,
                'home_score': game.home_score,
                'away_score': game.away_score,
            }
        if game.away_team:
            game_results[game.away_team_id] = {
                'opponent': game.get_home_team_display(),
                'won': not game.home_team_won if game.home_team_won is not None else None,
                'was_home': False,
                'spread': -game.home_team_spread,
                'home_score': game.home_score,
                'away_score': game.away_score,
            }

    all_users = User.query.order_by(func.lower(User.username)).all()
    users_who_picked = [pick.user_id for pick in picks]
    users_no_pick = [user for user in all_users if user.id not in users_who_picked]

    correct_picks_list = [p for p in picks if p.is_correct is True]
    incorrect_picks_list = [p for p in picks if p.is_correct is False]
    pending_picks_list = [p for p in picks if p.is_correct is None]

    # Bulk-load all picks up to the current week to avoid N+1 queries
    from collections import defaultdict
    all_past_picks = (
        Pick.query.join(Week)
        .filter(Week.week_number <= week.week_number)
        .order_by(Week.week_number)
        .all()
    )
    picks_by_user = defaultdict(list)
    for p in all_past_picks:
        picks_by_user[p.user_id].append(p)

    user_statuses = {}
    for user in all_users:
        lives = 2
        eliminated_week = None
        for past_pick in picks_by_user.get(user.id, []):
            if past_pick.is_correct is False:
                lives -= 1
                if lives <= 0:
                    eliminated_week = past_pick.week.week_number
                    lives = 0
                    break
        user_statuses[user.id] = {
            'lives': lives,
            'is_eliminated': lives == 0,
            'eliminated_week': eliminated_week,
        }

    for pick in picks:
        status = user_statuses.get(pick.user_id, {'lives': 2, 'is_eliminated': False})
        pick.lives_after = status['lives']
        pick.was_eliminated = status['is_eliminated']

    for user in users_no_pick:
        status = user_statuses.get(user.id, {'lives': 2, 'is_eliminated': False})
        user.lives_after = status['lives']
        user.was_eliminated = status['is_eliminated']

    eliminated_this_week = [
        user for user in all_users
        if user_statuses[user.id]['eliminated_week'] == week.week_number
    ]

    return render_template(
        'weekly_results.html',
        week=week,
        picks=picks,
        viewable_weeks=viewable_weeks,
        correct_picks=correct_picks_list,
        incorrect_picks=incorrect_picks_list,
        pending_picks=pending_picks_list,
        game_results=game_results,
        users_no_pick=users_no_pick,
        eliminated_this_week=eliminated_this_week,
        format_deadline=format_deadline,
        timezone=POOL_TZ_NAME,
    )
