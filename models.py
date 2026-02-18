"""
CF Survivor Pool - Database Models
===================================
SQLAlchemy models for users, teams, weeks, games, and picks.
"""

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from timezone_utils import deadline_has_passed
from constants import TEAM_CONFERENCES


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    lives_remaining = db.Column(db.Integer, default=2)
    is_eliminated = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    has_paid = db.Column(db.Boolean, default=False)
    cumulative_spread = db.Column(db.Float, default=0.0)
    _display_name = db.Column('display_name', db.String(80), nullable=True)

    picks = db.relationship('Pick', backref='user', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def calculate_cumulative_spread(self):
        """Calculate cumulative spread using a single joined query."""
        results = (
            db.session.query(Pick, Game)
            .join(Week, Pick.week_id == Week.id)
            .join(
                Game,
                db.and_(
                    Game.week_id == Pick.week_id,
                    db.or_(
                        Game.home_team_id == Pick.team_id,
                        Game.away_team_id == Pick.team_id,
                    ),
                ),
            )
            .filter(Pick.user_id == self.id)
            .all()
        )

        total = 0.0
        for pick, game in results:
            if not deadline_has_passed(pick.week.deadline):
                continue
            if pick.team_id == game.home_team_id:
                team_spread = game.home_team_spread
            else:
                team_spread = -game.home_team_spread
            # Favorites add positive, underdogs subtract
            if team_spread < 0:
                total += abs(team_spread)
            else:
                total -= team_spread

        self.cumulative_spread = total
        return total

    @property
    def display_name(self):
        return self._display_name or self.username

    def __repr__(self):
        return f'<User {self.username}>'


class Team(db.Model):
    __tablename__ = 'team'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    conference = db.Column(db.String(50))
    national_title_odds = db.Column(db.String(16), nullable=True)

    def get_conference(self):
        return TEAM_CONFERENCES.get(self.name, 'Unknown')

    def __repr__(self):
        return f'<Team {self.name}>'


class Week(db.Model):
    __tablename__ = 'week'

    id = db.Column(db.Integer, primary_key=True)
    week_number = db.Column(db.Integer, unique=True, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    is_complete = db.Column(db.Boolean, default=False)
    is_playoff_week = db.Column(db.Boolean, default=False)
    round_name = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Week {self.week_number}>'


class Game(db.Model):
    __tablename__ = 'game'

    id = db.Column(db.Integer, primary_key=True)
    week_id = db.Column(db.Integer, db.ForeignKey('week.id'), nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    home_team_name = db.Column(db.String(100), nullable=True)
    away_team_name = db.Column(db.String(100), nullable=True)
    home_team_spread = db.Column(db.Float)
    game_time = db.Column(db.DateTime)
    home_team_won = db.Column(db.Boolean, default=None)
    api_event_id = db.Column(db.String(64), nullable=True, index=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    spread_locked_at = db.Column(db.DateTime, nullable=True)

    week = db.relationship('Week', backref='games')
    home_team = db.relationship('Team', foreign_keys=[home_team_id], backref='home_games')
    away_team = db.relationship('Team', foreign_keys=[away_team_id], backref='away_games')

    def get_home_team_display(self):
        return self.home_team.name if self.home_team else self.home_team_name

    def get_away_team_display(self):
        return self.away_team.name if self.away_team else self.away_team_name

    def __repr__(self):
        return f'<Game {self.get_away_team_display()} @ {self.get_home_team_display()}>'


class Pick(db.Model):
    __tablename__ = 'pick'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_id = db.Column(db.Integer, db.ForeignKey('week.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    is_correct = db.Column(db.Boolean, default=None)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    week = db.relationship('Week', backref='picks')
    team = db.relationship('Team', backref='picks')

    __table_args__ = (db.UniqueConstraint('user_id', 'week_id'),)

    def __repr__(self):
        return f'<Pick user={self.user_id} week={self.week_id}>'
