"""
Database Backup System for CFB Survivor Pool
Creates organized, timestamped backups with metadata and restore capabilities
"""

import os
import shutil
import json
from datetime import datetime
from app import app, db
from models import User, Week, Game, Pick, Team
from timezone_utils import get_current_time, POOL_TZ_NAME

class DatabaseBackupManager:
    """Manages database backups with metadata and organization"""
    
    def __init__(self):
        # Create backups directory structure
        self.backup_root = "backups"
        self.weekly_dir = os.path.join(self.backup_root, "weekly")
        self.manual_dir = os.path.join(self.backup_root, "manual")
        self.auto_dir = os.path.join(self.backup_root, "auto")
        
        # Create directories if they don't exist
        for directory in [self.backup_root, self.weekly_dir, self.manual_dir, self.auto_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Database file path
        self.db_file = "picks.db"
    
    def get_pool_stats(self):
        """Gather current statistics about the pool"""
        with app.app_context():
            stats = {
                "total_users": User.query.count(),
                "active_users": User.query.filter_by(is_eliminated=False).count(),
                "eliminated_users": User.query.filter_by(is_eliminated=True).count(),
                "total_weeks": Week.query.count(),
                "total_games": Game.query.count(),
                "total_picks": Pick.query.count(),
                "current_week": None,
                "completed_weeks": []
            }
            
            # Get current active week
            current_week = Week.query.filter_by(is_active=True).first()
            if current_week:
                stats["current_week"] = current_week.week_number
            
            # Get completed weeks
            completed = Week.query.filter_by(is_complete=True).all()
            stats["completed_weeks"] = [w.week_number for w in completed]
            
            # Get leader information
            leader = User.query.filter_by(is_eliminated=False).order_by(
                User.lives_remaining.desc(),
                User.cumulative_spread.desc()
            ).first()
            
            if leader:
                stats["current_leader"] = {
                    "username": leader.username,
                    "lives": leader.lives_remaining,
                    "spread": float(leader.cumulative_spread)
                }
            
            return stats
    
    def create_backup(self, backup_type="manual", description=""):
        """
        Create a backup with metadata
        
        Args:
            backup_type: 'weekly', 'manual', or 'auto'
            description: Optional description of why backup was created
        
        Returns:
            Path to the created backup
        """
        # Generate timestamp
        timestamp = get_current_time().strftime("%Y%m%d_%H%M%S")
        
        # Get current stats
        stats = self.get_pool_stats()
        week_num = stats.get("current_week", 0)
        
        # Determine backup directory and filename
        if backup_type == "weekly":
            backup_dir = self.weekly_dir
            filename = f"week_{week_num:02d}_backup_{timestamp}.db"
            metadata_file = f"week_{week_num:02d}_backup_{timestamp}.json"
        elif backup_type == "auto":
            backup_dir = self.auto_dir
            filename = f"auto_backup_{timestamp}.db"
            metadata_file = f"auto_backup_{timestamp}.json"
        else:  # manual
            backup_dir = self.manual_dir
            filename = f"manual_backup_{timestamp}.db"
            metadata_file = f"manual_backup_{timestamp}.json"
        
        # Full paths
        backup_path = os.path.join(backup_dir, filename)
        metadata_path = os.path.join(backup_dir, metadata_file)
        
        # Check if database exists
        if not os.path.exists(self.db_file):
            print(f"❌ Database file '{self.db_file}' not found!")
            return None
        
        try:
            # Copy the database file
            shutil.copy2(self.db_file, backup_path)
            
            # Create metadata
            metadata = {
                "backup_type": backup_type,
                "timestamp": timestamp,
                "timezone": POOL_TZ_NAME,
                "readable_time": get_current_time().strftime("%B %d, %Y at %I:%M %p %Z"),
                "description": description,
                "filename": filename,
                "file_size_mb": round(os.path.getsize(backup_path) / (1024 * 1024), 2),
                "pool_stats": stats
            }
            
            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Backup created successfully!")
            print(f"   Database: {backup_path}")
            print(f"   Metadata: {metadata_path}")
            print(f"   Size: {metadata['file_size_mb']} MB")
            
            if stats.get("current_week"):
                print(f"   Week: {stats['current_week']}")
            print(f"   Active Users: {stats['active_users']}")
            print(f"   Total Picks: {stats['total_picks']}")
            
            return backup_path
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def list_backups(self, backup_type=None):
        """List all available backups with their metadata"""
        print("\n" + "="*60)
        print("AVAILABLE BACKUPS")
        print("="*60)
        
        # Determine which directories to check
        if backup_type:
            dirs_to_check = [(backup_type, getattr(self, f"{backup_type}_dir"))]
        else:
            dirs_to_check = [
                ("weekly", self.weekly_dir),
                ("manual", self.manual_dir),
                ("auto", self.auto_dir)
            ]
        
        total_backups = 0
        
        for type_name, directory in dirs_to_check:
            backups = [f for f in os.listdir(directory) if f.endswith('.db')]
            
            if backups:
                print(f"\n📁 {type_name.upper()} BACKUPS ({len(backups)}):")
                print("-" * 40)
                
                for backup in sorted(backups, reverse=True):
                    total_backups += 1
                    metadata_file = backup.replace('.db', '.json')
                    metadata_path = os.path.join(directory, metadata_file)
                    
                    # Try to load metadata
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        print(f"\n  {backup}")
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
                        print(f"\n  {backup} (no metadata)")
        
        print(f"\n{'='*60}")
        print(f"Total backups: {total_backups}")
        print(f"Total size: {self.get_total_backup_size():.2f} MB")
        print("="*60)
    
    def get_total_backup_size(self):
        """Calculate total size of all backups in MB"""
        total_size = 0
        for directory in [self.weekly_dir, self.manual_dir, self.auto_dir]:
            for file in os.listdir(directory):
                if file.endswith('.db'):
                    file_path = os.path.join(directory, file)
                    total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)
    
    def restore_backup(self, backup_filename):
        """
        Restore a database from a backup
        
        CAUTION: This will overwrite the current database!
        """
        # Find the backup file
        backup_path = None
        for directory in [self.weekly_dir, self.manual_dir, self.auto_dir]:
            potential_path = os.path.join(directory, backup_filename)
            if os.path.exists(potential_path):
                backup_path = potential_path
                break
        
        if not backup_path:
            print(f"❌ Backup file '{backup_filename}' not found!")
            return False
        
        # Create a safety backup of current database
        print("Creating safety backup of current database...")
        safety_backup = self.create_backup("manual", "Pre-restore safety backup")
        
        if not safety_backup:
            print("❌ Failed to create safety backup. Restore cancelled.")
            return False
        
        # Confirm restore
        print(f"\n⚠️  WARNING: This will replace your current database!")
        print(f"Restoring from: {backup_filename}")
        
        metadata_file = backup_filename.replace('.db', '.json')
        metadata_path = os.path.join(os.path.dirname(backup_path), metadata_file)
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            print(f"Backup created: {metadata.get('readable_time', 'Unknown')}")
            print(f"Description: {metadata.get('description', 'None')}")
        
        confirm = input("\nType 'RESTORE' to confirm: ")
        
        if confirm != 'RESTORE':
            print("Restore cancelled.")
            return False
        
        try:
            # Restore the backup
            shutil.copy2(backup_path, self.db_file)
            print(f"✅ Database restored successfully from {backup_filename}")
            print(f"Safety backup saved as: {os.path.basename(safety_backup)}")
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            print(f"Attempting to restore safety backup...")
            
            try:
                shutil.copy2(safety_backup, self.db_file)
                print("✅ Safety backup restored")
            except:
                print("❌ CRITICAL: Could not restore safety backup!")
                print(f"Manual intervention needed. Safety backup at: {safety_backup}")
            
            return False
    
    def cleanup_old_backups(self, keep_weekly=10, keep_auto=5, keep_manual=20):
        """
        Remove old backups to save space
        
        Args:
            keep_weekly: Number of weekly backups to keep
            keep_auto: Number of auto backups to keep  
            keep_manual: Number of manual backups to keep
        """
        print("\nCleaning up old backups...")
        
        cleanup_configs = [
            (self.weekly_dir, keep_weekly, "weekly"),
            (self.auto_dir, keep_auto, "auto"),
            (self.manual_dir, keep_manual, "manual")
        ]
        
        total_removed = 0
        
        for directory, keep_count, backup_type in cleanup_configs:
            backups = sorted([f for f in os.listdir(directory) if f.endswith('.db')])
            
            if len(backups) > keep_count:
                to_remove = backups[:-keep_count]  # Remove oldest
                
                for backup in to_remove:
                    backup_path = os.path.join(directory, backup)
                    metadata_path = backup_path.replace('.db', '.json')
                    
                    try:
                        os.remove(backup_path)
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                        
                        print(f"  Removed old {backup_type} backup: {backup}")
                        total_removed += 1
                    except Exception as e:
                        print(f"  Failed to remove {backup}: {e}")
        
        if total_removed > 0:
            print(f"✅ Removed {total_removed} old backup(s)")
        else:
            print("✅ No old backups to remove")

def main():
    """Main function for command-line usage"""
    manager = DatabaseBackupManager()
    
    while True:
        print("\n" + "="*60)
        print("CFB SURVIVOR POOL - DATABASE BACKUP MANAGER")
        print("="*60)
        print("1. Create Weekly Backup")
        print("2. Create Manual Backup")
        print("3. List All Backups")
        print("4. Restore from Backup")
        print("5. Cleanup Old Backups")
        print("6. Exit")
        print("="*60)
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            description = input("Enter description (optional): ").strip()
            manager.create_backup("weekly", description)
            
        elif choice == '2':
            description = input("Enter description: ").strip()
            manager.create_backup("manual", description or "Manual backup")
            
        elif choice == '3':
            manager.list_backups()
            
        elif choice == '4':
            manager.list_backups()
            filename = input("\nEnter backup filename to restore: ").strip()
            if filename:
                manager.restore_backup(filename)
            
        elif choice == '5':
            print("\nDefault retention policy:")
            print("  - Keep 10 most recent weekly backups")
            print("  - Keep 5 most recent auto backups")
            print("  - Keep 20 most recent manual backups")
            
            confirm = input("\nProceed with cleanup? (y/n): ").strip().lower()
            if confirm == 'y':
                manager.cleanup_old_backups()
            
        elif choice == '6':
            print("Goodbye!")
            break
        
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()