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
from db_maintenance import ensure_team_national_title_odds_column
from datetime_utils import is_past_deadline, get_chicago_time, make_chicago_aware, format_chicago_time
from display_utils import (
    get_display_helpers, get_playoff_teams, is_week_playoff,
    get_cfp_eliminated_teams, get_cfp_active_teams, get_cfp_teams_on_bye,
    get_cfp_teams_in_week, get_cfp_available_teams_for_user
)
from sqlalchemy import func
import os
import pytz

app = Flask(__name__)

# Determine environment
if os.getenv('ENVIRONMENT') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Initialize Flask app
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Load environment variables
load_dotenv()

db.init_app(app)

# Ensure schema updates needed by the application are applied
ensure_team_national_title_odds_column(app, db, reporter=app.logger.info)

# Import our models
from models import User, Team, Week, Game, Pick

# Make timezone functions AND display helpers available in all templates
@app.context_processor
def inject_helpers():
    helpers = {
        'format_deadline': format_deadline,
        'to_pool_time': to_pool_time,
        'get_current_time': get_current_time,
        'timezone': POOL_TZ_NAME,
    }
    # Add display helpers from display_utils
    helpers.update(get_display_helpers())
    return helpers

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    """Tell Flask-Login how to find a user"""
    return db.session.get(User, int(user_id))

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
     # Auto-picks are processed via scheduled tasks (see run_autopicks.py)

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
                         week_picks=week_picks,
                         show_picks=show_picks,
                         format_deadline=format_deadline,
                         timezone=POOL_TZ_NAME)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username already exists
        existing_username = User.query.filter(
            func.lower(User.username) == username.casefold()
        ).first()
        if existing_username:
            flash('That username already exists.', 'error')
            return redirect(url_for('register'))
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('An account already exists for that email.', 'error')
            return redirect(url_for('register'))

        # Prevent registration after contest has started
        first_week = Week.query.order_by(Week.week_number).first()
        if first_week and deadline_has_passed(first_week.deadline):
            flash('Registration closed. The pool has already started.', 'error')
            return redirect(url_for('login'))

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
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        
        # Find user (case-insensitive)
        user = User.query.filter(
            func.lower(User.username) == username.casefold()
        ).first()
        
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
    """Show user's pick history and available teams organized by conference"""
    from models import TEAM_CONFERENCES
    
    # Get current week for context
    current_week = Week.query.filter_by(is_active=True).first()
    
    # Check if we're in CFP (week 16+)
    in_cfp = current_week and is_week_playoff(current_week)
    
    # Get all user's picks with week and team information
    user_picks = Pick.query.filter_by(user_id=current_user.id).join(Week).order_by(Week.week_number).all()
    
    # Add spread data and week display info to each pick
    for pick in user_picks:
        # Get week display info using display_utils
        from display_utils import get_week_display_name, get_week_short_label
        pick.week_display = {
            'display_name': get_week_display_name(pick.week),
            'short_label': get_week_short_label(pick.week),
            'badge_type': 'playoff' if is_week_playoff(pick.week) else (
                'conference' if pick.week.week_number == 15 else None
            )
        }
        
        # Get spread data
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
    
    # Determine which picks to consider for "used teams"
    if in_cfp:
        # In CFP, only consider CFP picks (week 16+)
        relevant_picks = [p for p in user_picks if is_week_playoff(p.week)]
        phase_description = "CFP Phase"
    else:
        # Regular season + conf championship, consider weeks 1-15
        relevant_picks = [p for p in user_picks if not is_week_playoff(p.week)]
        phase_description = "Regular Season"
    
    # Get IDs of teams already used in the current phase
    used_team_ids = [pick.team_id for pick in relevant_picks]
    
    # Separate teams into used and available
    used_teams = []
    available_teams = []
    teams_by_conference = {}  # For organizing available teams by conference
    
    # CFP-specific variables
    cfp_eliminated_teams = []
    cfp_teams_on_bye = []
    
    if in_cfp:
        # Get CFP elimination status
        eliminated_names = get_cfp_eliminated_teams()
        teams_playing_this_week = get_cfp_teams_in_week(current_week)
        active_team_names = get_cfp_active_teams()
        playoff_team_names = set(get_playoff_teams())
        
        # Build lists for template
        for team in all_teams:
            if team.name not in playoff_team_names:
                continue  # Skip non-playoff teams
            
            if team.id in used_team_ids:
                # User already picked this team in CFP
                for pick in relevant_picks:
                    if pick.team_id == team.id:
                        used_teams.append({
                            'team': team,
                            'week': pick.week.week_number,
                            'week_display': pick.week_display['display_name'],
                            'is_correct': pick.is_correct
                        })
                        break
            elif team.name in eliminated_names:
                # Team has been eliminated from playoffs
                cfp_eliminated_teams.append(team)
            elif team.name not in teams_playing_this_week:
                # Team is on bye this round
                cfp_teams_on_bye.append(team)
            else:
                # Team is available to pick
                available_teams.append(team)
    else:
        # Regular season logic (unchanged)
        playoff_team_names = get_playoff_teams()
        
        for team in all_teams:
            if team.id in used_team_ids:
                # Find which week this team was used in current phase
                for pick in relevant_picks:
                    if pick.team_id == team.id:
                        used_teams.append({
                            'team': team,
                            'week': pick.week.week_number,
                            'week_display': pick.week_display['display_name'],
                            'is_correct': pick.is_correct
                        })
                        break
            else:
                # Regular season: all unused teams available
                available_teams.append(team)
                
                # Organize by conference (only for regular season)
                conference = TEAM_CONFERENCES.get(team.name, 'Unknown')
                if conference not in teams_by_conference:
                    teams_by_conference[conference] = []
                teams_by_conference[conference].append(team)
    
    # Calculate conference championship coverage (only relevant for regular season)
    all_conferences = set()
    conferences_with_teams = 0
    conference_status = {}
    conference_warnings = []
    
    if not in_cfp:  # Only show conference coverage during regular season
        # Get unique conferences (excluding Independent since no championship game)
        for conf in TEAM_CONFERENCES.values():
            if conf != 'Independent':
                all_conferences.add(conf)
        
        # Check status for each conference
        for conf in sorted(all_conferences):
            team_count = len(teams_by_conference.get(conf, []))
            conference_status[conf] = {'count': team_count}
            
            if team_count > 0:
                conferences_with_teams += 1
                
            # Generate warnings (EXCLUDE Independent from warnings)
            if conf != 'Independent':  # Don't warn about Independent
                if team_count == 1:
                    team_name = teams_by_conference[conf][0].name
                    conference_warnings.append(f"Only {team_name} remaining for {conf} championship")
                elif team_count == 0:
                    conference_warnings.append(f"No teams available for {conf} championship")
    
    # Calculate some statistics
    total_picks = len(user_picks)
    correct_picks = sum(1 for pick in user_picks if pick.is_correct == True)
    incorrect_picks = sum(1 for pick in user_picks if pick.is_correct == False)
    pending_picks = sum(1 for pick in user_picks if pick.is_correct is None)
    
    # Total conferences (excluding Independent)
    total_conferences = len(all_conferences)
    
    # Get week display info for current week
    from display_utils import get_week_display_name, get_week_short_label
    current_week_display = None
    if current_week:
        current_week_display = {
            'display_name': get_week_display_name(current_week),
            'short_label': get_week_short_label(current_week),
            'badge_type': 'playoff' if is_week_playoff(current_week) else (
                'conference' if current_week.week_number == 15 else None
            ),
            'progress_text': get_week_display_name(current_week)
        }
    
    return render_template('my_picks.html',
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
                         cfp_teams_on_bye=cfp_teams_on_bye)

@app.route('/pick/<int:week_number>', methods=['GET', 'POST'])
@login_required
def make_pick(week_number):
    """Page for making picks for a specific week - WITH PLAYOFF LOGIC"""
    
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

    # Get CFP elimination info if playoff week
    cfp_eliminated_names = set()
    if is_week_playoff(week):
        cfp_eliminated_names = get_cfp_eliminated_teams()

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

            # Check if team has been eliminated from CFP
            if is_week_playoff(week):
                team = Team.query.get(team_id)
                if team and team.name in cfp_eliminated_names:
                    flash('Cannot pick this team - they have been eliminated from the playoffs.', 'error')
                    return redirect(url_for('make_pick', week_number=week_number))

            # *** PLAYOFF LOGIC: Determine which picks to check for "used teams" ***
            if is_week_playoff(week):
                # In playoff weeks, only check OTHER PLAYOFF WEEKS
                used_teams = db.session.query(Pick.team_id).join(Week).filter(
                    Pick.user_id == current_user.id,
                    Week.is_playoff_week == True,
                    Pick.week_id != week.id  # Exclude current week
                ).all()
            else:
                # In regular season weeks (including CCW), check ALL NON-PLAYOFF WEEKS
                used_teams = db.session.query(Pick.team_id).join(Week).filter(
                    Pick.user_id == current_user.id,
                    Week.is_playoff_week == False,
                    Pick.week_id != week.id  # Exclude current week
                ).all()
            
            used_team_ids = [t[0] for t in used_teams]

            # Verify team hasn't been used before in the current phase
            if team_id in used_team_ids:
                phase_name = "playoff rounds" if is_week_playoff(week) else "previous weeks"
                flash(f'You have already used this team in {phase_name}.', 'error')
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
    
    # *** PLAYOFF LOGIC: Determine which teams user has already used ***
    if is_week_playoff(week):
        # In playoff weeks, only check OTHER PLAYOFF WEEKS
        used_teams = db.session.query(Pick.team_id).join(Week).filter(
            Pick.user_id == current_user.id,
            Week.is_playoff_week == True,
            Pick.week_id != week.id
        ).all()
    else:
        # In regular season weeks (including CCW), check ALL NON-PLAYOFF WEEKS
        used_teams = db.session.query(Pick.team_id).join(Week).filter(
            Pick.user_id == current_user.id,
            Week.is_playoff_week == False,
            Pick.week_id != week.id
        ).all()
    
    used_team_ids = [t[0] for t in used_teams]
    
    # Build eligible teams list
    eligible_teams = []
    teams_added = set()  # Track teams to avoid duplicates
    
    for game in games:
        # Check home team
        if game.home_team and game.home_team.id not in used_team_ids and game.home_team.id not in teams_added:
            # Check if team has been eliminated from CFP
            if is_week_playoff(week) and game.home_team.name in cfp_eliminated_names:
                continue  # Skip eliminated teams
            
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
            # Check if team has been eliminated from CFP
            if is_week_playoff(week) and game.away_team.name in cfp_eliminated_names:
                continue  # Skip eliminated teams
            
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
    picks = Pick.query.filter_by(week_id=week.id).join(User).order_by(func.lower(User.username)).all()
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
    all_users = User.query.order_by(func.lower(User.username)).all()
    users_who_picked = [pick.user_id for pick in picks]
    users_no_pick = [user for user in all_users if user.id not in users_who_picked]

    # Separate picks by result
    correct_picks = [p for p in picks if p.is_correct == True]
    incorrect_picks = [p for p in picks if p.is_correct == False]
    pending_picks = [p for p in picks if p.is_correct is None]

    # Calculate each user's status after this week
    user_statuses = {}
    for user in all_users:
        lives = 2
        eliminated_week = None
        past_picks = Pick.query.join(Week).filter(
            Pick.user_id == user.id,
            Week.week_number <= week.week_number
        ).order_by(Week.week_number).all()
        for past_pick in past_picks:
            if past_pick.is_correct == False:
                lives -= 1
                if lives <= 0:
                    eliminated_week = past_pick.week.week_number
                    lives = 0
                    break
        user_statuses[user.id] = {
            'lives': lives,
            'is_eliminated': lives == 0,
            'eliminated_week': eliminated_week
        }

    # Attach status info to picks and no-pick users
    for pick in picks:
        status = user_statuses.get(pick.user_id, {'lives': 2, 'is_eliminated': False})
        pick.lives_after = status['lives']
        pick.was_eliminated = status['is_eliminated']

    for user in users_no_pick:
        status = user_statuses.get(user.id, {'lives': 2, 'is_eliminated': False})
        user.lives_after = status['lives']
        user.was_eliminated = status['is_eliminated']

    # Determine who was eliminated this week
    eliminated_this_week = [
        user for user in all_users
        if user_statuses[user.id]['eliminated_week'] == week.week_number
    ]

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
    """Create a new week - WITH PLAYOFF SUPPORT"""
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
        
        # CRITICAL: Localize as Chicago time
        start_date = chicago_tz.localize(start_date_naive)
        deadline = chicago_tz.localize(deadline_naive)
        
        # Check if week already exists
        existing = Week.query.filter_by(week_number=week_number).first()
        if existing:
            flash(f'Week {week_number} already exists!', 'error')
            return redirect(url_for('create_week'))
        
        # Get playoff week settings
        is_playoff = request.form.get('is_playoff_week') == 'on'
        round_name = request.form.get('round_name', '').strip() or None
        
        # Create new week
        new_week = Week(
            week_number=week_number,
            start_date=start_date,
            deadline=deadline,
            is_active=False,
            is_playoff_week=is_playoff,
            round_name=round_name
        )
        db.session.add(new_week)
        db.session.commit()
        
        display_name = round_name if round_name else f"Week {week_number}"
        flash(f'{display_name} created successfully!', 'success')
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
    all_users = User.query.order_by(func.lower(User.username)).all()
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
    users = User.query.order_by(func.lower(User.username)).all()

    # Calculate statistics across the full roster
    paid_count = sum(1 for u in users if u.has_paid)
    unpaid_count = len(users) - paid_count

    # Calculate total collected (assuming $25 entry fee - adjust as needed)
    entry_fee = 25  # Change this to your actual entry fee
    total_collected = paid_count * entry_fee

    return render_template('admin/payments.html',
                         users=users,
                         paid_count=paid_count,
                         unpaid_count=unpaid_count,
                         total_users=len(users),
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
    """Process pick results and update user lives - WITH REVIVAL RULE"""
    week = Week.query.get(week_id)
    picks = Pick.query.filter_by(week_id=week_id).all()

    # Track active users who had 1 life at START of week (for revival rule)
    active_users = User.query.filter_by(is_eliminated=False).all()
    active_user_ids = {user.id for user in active_users}
    users_with_one_life_before = [
        user.id for user in active_users if user.lives_remaining == 1
    ]

    for pick in picks:
        # Find the game with this team that has a recorded result
        game = Game.query.filter_by(week_id=week_id).filter(
            db.or_(Game.home_team_id == pick.team_id,
                   Game.away_team_id == pick.team_id),
            Game.home_team_won != None
        ).first()

        if game:
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
    
    # *** REVIVAL RULE: Check if ALL users with 1 life lost ***
    if users_with_one_life_before and len(users_with_one_life_before) == len(active_user_ids):
        # Get current status of those users
        users_to_check = User.query.filter(User.id.in_(users_with_one_life_before)).all()
        
        # Check if ALL of them are now at 0 lives
        all_eliminated = all(user.lives_remaining == 0 for user in users_to_check)
        
        if all_eliminated:
            # REVIVAL: Give them all back 1 life
            for user in users_to_check:
                user.lives_remaining = 1
                user.is_eliminated = False
            
            db.session.commit()
            
            # Log this event (silent - no user notification)
            app.logger.info(f"REVIVAL RULE ACTIVATED: Week {week.week_number} - {len(users_to_check)} users revived")

def process_autopicks(week_id):
    """Process auto-picks for users who missed the deadline - WITH PLAYOFF SUPPORT AND CFP ELIMINATION"""
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
    
    # Get CFP eliminated teams if this is a playoff week
    cfp_eliminated_names = set()
    if is_week_playoff(week):
        cfp_eliminated_names = get_cfp_eliminated_teams()
    
    for user in users_needing_autopick:
        # *** PLAYOFF LOGIC: Determine which teams user has already used ***
        if is_week_playoff(week):
            # In playoff weeks, only check OTHER PLAYOFF WEEKS
            used_teams = db.session.query(Pick.team_id).join(Week).filter(
                Pick.user_id == user.id,
                Week.is_playoff_week == True,
                Pick.week_id != week_id
            ).all()
        else:
            # In regular season weeks (including CCW), check ALL NON-PLAYOFF WEEKS
            used_teams = db.session.query(Pick.team_id).join(Week).filter(
                Pick.user_id == user.id,
                Week.is_playoff_week == False,
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
                # Skip if team is eliminated from CFP
                if is_week_playoff(week) and game.home_team.name in cfp_eliminated_names:
                    continue
                
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
                # Skip if team is eliminated from CFP
                if is_week_playoff(week) and game.away_team.name in cfp_eliminated_names:
                    continue
                
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
                    # Skip if team is eliminated from CFP
                    if is_week_playoff(week) and game.home_team.name in cfp_eliminated_names:
                        continue
                    
                    if game.home_team_spread > 0:  # Home team is underdog
                        if game.home_team_spread < smallest_underdog_points:
                            smallest_underdog_points = game.home_team_spread
                            smallest_underdog = game.home_team
                            best_spread = game.home_team_spread
                
                # Check away team as underdog
                if game.away_team and game.away_team_id not in used_team_ids:
                    # Skip if team is eliminated from CFP
                    if is_week_playoff(week) and game.away_team.name in cfp_eliminated_names:
                        continue
                    
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
