"""
CF Survivor Pool - Admin Routes
=================================
All admin-only routes: dashboard, week management, game management, results, users, payments.
"""

import logging
from datetime import datetime
from functools import wraps

import pytz
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import User, Team, Week, Game, Pick
from timezone_utils import get_current_time, format_deadline, make_aware, POOL_TZ_NAME
from services.game_logic import process_week_results, process_autopicks

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def dashboard():
    weeks = Week.query.order_by(Week.week_number).all()
    total_users = User.query.count()
    active_users = User.query.filter_by(is_eliminated=False).count()
    current_time = get_current_time()

    for week in weeks:
        week.deadline = make_aware(week.deadline)

    return render_template(
        'admin/dashboard.html',
        weeks=weeks,
        total_users=total_users,
        active_users=active_users,
        current_time=current_time,
        timezone=POOL_TZ_NAME,
        format_deadline=format_deadline,
    )


@admin_bp.route('/week/new', methods=['GET', 'POST'])
@admin_required
def create_week():
    if request.method == 'POST':
        chicago_tz = pytz.timezone('America/Chicago')
        week_number = int(request.form.get('week_number'))

        start_date_naive = datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M')
        deadline_naive = datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M')

        start_date = chicago_tz.localize(start_date_naive)
        deadline = chicago_tz.localize(deadline_naive)

        existing = Week.query.filter_by(week_number=week_number).first()
        if existing:
            flash(f'Week {week_number} already exists!', 'error')
            return redirect(url_for('admin.create_week'))

        is_playoff = request.form.get('is_playoff_week') == 'on'
        round_name = request.form.get('round_name', '').strip() or None

        new_week = Week(
            week_number=week_number,
            start_date=start_date,
            deadline=deadline,
            is_active=False,
            is_playoff_week=is_playoff,
            round_name=round_name,
        )
        db.session.add(new_week)
        db.session.commit()

        display_name = round_name if round_name else f"Week {week_number}"
        flash(f'{display_name} created successfully!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/create_week.html', timezone='America/Chicago')


@admin_bp.route('/week/<int:week_id>/activate', methods=['POST'])
@admin_required
def activate_week(week_id):
    Week.query.update({'is_active': False})
    week = Week.query.get_or_404(week_id)
    week.is_active = True
    db.session.commit()
    flash(f'Week {week.week_number} is now active!', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/week/<int:week_id>/games', methods=['GET', 'POST'])
@admin_required
def manage_games(week_id):
    week = Week.query.get_or_404(week_id)

    if request.method == 'POST':
        home_team_id = int(request.form.get('home_team_id'))
        away_team_id = int(request.form.get('away_team_id'))
        home_spread = float(request.form.get('home_spread'))
        game_time = datetime.strptime(request.form.get('game_time'), '%Y-%m-%dT%H:%M')

        if home_team_id == away_team_id:
            flash('Home team and away team cannot be the same.', 'error')
            return redirect(url_for('admin.manage_games', week_id=week_id))

        game = Game(
            week_id=week_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_spread=home_spread,
            game_time=game_time,
        )
        db.session.add(game)
        db.session.commit()

        flash('Game added successfully!', 'success')
        return redirect(url_for('admin.manage_games', week_id=week_id))

    teams = Team.query.order_by(Team.name).all()
    games = Game.query.filter_by(week_id=week_id).all()

    return render_template('admin/manage_games.html', week=week, teams=teams, games=games)


@admin_bp.route('/game/<int:game_id>/delete', methods=['POST'])
@admin_required
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)
    week_id = game.week_id
    db.session.delete(game)
    db.session.commit()
    flash('Game deleted.', 'success')
    return redirect(url_for('admin.manage_games', week_id=week_id))


@admin_bp.route('/week/<int:week_id>/results', methods=['GET', 'POST'])
@admin_required
def mark_results(week_id):
    week = Week.query.get_or_404(week_id)
    games = Game.query.filter_by(week_id=week_id).all()

    if request.method == 'POST':
        missing = []
        for game in games:
            result = request.form.get(f'game_{game.id}')
            if not result:
                home = game.get_home_team_display()
                away = game.get_away_team_display()
                missing.append(f'{away} @ {home}')
            else:
                game.home_team_won = (result == 'home')

        if missing:
            flash(f'Missing results for: {", ".join(missing)}', 'error')
            return render_template('admin/mark_results.html', week=week, games=games)

        week.is_complete = True
        db.session.commit()

        process_week_results(week_id)

        flash(f'Results for Week {week.week_number} have been recorded!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/mark_results.html', week=week, games=games)


@admin_bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(func.lower(User.username)).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')

    if new_password:
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password reset for {user.username}.', 'success')
    else:
        flash('No password provided', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/process-autopicks/<int:week_id>')
@admin_required
def admin_process_autopicks(week_id):
    result = process_autopicks(week_id)

    if result["processed"]:
        if result["autopicks"] > 0:
            flash(f'Auto-picks processed: {result["autopicks"]} picks made', 'success')
            for detail in result["details"]:
                flash(f'  {detail["user"]} -> {detail["team"]} ({detail["description"]})', 'info')
        else:
            flash('No auto-picks needed - all users have picks', 'info')

        if result.get("failed", 0) > 0:
            for failure in result["failures"]:
                flash(f'  {failure["user"]}: {failure["reason"]}', 'warning')
    else:
        flash(f'Auto-picks not processed: {result.get("reason", "Unknown reason")}', 'warning')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/payments')
@admin_required
def payments():
    from flask import current_app
    users_list = User.query.order_by(func.lower(User.username)).all()
    entry_fee = current_app.config.get('ENTRY_FEE', 25)

    paid_count = sum(1 for u in users_list if u.has_paid)
    unpaid_count = len(users_list) - paid_count
    total_collected = paid_count * entry_fee

    return render_template(
        'admin/payments.html',
        users=users_list,
        paid_count=paid_count,
        unpaid_count=unpaid_count,
        total_users=len(users_list),
        total_collected=total_collected,
        entry_fee=entry_fee,
    )


@admin_bp.route('/update-payment/<int:user_id>', methods=['POST'])
@admin_required
def update_payment(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    has_paid = data.get('has_paid', False)
    user.has_paid = has_paid
    db.session.commit()
    return jsonify({'success': True, 'has_paid': has_paid})
