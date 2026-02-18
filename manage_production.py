"""
Production Management Script
Provides deployment workflow guidance for PythonAnywhere.
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class ProductionManager:
    def __init__(self):
        self.username = os.environ.get('PA_USERNAME', 'b1gbrad')
        self.local_db = 'picks.db'
        self.backup_dir = os.path.join(BASE_DIR, 'production_backups')
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup_production_db(self):
        """Remind user to download production database as backup."""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_dir, f'production_backup_{timestamp}.db')

        print(f'\nTo back up production database:')
        print(f'  1. Go to PythonAnywhere Files tab')
        print(f'  2. Navigate to /home/{self.username}/cfb-survivor-pool/')
        print(f'  3. Download picks.db')
        print(f'  4. Save as: {backup_file}')
        return backup_file

    def upload_database(self):
        """Guide user through uploading local database to production."""
        print('\nWARNING: This will overwrite the production database!')
        confirm = input("Type 'UPLOAD' to see instructions: ")
        if confirm != 'UPLOAD':
            print('Cancelled.')
            return

        self.backup_production_db()

        print(f'\nUpload steps:')
        print(f'  1. Go to PythonAnywhere Files tab')
        print(f'  2. Navigate to /home/{self.username}/cfb-survivor-pool/')
        print(f'  3. Delete old picks.db')
        print(f'  4. Upload your local picks.db')
        print(f'  5. Reload your web app')

    def push_code_changes(self):
        """Push code changes to production via git."""
        if not os.path.exists(os.path.join(BASE_DIR, '.git')):
            print('No git repo found. Upload files manually via PythonAnywhere Files tab.')
            return

        print('\nPushing code changes...')
        subprocess.run(['git', 'add', '.'], cwd=BASE_DIR)
        subprocess.run(['git', 'commit', '-m', 'Production update'], cwd=BASE_DIR)
        subprocess.run(['git', 'push'], cwd=BASE_DIR)

        print(f'\nCode pushed. Now on PythonAnywhere:')
        print(f'  1. Open Bash console')
        print(f'  2. cd ~/cfb-survivor-pool')
        print(f'  3. git pull')
        print(f'  4. Web tab -> Reload')

    def show_workflow(self):
        """Display the production workflow."""
        print('\n' + '=' * 60)
        print('PRODUCTION WORKFLOW')
        print('=' * 60)
        print('\nWEEKLY GAME MANAGEMENT:')
        print('  1. Work locally - import and verify games')
        print('  2. Test everything locally')
        print('  3. Upload database via PythonAnywhere Files tab')
        print('  4. Reload web app')

        print('\nCODE CHANGES:')
        print('  1. Make changes locally')
        print('  2. Test thoroughly')
        print('  3. git commit & push')
        print('  4. git pull on PythonAnywhere')
        print('  5. Reload web app')

        print('\nQUICK ADMIN TASKS (do on production directly):')
        print('  - Mark game results')
        print('  - Process auto-picks')
        print('  - View standings')

        print(f'\nURLS:')
        print(f'  Public: https://{self.username}.pythonanywhere.com')
        print(f'  Admin:  https://{self.username}.pythonanywhere.com/admin')
        print(f'  PA:     https://www.pythonanywhere.com')
        print('=' * 60)


def main():
    manager = ProductionManager()

    while True:
        print('\n' + '=' * 60)
        print('PRODUCTION MANAGEMENT')
        print('=' * 60)
        print('1. Show Production Workflow')
        print('2. Backup Production Database')
        print('3. Upload Local Database to Production')
        print('4. Push Code Changes')
        print('5. Exit')

        choice = input('\nSelect option (1-5): ').strip()

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


if __name__ == '__main__':
    main()
