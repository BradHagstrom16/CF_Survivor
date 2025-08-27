from backup_database import DatabaseBackupManager

if __name__ == "__main__":
    manager = DatabaseBackupManager()
    manager.create_backup("weekly", "Automated weekly backup")
    manager.cleanup_old_backups()  # optional: cleans up old backups
