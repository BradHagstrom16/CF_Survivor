"""
CF Survivor Pool - Application Factory
========================================
Creates and configures the Flask application.
"""

import logging
import os

import click
from flask import Flask, render_template

from config import config
from extensions import db, login_manager, csrf, limiter
from db_maintenance import (
    ensure_team_national_title_odds_column,
    ensure_user_is_admin_column,
    ensure_user_display_name_column,
    ensure_game_automation_columns,
)


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('ENVIRONMENT', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ── Logging ──────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )

    # ── Extensions ───────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # ── User loader ──────────────────────────────────────────────────────
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Schema migrations ────────────────────────────────────────────────
    ensure_team_national_title_odds_column(app, db, reporter=app.logger.info)
    ensure_user_is_admin_column(app, db, reporter=app.logger.info)
    ensure_user_display_name_column(app, db, reporter=app.logger.info)
    ensure_game_automation_columns(app, db, reporter=app.logger.info)

    # ── Blueprints ───────────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    # ── Context processors ───────────────────────────────────────────────
    from timezone_utils import format_deadline, to_pool_time, get_current_time, POOL_TZ_NAME
    from display_utils import get_display_helpers

    @app.context_processor
    def inject_helpers():
        helpers = {
            'format_deadline': format_deadline,
            'to_pool_time': to_pool_time,
            'get_current_time': get_current_time,
            'timezone': POOL_TZ_NAME,
            'entry_fee': app.config.get('ENTRY_FEE', 25),
        }
        helpers.update(get_display_helpers())
        return helpers

    # ── Error handlers ───────────────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # ── CLI commands ─────────────────────────────────────────────────────
    @app.cli.command('init-db')
    def init_db_command():
        """Create all database tables."""
        db.create_all()
        app.logger.info('Database tables created.')

    @app.cli.command('cfb-sync')
    @click.option('--mode', required=True,
                  type=click.Choice(['setup', 'spreads', 'scores', 'autopick', 'remind', 'status']),
                  help='Sync mode to run.')
    def cfb_sync_command(mode):
        """Unified CFB automation CLI — run weekly tasks by mode."""
        from services.automation import run_setup, run_spread_update, run_scores, run_status
        from services.game_logic import check_and_process_autopicks

        if mode == 'setup':
            result = run_setup()
        elif mode == 'spreads':
            result = run_spread_update()
        elif mode == 'scores':
            result = run_scores()
        elif mode == 'autopick':
            results = check_and_process_autopicks()
            result = {
                'status': 'processed',
                'details': '\n'.join(results) if results else 'No auto-picks needed',
            }
        elif mode == 'remind':
            from send_reminders import main as send_reminders_main
            send_reminders_main()
            result = {'status': 'ok', 'details': 'Reminder check complete'}
        elif mode == 'status':
            result = run_status()

        click.echo(f"\n[cfb-sync --mode {mode}]")
        click.echo(result.get('details', str(result)))

    return app


# Allow ``python app.py`` for local development
if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
