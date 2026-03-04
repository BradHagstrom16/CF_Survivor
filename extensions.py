"""
CF Survivor Pool - Flask Extensions
====================================
Centralized extension instances, initialized in the app factory.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://",
)
