"""Automated weekly backup wrapper.

Run via cron:
    python weekly_backup.py
"""

from backup_database import DatabaseBackupManager

if __name__ == '__main__':
    manager = DatabaseBackupManager()
    manager.create_backup('weekly', 'Automated weekly backup')
    manager.cleanup_old_backups()
