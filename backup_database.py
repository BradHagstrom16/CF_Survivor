"""
Database Backup System for CFB Survivor Pool
Creates organized, timestamped backups with metadata and restore capabilities.
"""

import json
import logging
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('ENVIRONMENT', 'production')

from app import create_app
from extensions import db
from models import User, Week, Game, Pick
from timezone_utils import get_current_time, POOL_TZ_NAME

logger = logging.getLogger(__name__)

app = create_app()


class DatabaseBackupManager:
    """Manages database backups with metadata and organization."""

    def __init__(self):
        self.backup_root = os.path.join(BASE_DIR, 'backups')
        self.weekly_dir = os.path.join(self.backup_root, 'weekly')
        self.manual_dir = os.path.join(self.backup_root, 'manual')
        self.auto_dir = os.path.join(self.backup_root, 'auto')

        for directory in [self.backup_root, self.weekly_dir, self.manual_dir, self.auto_dir]:
            os.makedirs(directory, exist_ok=True)

        with app.app_context():
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        # Extract file path from sqlite URI
        if db_uri.startswith('sqlite:///'):
            self.db_file = db_uri.replace('sqlite:///', '')
        else:
            self.db_file = os.path.join(BASE_DIR, 'picks.db')

    def get_pool_stats(self):
        """Gather current statistics about the pool."""
        with app.app_context():
            stats = {
                'total_users': User.query.count(),
                'active_users': User.query.filter_by(is_eliminated=False).count(),
                'eliminated_users': User.query.filter_by(is_eliminated=True).count(),
                'total_weeks': Week.query.count(),
                'total_games': Game.query.count(),
                'total_picks': Pick.query.count(),
                'current_week': None,
                'completed_weeks': [],
            }

            current_week = Week.query.filter_by(is_active=True).first()
            if current_week:
                stats['current_week'] = current_week.week_number

            completed = Week.query.filter_by(is_complete=True).all()
            stats['completed_weeks'] = [w.week_number for w in completed]

            leader = User.query.filter_by(is_eliminated=False).order_by(
                User.lives_remaining.desc(),
                User.cumulative_spread.desc(),
            ).first()

            if leader:
                stats['current_leader'] = {
                    'username': leader.username,
                    'lives': leader.lives_remaining,
                    'spread': float(leader.cumulative_spread),
                }

            return stats

    def create_backup(self, backup_type='manual', description=''):
        """Create a backup with metadata.

        Args:
            backup_type: 'weekly', 'manual', or 'auto'
            description: Optional description of why backup was created

        Returns:
            Path to the created backup, or None on failure.
        """
        timestamp = get_current_time().strftime('%Y%m%d_%H%M%S')
        stats = self.get_pool_stats()
        week_num = stats.get('current_week', 0)

        if backup_type == 'weekly':
            backup_dir = self.weekly_dir
            filename = f'week_{week_num:02d}_backup_{timestamp}.db'
        elif backup_type == 'auto':
            backup_dir = self.auto_dir
            filename = f'auto_backup_{timestamp}.db'
        else:
            backup_dir = self.manual_dir
            filename = f'manual_backup_{timestamp}.db'

        metadata_file = filename.replace('.db', '.json')
        backup_path = os.path.join(backup_dir, filename)
        metadata_path = os.path.join(backup_dir, metadata_file)

        if not os.path.exists(self.db_file):
            logger.error("Database file '%s' not found!", self.db_file)
            return None

        try:
            shutil.copy2(self.db_file, backup_path)

            metadata = {
                'backup_type': backup_type,
                'timestamp': timestamp,
                'timezone': POOL_TZ_NAME,
                'readable_time': get_current_time().strftime('%B %d, %Y at %I:%M %p %Z'),
                'description': description,
                'filename': filename,
                'file_size_mb': round(os.path.getsize(backup_path) / (1024 * 1024), 2),
                'pool_stats': stats,
            }

            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info("Backup created: %s (%.2f MB)", backup_path, metadata['file_size_mb'])
            return backup_path

        except Exception as e:
            logger.error("Backup failed: %s", e)
            return None

    def list_backups(self, backup_type=None):
        """List all available backups with their metadata."""
        if backup_type:
            dirs_to_check = [(backup_type, getattr(self, f'{backup_type}_dir'))]
        else:
            dirs_to_check = [
                ('weekly', self.weekly_dir),
                ('manual', self.manual_dir),
                ('auto', self.auto_dir),
            ]

        total_backups = 0

        for type_name, directory in dirs_to_check:
            backups = [f for f in os.listdir(directory) if f.endswith('.db')]
            if not backups:
                continue

            print(f'\n{type_name.upper()} BACKUPS ({len(backups)}):')
            print('-' * 40)

            for backup in sorted(backups, reverse=True):
                total_backups += 1
                metadata_file = backup.replace('.db', '.json')
                metadata_path = os.path.join(directory, metadata_file)

                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    print(f'\n  {backup}')
                    print(f"    Created: {metadata.get('readable_time', 'Unknown')}")
                    print(f"    Size: {metadata.get('file_size_mb', 'Unknown')} MB")
                    if metadata.get('description'):
                        print(f"    Note: {metadata['description']}")
                    stats = metadata.get('pool_stats', {})
                    if stats:
                        print(f"    Week: {stats.get('current_week', 'N/A')}")
                        print(f"    Users: {stats.get('active_users', 0)} active, "
                              f"{stats.get('eliminated_users', 0)} eliminated")
                else:
                    print(f'\n  {backup} (no metadata)')

        print(f'\nTotal backups: {total_backups}')
        print(f'Total size: {self.get_total_backup_size():.2f} MB')

    def get_total_backup_size(self):
        """Calculate total size of all backups in MB."""
        total_size = 0
        for directory in [self.weekly_dir, self.manual_dir, self.auto_dir]:
            for file in os.listdir(directory):
                if file.endswith('.db'):
                    total_size += os.path.getsize(os.path.join(directory, file))
        return total_size / (1024 * 1024)

    def restore_backup(self, backup_filename):
        """Restore a database from a backup.

        CAUTION: This will overwrite the current database!
        """
        backup_path = None
        for directory in [self.weekly_dir, self.manual_dir, self.auto_dir]:
            potential_path = os.path.join(directory, backup_filename)
            if os.path.exists(potential_path):
                backup_path = potential_path
                break

        if not backup_path:
            logger.error("Backup file '%s' not found!", backup_filename)
            return False

        logger.info("Creating safety backup of current database...")
        safety_backup = self.create_backup('manual', 'Pre-restore safety backup')
        if not safety_backup:
            logger.error("Failed to create safety backup. Restore cancelled.")
            return False

        print(f'\nWARNING: This will replace your current database!')
        print(f'Restoring from: {backup_filename}')

        metadata_file = backup_filename.replace('.db', '.json')
        metadata_path = os.path.join(os.path.dirname(backup_path), metadata_file)
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            print(f"Backup created: {metadata.get('readable_time', 'Unknown')}")
            print(f"Description: {metadata.get('description', 'None')}")

        confirm = input("\nType 'RESTORE' to confirm: ")
        if confirm != 'RESTORE':
            print('Restore cancelled.')
            return False

        try:
            shutil.copy2(backup_path, self.db_file)
            logger.info("Database restored from %s", backup_filename)
            return True
        except Exception as e:
            logger.error("Restore failed: %s", e)
            try:
                shutil.copy2(safety_backup, self.db_file)
                logger.info("Safety backup restored.")
            except Exception:
                logger.critical("Could not restore safety backup at: %s", safety_backup)
            return False

    def cleanup_old_backups(self, keep_weekly=10, keep_auto=5, keep_manual=20):
        """Remove old backups to save space."""
        cleanup_configs = [
            (self.weekly_dir, keep_weekly, 'weekly'),
            (self.auto_dir, keep_auto, 'auto'),
            (self.manual_dir, keep_manual, 'manual'),
        ]

        total_removed = 0
        for directory, keep_count, backup_type in cleanup_configs:
            backups = sorted(f for f in os.listdir(directory) if f.endswith('.db'))
            if len(backups) <= keep_count:
                continue

            for backup in backups[:-keep_count]:
                backup_path = os.path.join(directory, backup)
                metadata_path = backup_path.replace('.db', '.json')
                try:
                    os.remove(backup_path)
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                    logger.info("Removed old %s backup: %s", backup_type, backup)
                    total_removed += 1
                except Exception as e:
                    logger.warning("Failed to remove %s: %s", backup, e)

        if total_removed:
            logger.info("Removed %d old backup(s).", total_removed)
        else:
            logger.info("No old backups to remove.")


def main():
    """Interactive command-line backup manager."""
    manager = DatabaseBackupManager()

    while True:
        print('\n' + '=' * 60)
        print('CFB SURVIVOR POOL - DATABASE BACKUP MANAGER')
        print('=' * 60)
        print('1. Create Weekly Backup')
        print('2. Create Manual Backup')
        print('3. List All Backups')
        print('4. Restore from Backup')
        print('5. Cleanup Old Backups')
        print('6. Exit')
        print('=' * 60)

        choice = input('\nSelect option (1-6): ').strip()

        if choice == '1':
            description = input('Enter description (optional): ').strip()
            manager.create_backup('weekly', description)
        elif choice == '2':
            description = input('Enter description: ').strip()
            manager.create_backup('manual', description or 'Manual backup')
        elif choice == '3':
            manager.list_backups()
        elif choice == '4':
            manager.list_backups()
            filename = input('\nEnter backup filename to restore: ').strip()
            if filename:
                manager.restore_backup(filename)
        elif choice == '5':
            print('\nDefault retention: 10 weekly, 5 auto, 20 manual')
            if input('Proceed with cleanup? (y/n): ').strip().lower() == 'y':
                manager.cleanup_old_backups()
        elif choice == '6':
            break


if __name__ == '__main__':
    main()
