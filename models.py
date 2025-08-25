from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize database
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model - stores user account information"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    lives_remaining = db.Column(db.Integer, default=2)
    is_eliminated = db.Column(db.Boolean, default=False)
    cumulative_spread = db.Column(db.Float, default=0.0)  # Add this line
    
    # Relationship to picks
    picks = db.relationship('Pick', backref='user', lazy=True)
    
    def calculate_cumulative_spread(self):
        """Calculate and update the user's cumulative spread based on all picks"""
        total = 0.0
        for pick in self.picks:
            # Find the game to get the spread
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
                
                # Add to cumulative (favorites add positive, underdogs subtract)
                if team_spread < 0:  # Favorite
                    total += abs(team_spread)
                else:  # Underdog
                    total -= team_spread
        
        self.cumulative_spread = total
        return total

class Team(db.Model):
    """Team model - stores college football teams"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    conference = db.Column(db.String(50))  # Optional: SEC, Big Ten, etc.
    
class Week(db.Model):
    """Week model - represents each week of the season"""
    id = db.Column(db.Integer, primary_key=True)
    week_number = db.Column(db.Integer, unique=True, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)  # When picks lock
    is_active = db.Column(db.Boolean, default=False)  # Current week flag
    is_complete = db.Column(db.Boolean, default=False)  # Week results finalized
    
class Game(db.Model):
    """Game model - stores individual games and spreads"""
    id = db.Column(db.Integer, primary_key=True)
    week_id = db.Column(db.Integer, db.ForeignKey('week.id'), nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)  # Now nullable
    away_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)  # Now nullable
    
    # New fields for non-tracked teams
    home_team_name = db.Column(db.String(100), nullable=True)  # Store name if not in Team table
    away_team_name = db.Column(db.String(100), nullable=True)  # Store name if not in Team table
    
    home_team_spread = db.Column(db.Float)
    game_time = db.Column(db.DateTime)
    home_team_won = db.Column(db.Boolean, default=None)
    
    # Update relationships to handle nullable foreign keys
    week = db.relationship('Week', backref='games')
    home_team = db.relationship('Team', foreign_keys=[home_team_id], backref='home_games')
    away_team = db.relationship('Team', foreign_keys=[away_team_id], backref='away_games')
    
    def get_home_team_display(self):
        """Returns the home team name for display"""
        return self.home_team.name if self.home_team else self.home_team_name
    
    def get_away_team_display(self):
        """Returns the away team name for display"""
        return self.away_team.name if self.away_team else self.away_team_name

class Pick(db.Model):
    """Pick model - stores user selections"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_id = db.Column(db.Integer, db.ForeignKey('week.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    is_correct = db.Column(db.Boolean, default=None)  # None = game not complete
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    week = db.relationship('Week', backref='picks')
    team = db.relationship('Team', backref='picks')
    
    # Ensure user can only pick once per week
    __table_args__ = (db.UniqueConstraint('user_id', 'week_id'),)