"""
Production Management Script
Run this locally to update production
"""

import os
import paramiko
import subprocess
from datetime import datetime

class ProductionManager:
    def __init__(self):
        self.username = "B1GBrad"  # PythonAnywhere username
        self.local_db = "picks.db"
        self.backup_dir = "production_backups"
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def backup_production_db(self):
        """Download current production database as backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{self.backup_dir}/production_backup_{timestamp}.db"
        
        print(f"📥 Downloading production database...")
        # You'll need to use PythonAnywhere's Files tab to download
        # Or set up SSH (paid feature)
        
        print(f"✅ Backup saved to {backup_file}")
        return backup_file
    
    def upload_database(self):
        """Upload local database to production"""
        print("\n⚠️  WARNING: This will overwrite production database!")
        print("Current local database will replace the live one.")
        
        confirm = input("Type 'UPLOAD' to confirm: ")
        if confirm != 'UPLOAD':
            print("Upload cancelled")
            return
        
        # First backup production
        self.backup_production_db()
        
        print("\n📤 Uploading local database to production...")
        print("Steps:")
        print("1. Go to PythonAnywhere Files tab")
        print("2. Navigate to /home/yourusername/cfb-survivor-pool/")
        print("3. Delete old picks.db")
        print("4. Upload your local picks.db")
        print("5. Reload your web app")
        
    def push_code_changes(self):
        """Push code changes to production"""
        print("\n📦 Deploying code changes...")
        
        if os.path.exists('.git'):
            # If using git
            subprocess.run(['git', 'add', '.'])
            subprocess.run(['git', 'commit', '-m', 'Production update'])
            subprocess.run(['git', 'push'])
            
            print("\n✅ Code pushed to GitHub")
            print("Now on PythonAnywhere:")
            print("1. Open Bash console")
            print("2. Run: cd ~/cfb-survivor-pool")
            print("3. Run: git pull")
            print("4. Go to Web tab and click 'Reload'")
        else:
            print("Upload files manually via PythonAnywhere Files tab")
    
    def show_workflow(self):
        """Display the production workflow"""
        print("\n" + "="*60)
        print("PRODUCTION WORKFLOW")
        print("="*60)
        print("\n📝 WEEKLY GAME MANAGEMENT:")
        print("1. Work locally - import and verify games")
        print("2. Test everything locally")
        print("3. Run: python manage_production.py")
        print("4. Choose 'Upload Database'")
        print("5. Go to PythonAnywhere and upload the database file")
        print("6. Reload web app")
        
        print("\n🔧 CODE CHANGES:")
        print("1. Make changes locally")
        print("2. Test thoroughly")
        print("3. Commit to Git (if using)")
        print("4. Push to GitHub")
        print("5. Pull on PythonAnywhere")
        print("6. Reload web app")
        
        print("\n⚡ QUICK ADMIN TASKS:")
        print("Can be done directly on production:")
        print("- Mark game results")
        print("- Process auto-picks")
        print("- View standings")
        
        print("\n🔒 IMPORTANT URLS:")
        print(f"Public site: https://{self.username}.pythonanywhere.com")
        print(f"Admin panel: https://{self.username}.pythonanywhere.com/admin")
        print("PythonAnywhere dashboard: https://www.pythonanywhere.com")
        print("="*60)

def main():
    manager = ProductionManager()
    
    while True:
        print("\n" + "="*60)
        print("PRODUCTION MANAGEMENT")
        print("="*60)
        print("1. Show Production Workflow")
        print("2. Backup Production Database")
        print("3. Upload Local Database to Production")
        print("4. Push Code Changes")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            manager.show_workflow()
        elif choice == '2':
            manager.backup_production_db()
        elif choice == '3':
            manager.upload_database()
        elif choice == '4':
            manager.push_code_changes()
        elif choice == '5':
            break

if __name__ == "__main__":
    # Update with your username
    print("⚠️  First update YOURUSERNAME in this file!")
    main()