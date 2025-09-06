from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
from timezone_utils import (
    get_current_time, get_utc_time, to_pool_time, to_utc,
    deadline_has_passed, format_deadline, make_aware,
    parse_form_datetime, POOL_TZ, POOL_TZ_NAME, UTC_TZ
)
from config import DevelopmentConfig, ProductionConfig
from extensions import db
from datetime_utils import is_past_deadline, get_chicago_time, make_chicago_aware, format_chicago_time
import os
import pytz

app = Flask(__name__)

# Determine environment
if os.getenv('ENVIRONMENT') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Initialize Flask app testing out changes
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Load environment variables
load_dotenv()

db.init_app(app)

# Import our models
from models import User, Team, Week, Game, Pick

# Make timezone functions available in all templates
@app.context_processor
def inject_timezone_functions():
    return {
        'format_deadline': format_deadline,
        'to_pool_time': to_pool_time,
        'get_current_time': get_current_time,
        'timezone': POOL_TZ_NAME
    }

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    """Tell Flask-Login how to find a user"""
    return User.query.get(int(user_id))

def admin_required(f):
    """Decorator to require admin access for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        # Check if user is admin
        if current_user.username not in ['admin', 'B1G_Brad']:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Home page - shows standings and current week info"""
    # Check and process any needed auto-picks
    check_and_process_autopicks()
    
    # Get current week
    current_week = Week.query.filter_by(is_active=True).first()
    
    # Get the current user's pick for this week (if they're logged in)
    user_pick = None
    user_pick_spread = None
    if current_week and current_user.is_authenticated:
        user_pick = Pick.query.filter_by(
            user_id=current_user.id,
            week_id=current_week.id
        ).first()
        if user_pick:
            game = Game.query.filter_by(week_id=current_week.id).filter(
                db.or_(Game.home_team_id == user_pick.team_id,
                       Game.away_team_id == user_pick.team_id)
            ).first()
            if game:
                if user_pick.team_id == game.home_team_id:
                    user_pick_spread = game.home_team_spread
                else:
                    user_pick_spread = -game.home_team_spread
    
    # Get all picks for current week if deadline has passed
    week_picks = {}
    show_picks = False
    if current_week:
        # Check if deadline has passed
        current_week.deadline = make_aware(current_week.deadline)
        show_picks = deadline_has_passed(current_week.deadline)
        
        if show_picks:
            # Get all picks for this week
            all_picks = Pick.query.filter_by(week_id=current_week.id).all()
            for pick in all_picks:
                game = Game.query.filter_by(week_id=current_week.id).filter(
                    db.or_(Game.home_team_id == pick.team_id,
                           Game.away_team_id == pick.team_id)
                ).first()
                if game:
                    if pick.team_id == game.home_team_id:
                        spread = game.home_team_spread
                    else:
                        spread = -game.home_team_spread
                    week_picks[pick.user_id] = f"{pick.team.name} ({spread:+.1f})"
                else:
                    week_picks[pick.user_id] = pick.team.name
    
    # Recalculate spreads for all users (only includes past deadlines)
    all_users = User.query.all()
    for user in all_users:
        user.calculate_cumulative_spread()
    db.session.commit()
    
    # Get standings with CORRECTED sorting
    # Sort by: 1) Not eliminated, 2) Lives remaining (desc), 3) Cumulative spread (ASC - smallest/most negative is best)
    users = User.query.filter_by(is_eliminated=False).order_by(
        User.lives_remaining.desc(),
        User.cumulative_spread.asc()  # Changed from desc to asc
    ).all()
    
    eliminated_users = User.query.filter_by(is_eliminated=True).all()
    
    return render_template('index.html', 
                         current_week=current_week,
                         user_pick=user_pick,
                         user_pick_spread=user_pick_spread,
                         users=users,
                         eliminated_users=eliminated_users,
                         week_picks=week_picks,  # Add this
                         show_picks=show_picks,  # Add this
                         format_deadline=format_deadline,
                         timezone=POOL_TZ_NAME)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username already exists
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash('That username already exists.', 'error')
            return redirect(url_for('register'))
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('An account already exists for that email.', 'error')
            return redirect(url_for('register'))
        
        # Create new user with hashed password
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        # Check password
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow users to change their password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Verify current password is correct
        if not check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('change_password'))
        
        # Check new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('change_password'))
        
        # Check new password is different from current
        if current_password == new_password:
            flash('New password must be different from current password.', 'error')
            return redirect(url_for('change_password'))
        
        # Check password meets minimum requirements
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('change_password'))
        
        # Update password
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('change_password.html')

@app.route('/my-picks')
@login_required
def my_picks():
    """Show user's pick history and available teams"""
    # Get all user's picks with week and team information
    user_picks = Pick.query.filter_by(user_id=current_user.id).join(Week).order_by(Week.week_number).all()
    
    # Add spread data to each pick
    for pick in user_picks:
        game = Game.query.filter_by(week_id=pick.week_id).filter(
            db.or_(Game.home_team_id == pick.team_id, 
                   Game.away_team_id == pick.team_id)
        ).first()
        
        if game:
            # Determine the spread for the picked team
            if pick.team_id == game.home_team_id:
                team_spread = game.home_team_spread
            else:  # Away team
                team_spread = -game.home_team_spread
            
            # Attach spread data to the pick object
            pick.spread_data = {'team_spread': team_spread}
        else:
            pick.spread_data = None
    
    # Get all teams
    all_teams = Team.query.order_by(Team.name).all()
    
    # Get IDs of teams already used
    used_team_ids = [pick.team_id for pick in user_picks]
    
    # Separate teams into used and available
    used_teams = []
    available_teams = []
    
    for team in all_teams:
        if team.id in used_team_ids:
            # Find which week this team was used
            for pick in user_picks:
                if pick.team_id == team.id:
                    used_teams.append({
                        'team': team,
                        'week': pick.week.week_number,
                        'is_correct': pick.is_correct
                    })
                    break
        else:
            available_teams.append(team)
    
    # Get current week for context
    current_week = Week.query.filter_by(is_active=True).first()
    
    # Calculate some statistics
    total_picks = len(user_picks)
    correct_picks = sum(1 for pick in user_picks if pick.is_correct == True)
    incorrect_picks = sum(1 for pick in user_picks if pick.is_correct == False)
    pending_picks = sum(1 for pick in user_picks if pick.is_correct is None)
    
    return render_template('my_picks.html',
                         user_picks=user_picks,
                         used_teams=used_teams,
                         available_teams=available_teams,
                         current_week=current_week,
                         total_picks=total_picks,
                         correct_picks=correct_picks,
                         incorrect_picks=incorrect_picks,
                         pending_picks=pending_picks)

@app.route('/pick/<int:week_number>', methods=['GET', 'POST'])
@login_required
def make_pick(week_number):
    """Page for making picks for a specific week"""

    
    chicago_tz = pytz.timezone('America/Chicago')
    current_time = datetime.now(chicago_tz)
    
    # Check if user is eliminated
    if current_user.is_eliminated:
        flash('Sorry, you have been eliminated from the pool.', 'error')
        return redirect(url_for('index'))
    
    # Get the week
    week = Week.query.filter_by(week_number=week_number).first_or_404()
    
    # Check week deadline
    deadline = week.deadline
    if deadline.tzinfo is None:
        deadline = chicago_tz.localize(deadline)
    
    if current_time > deadline:
        flash('The deadline for this week has passed.', 'error')
        return redirect(url_for('index'))
    
    # Get user's existing pick for this week
    existing_pick = Pick.query.filter_by(
        user_id=current_user.id,
        week_id=week.id
    ).first()

    # Determine if existing pick's game has started
    pick_locked = False
    if existing_pick:
        existing_game = Game.query.filter_by(week_id=week.id).filter(
            db.or_(Game.home_team_id == existing_pick.team_id,
                   Game.away_team_id == existing_pick.team_id)
        ).first()

        if existing_game and existing_game.game_time:
            game_time = existing_game.game_time
            if game_time.tzinfo is None:
                game_time = chicago_tz.localize(game_time)

            if current_time > game_time:
                pick_locked = True

    # Handle POST request (submitting/updating pick)
    if request.method == 'POST':
        if pick_locked:
            flash('Your pick is locked - that game has already started.', 'error')
        else:
            team_id = int(request.form.get('team_id'))

            # Check if the selected team's game has already started
            new_team_game = Game.query.filter_by(week_id=week.id).filter(
                db.or_(Game.home_team_id == team_id,
                       Game.away_team_id == team_id)
            ).first()

            if new_team_game and new_team_game.game_time:
                game_time = new_team_game.game_time
                if game_time.tzinfo is None:
                    game_time = chicago_tz.localize(game_time)

                if current_time > game_time:
                    flash('Cannot pick this team - their game has already started.', 'error')
                    return redirect(url_for('make_pick', week_number=week_number))

            # Get teams user has already used in previous weeks
            used_teams = db.session.query(Pick.team_id).filter(
                Pick.user_id == current_user.id,
                Pick.week_id != week.id
            ).all()
            used_team_ids = [t[0] for t in used_teams]

            # Verify team hasn't been used before
            if team_id in used_team_ids:
                flash('You have already used this team in a previous week.', 'error')
                return redirect(url_for('make_pick', week_number=week_number))

            # Save or update pick
            if existing_pick:
                existing_pick.team_id = team_id
                existing_pick.created_at = current_time
                flash('Pick updated successfully!', 'success')
            else:
                new_pick = Pick(
                    user_id=current_user.id,
                    week_id=week.id,
                    team_id=team_id,
                    created_at=current_time
                )
                db.session.add(new_pick)
                flash('Pick submitted successfully!', 'success')

            # Recalculate cumulative spread
            current_user.calculate_cumulative_spread()
            db.session.commit()

            return redirect(url_for('index'))
    
    # GET request - build list of eligible teams
    
    # Get all games for this week
    games = Game.query.filter_by(week_id=week.id).all()

    for game in games:
        if game.game_time:
            if game.game_time.tzinfo is None:
                game.game_time = chicago_tz.localize(game.game_time)
    
    # Get teams user has already used in previous weeks
    used_teams = db.session.query(Pick.team_id).filter(
        Pick.user_id == current_user.id,
        Pick.week_id != week.id
    ).all()
    used_team_ids = [t[0] for t in used_teams]
    
    # Build eligible teams list
    eligible_teams = []
    teams_added = set()  # Track teams to avoid duplicates
    
    for game in games:
        # Check home team
        if game.home_team and game.home_team.id not in used_team_ids and game.home_team.id not in teams_added:
            # Check spread eligibility (not favored by more than 16)
            if game.home_team_spread >= -16:
                # Check if game has started
                can_pick = True
                if game.game_time:
                    game_time = game.game_time
                    if game_time.tzinfo is None:
                        game_time = chicago_tz.localize(game_time)
                    if current_time > game_time:
                        can_pick = False  # Game has started
                
                if can_pick:
                    eligible_teams.append(game.home_team)
                    teams_added.add(game.home_team.id)
        
        # Check away team
        if game.away_team and game.away_team.id not in used_team_ids and game.away_team.id not in teams_added:
            # Check spread eligibility (not favored by more than 16)
            away_spread = -game.home_team_spread
            if away_spread >= -16:
                # Check if game has started
                can_pick = True
                if game.game_time:
                    game_time = game.game_time
                    if game_time.tzinfo is None:
                        game_time = chicago_tz.localize(game_time)
                    if current_time > game_time:
                        can_pick = False  # Game has started
                
                if can_pick:
                    eligible_teams.append(game.away_team)
                    teams_added.add(game.away_team.id)
    
    return render_template('pick.html', 
                         week=week,
                         games=games,
                         eligible_teams=eligible_teams,
                         existing_pick=existing_pick,
                         format_deadline=format_deadline,
                         current_time=current_time,
                         pick_locked=pick_locked)

@app.route('/weekly_results')
@app.route('/results/week/<int:week_number>')
def weekly_results(week_number=None):
    """Show weekly results and picks for all users"""
    current_time = get_current_time()
    
    # Get all weeks
    all_weeks = Week.query.order_by(Week.week_number).all()
    
    # Make deadlines timezone-aware and filter viewable weeks
    viewable_weeks = []
    for w in all_weeks:
        w.deadline = make_aware(w.deadline)
        if deadline_has_passed(w.deadline):
            viewable_weeks.append(w)
    
    # If no specific week requested, show the most recent viewable week
    if week_number is None:
        if viewable_weeks:
            week_number = viewable_weeks[-1].week_number
        else:
            flash('No weekly results available yet. Check back after the first week deadline.', 'info')
            return redirect(url_for('index'))
    
    # Get the specific week
    week = Week.query.filter_by(week_number=week_number).first_or_404()
    # Ensure the week's deadline is timezone-aware
    week.deadline = make_aware(week.deadline)

    # Check if deadline has passed
    if current_time <= week.deadline:
        flash(f'Week {week_number} results will be available after the deadline: {week.deadline.strftime("%B %d at %I:%M %p")}', 'warning')
        return redirect(url_for('index'))

    # Get all picks for this week with user information
    picks = Pick.query.filter_by(week_id=week.id).join(User).order_by(User.username).all()
    # Convert pick timestamps to pool timezone for accurate comparisons
    for pick in picks:
        pick.created_at = to_pool_time(pick.created_at)
    
    # Get all games for this week to show results
    games = Game.query.filter_by(week_id=week.id).all()
    
    # Build a dictionary of game results for easy lookup
    game_results = {}
    for game in games:
        if game.home_team:
            game_results[game.home_team_id] = {
                'opponent': game.get_away_team_display(),
                'won': game.home_team_won if game.home_team_won is not None else None,
                'was_home': True,
                'spread': game.home_team_spread
            }
        if game.away_team:
            game_results[game.away_team_id] = {
                'opponent': game.get_home_team_display(),
                'won': not game.home_team_won if game.home_team_won is not None else None,
                'was_home': False,
                'spread': -game.home_team_spread
            }
    
    # Get users who didn't pick (if any)
    all_users = User.query.filter_by(is_eliminated=False).all()
    users_who_picked = [pick.user_id for pick in picks]
    users_no_pick = [user for user in all_users if user.id not in users_who_picked]
    
    # Separate picks by result
    correct_picks = [p for p in picks if p.is_correct == True]
    incorrect_picks = [p for p in picks if p.is_correct == False]
    pending_picks = [p for p in picks if p.is_correct is None]
    
    # Find who was eliminated this week
    eliminated_this_week = []
    for pick in incorrect_picks:
        if pick.user.lives_remaining == 0 and pick.user.is_eliminated:
            eliminated_this_week.append(pick.user)

    return render_template('weekly_results.html',
                         week=week,
                         picks=picks,
                         viewable_weeks=viewable_weeks,
                         correct_picks=correct_picks,
                         incorrect_picks=incorrect_picks,
                         pending_picks=pending_picks,
                         game_results=game_results,
                         users_no_pick=users_no_pick,
                         eliminated_this_week=eliminated_this_week,
                         format_deadline=format_deadline,
                         timezone=POOL_TZ_NAME)

@app.route('/init-db')
def init_database():
    """Initialize database - run this once to create tables"""
    db.create_all()
    flash('Database initialized!', 'success')
    return redirect(url_for('index'))

# Admin Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard - main admin page"""
    weeks = Week.query.order_by(Week.week_number).all()
    total_users = User.query.count()
    active_users = User.query.filter_by(is_eliminated=False).count()
    current_time = get_current_time()  # This is now timezone-aware
    
    # Make all week deadlines aware for comparison
    for week in weeks:
        week.deadline = make_aware(week.deadline)
    
    return render_template('admin/dashboard.html', 
                         weeks=weeks,
                         total_users=total_users,
                         active_users=active_users,
                         current_time=current_time,
                         timezone=POOL_TZ_NAME,
                         format_deadline=format_deadline)

@app.route('/admin/week/new', methods=['GET', 'POST'])
@admin_required
def create_week():
    """Create a new week"""
    if request.method == 'POST':
        import pytz
        from datetime import datetime
        
        chicago_tz = pytz.timezone('America/Chicago')
        week_number = int(request.form.get('week_number'))
        
        # Parse the dates as naive (no timezone)
        start_date_str = request.form.get('start_date')
        deadline_str = request.form.get('deadline')
        
        start_date_naive = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        deadline_naive = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        
        # CRITICAL: Localize as Chicago time (this interprets the input AS Chicago time)
        start_date = chicago_tz.localize(start_date_naive)
        deadline = chicago_tz.localize(deadline_naive)
        
        # Check if week already exists
        existing = Week.query.filter_by(week_number=week_number).first()
        if existing:
            flash(f'Week {week_number} already exists!', 'error')
            return redirect(url_for('create_week'))
        
        # Create new week - store with timezone info
        new_week = Week(
            week_number=week_number,
            start_date=start_date,
            deadline=deadline,
            is_active=False
        )
        db.session.add(new_week)
        db.session.commit()
        
        flash(f'Week {week_number} created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/create_week.html', timezone='America/Chicago')

@app.route('/admin/week/<int:week_id>/activate')
@admin_required
def activate_week(week_id):
    """Set a week as the current active week"""
    # Deactivate all weeks first
    Week.query.update({'is_active': False})
    
    # Activate the selected week
    week = Week.query.get_or_404(week_id)
    week.is_active = True
    db.session.commit()
    
    flash(f'Week {week.week_number} is now active!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/week/<int:week_id>/games', methods=['GET', 'POST'])
@admin_required
def manage_games(week_id):
    """Add/edit games for a specific week"""
    week = Week.query.get_or_404(week_id)
    
    if request.method == 'POST':
        # Get form data
        home_team_id = int(request.form.get('home_team_id'))
        away_team_id = int(request.form.get('away_team_id'))
        home_spread = float(request.form.get('home_spread'))
        game_time = datetime.strptime(request.form.get('game_time'), '%Y-%m-%dT%H:%M')
        
        # Create new game
        game = Game(
            week_id=week_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_spread=home_spread,
            game_time=game_time
        )
        db.session.add(game)
        db.session.commit()
        
        flash('Game added successfully!', 'success')
        return redirect(url_for('manage_games', week_id=week_id))
    
    # Get all teams for the dropdown
    teams = Team.query.order_by(Team.name).all()
    games = Game.query.filter_by(week_id=week_id).all()
    
    return render_template('admin/manage_games.html', 
                         week=week, 
                         teams=teams, 
                         games=games)

@app.route('/admin/game/<int:game_id>/delete')
@admin_required
def delete_game(game_id):
    """Delete a game"""
    game = Game.query.get_or_404(game_id)
    week_id = game.week_id
    db.session.delete(game)
    db.session.commit()
    flash('Game deleted.', 'success')
    return redirect(url_for('manage_games', week_id=week_id))

@app.route('/admin/week/<int:week_id>/results', methods=['GET', 'POST'])
@admin_required
def mark_results(week_id):
    """Mark game results for a week"""
    week = Week.query.get_or_404(week_id)
    games = Game.query.filter_by(week_id=week_id).all()
    
    if request.method == 'POST':
        # Process each game's result
        for game in games:
            result = request.form.get(f'game_{game.id}')
            if result:
                game.home_team_won = (result == 'home')
        
        # Mark week as complete
        week.is_complete = True
        db.session.commit()
        
        # Process picks and update lives
        process_week_results(week_id)
        
        flash(f'Results for Week {week.week_number} have been recorded!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/mark_results.html', week=week, games=games)

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin page to manage users"""
    all_users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=all_users)

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """Admin can reset a user's password"""
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    
    if new_password:
        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash(f'Password reset for {user.username}. New password: {new_password}', 'success')
    else:
        flash('No password provided', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/process-autopicks/<int:week_id>')
@admin_required
def admin_process_autopicks(week_id):
    """Manually trigger auto-pick processing for a specific week"""
    result = process_autopicks(week_id)
    
    if result["processed"]:
        if result["autopicks"] > 0:
            flash(f'Auto-picks processed: {result["autopicks"]} picks made', 'success')
            # Show details of what happened
            for detail in result["details"]:
                flash(f'  • {detail["user"]} → {detail["team"]} ({detail["description"]})', 'info')
        else:
            flash('No auto-picks needed - all users have picks', 'info')
        
        if result.get("failed", 0) > 0:
            for failure in result["failures"]:
                flash(f'  ⚠️ {failure["user"]}: {failure["reason"]}', 'warning')
    else:
        flash(f'Auto-picks not processed: {result.get("reason", "Unknown reason")}', 'warning')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/payments')
@admin_required
def admin_payments():
    """Admin page to track payments"""
    # Get all users
    all_users = User.query.order_by(User.username).all()
    
    # Separate active and eliminated
    active_users = [u for u in all_users if not u.is_eliminated]
    eliminated_users = [u for u in all_users if u.is_eliminated]
    
    # Calculate statistics
    paid_count = sum(1 for u in active_users if u.has_paid)
    unpaid_count = len(active_users) - paid_count
    
    # Calculate total collected (assuming $20 entry fee - adjust as needed)
    entry_fee = 25  # Change this to your actual entry fee
    total_collected = paid_count * entry_fee
    
    return render_template('admin/payments.html',
                         active_users=active_users,
                         eliminated_users=eliminated_users,
                         paid_count=paid_count,
                         unpaid_count=unpaid_count,
                         total_active=len(active_users),
                         total_collected=total_collected,
                         entry_fee=entry_fee)

@app.route('/admin/update-payment/<int:user_id>', methods=['POST'])
@admin_required
def admin_update_payment(user_id):
    """AJAX endpoint to update payment status"""
    import json
    
    user = User.query.get_or_404(user_id)
    
    # Get JSON data from request
    data = request.get_json()
    has_paid = data.get('has_paid', False)
    
    # Update payment status
    user.has_paid = has_paid
    db.session.commit()
    
    return json.dumps({'success': True, 'has_paid': has_paid})

# Helper Functions
def process_week_results(week_id):
    """Process pick results and update user lives"""
    week = Week.query.get(week_id)
    picks = Pick.query.filter_by(week_id=week_id).all()
    
    for pick in picks:
        # Find the game with this team
        game = Game.query.filter_by(week_id=week_id).filter(
            db.or_(Game.home_team_id == pick.team_id, 
                   Game.away_team_id == pick.team_id)
        ).first()
        
        if game and game.home_team_won is not None:
            # Determine if pick was correct
            if pick.team_id == game.home_team_id:
                pick.is_correct = game.home_team_won
            else:  # picked away team
                pick.is_correct = not game.home_team_won
            
            # If incorrect, deduct a life
            if not pick.is_correct:
                user = pick.user
                user.lives_remaining -= 1
                if user.lives_remaining <= 0:
                    user.is_eliminated = True
                    user.lives_remaining = 0
        
        # Recalculate cumulative spread for the user
        pick.user.calculate_cumulative_spread()
    
    db.session.commit()

def process_autopicks(week_id):
    """Process auto-picks for users who missed the deadline"""
    week = Week.query.get(week_id)
    week.deadline = make_aware(week.deadline)
    
    if not deadline_has_passed(week.deadline):
        return {"processed": False, "reason": "Deadline not yet passed"}
    
    # Get all active users (not eliminated)
    active_users = User.query.filter_by(is_eliminated=False).all()
    
    # Get users who already picked this week
    existing_picks = Pick.query.filter_by(week_id=week_id).all()
    users_with_picks = [pick.user_id for pick in existing_picks]
    
    # Find users who need auto-picks
    users_needing_autopick = [u for u in active_users if u.id not in users_with_picks]
    
    if not users_needing_autopick:
        return {"processed": True, "autopicks": 0, "reason": "All active users have picks"}
    
    autopicks_made = []
    autopicks_failed = []
    
    # Get all games for this week that haven't started yet
    current_time = get_current_time()
    games = [
        game for game in Game.query.filter_by(week_id=week_id).all()
        if not game.game_time or make_aware(game.game_time) > current_time
    ]
    
    for user in users_needing_autopick:
        # Get teams user has already used in previous weeks
        used_teams = db.session.query(Pick.team_id).filter(
            Pick.user_id == user.id,
            Pick.week_id != week_id
        ).all()
        used_team_ids = [t[0] for t in used_teams]
        
        # Find best available team
        best_team = None
        best_spread = None
        best_favoritism = -999  # How many points they're favored by (positive number)
        
        for game in games:
            # Check home team
            if game.home_team and game.home_team_id not in used_team_ids:
                # Convert spread to favoritism (positive = favored by that many points)
                home_favoritism = -game.home_team_spread
                
                # Check if team is favored and within our limit
                if 0 < home_favoritism <= 16:
                    if home_favoritism > best_favoritism:
                        best_favoritism = home_favoritism
                        best_spread = game.home_team_spread
                        best_team = game.home_team
            
            # Check away team
            if game.away_team and game.away_team_id not in used_team_ids:
                # Away team's favoritism is opposite of home spread
                away_favoritism = game.home_team_spread  # If positive, away team is favored
                
                # Check if team is favored and within our limit
                if 0 < away_favoritism <= 16:
                    if away_favoritism > best_favoritism:
                        best_favoritism = away_favoritism
                        best_spread = -game.home_team_spread  # Away team's actual spread
                        best_team = game.away_team
        
        # If no favored teams available, pick the smallest underdog
        if not best_team:
            smallest_underdog = None
            smallest_underdog_points = 999  # How many points they're underdog by
            
            for game in games:
                # Check home team as underdog
                if game.home_team and game.home_team_id not in used_team_ids:
                    if game.home_team_spread > 0:  # Home team is underdog
                        if game.home_team_spread < smallest_underdog_points:
                            smallest_underdog_points = game.home_team_spread
                            smallest_underdog = game.home_team
                            best_spread = game.home_team_spread
                
                # Check away team as underdog
                if game.away_team and game.away_team_id not in used_team_ids:
                    away_spread = -game.home_team_spread
                    if away_spread > 0:  # Away team is underdog
                        if away_spread < smallest_underdog_points:
                            smallest_underdog_points = away_spread
                            smallest_underdog = game.away_team
                            best_spread = away_spread
            
            best_team = smallest_underdog
        
        # Make the auto-pick if we found an eligible team
        if best_team:
            auto_pick = Pick(
        user_id=user.id,
        week_id=week_id,
        team_id=best_team.id,
        created_at=get_utc_time()  # Store in UTC, aware
    )
            db.session.add(auto_pick)
            
            # Recalculate user's cumulative spread
            user.calculate_cumulative_spread()
            
            # Log the pick with clear information
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
                "description": favoritism_text
            })
            
            print(f"Auto-pick: {user.username} -> {best_team.name} ({favoritism_text})")
        else:
            autopicks_failed.append({
                "user": user.username,
                "reason": "No eligible teams available"
            })
            print(f"Auto-pick failed: {user.username} - No eligible teams")
    
    # Commit all auto-picks
    if autopicks_made:
        db.session.commit()
    
    return {
        "processed": True,
        "autopicks": len(autopicks_made),
        "failed": len(autopicks_failed),
        "details": autopicks_made,
        "failures": autopicks_failed
    }

def check_and_process_autopicks():
    """Check all active weeks and process autopicks if past deadline"""
    weeks = Week.query.filter_by(is_complete=False).all()
    
    results = []
    for week in weeks:
        # Ensure deadline is timezone-aware
        week.deadline = make_aware(week.deadline)
        
        if deadline_has_passed(week.deadline):
            result = process_autopicks(week.id)
            if result["processed"] and result["autopicks"] > 0:
                results.append(f"Week {week.week_number}: {result['autopicks']} auto-picks made")
    
    return results



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True)