# 🏈 CFB Survivor Pool

A sophisticated web application for managing college football survivor pools with advanced features including playoff support, automatic team availability reset, spread tracking, and comprehensive admin tools.

![CFB Survivor Pool](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1.1-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

### Core Functionality
- **Survivor Pool Mechanics**: Classic survivor pool format where players pick one team per week
- **Two Lives System**: Each player starts with 2 lives, losing one for each incorrect pick
- **Team Usage Restrictions**: Teams can only be picked once per season (resets for playoffs)
- **Spread Tracking**: Sophisticated cumulative spread calculation for tiebreaking
- **Automatic Pick Processing**: Auto-picks for missed deadlines using intelligent team selection

### Advanced Playoff System
- **College Football Playoff Support**: Full CFP integration with automatic team availability reset
- **12-Team Playoff Field**: Tracks the initial playoff teams and their elimination status
- **Elimination Tracking**: Automatically removes teams that lose playoff games from future availability
- **Custom Round Names**: Display names like "CFP Round 1", "CFP Semifinals", etc.
- **Revival Rule**: All players at 1 life are revived if they all lose in the same week

### Spread & Scoring Features
- **Point Spread Integration**: Imports spreads from The Odds API
- **Cumulative Spread Tiebreaker**: Rewards strategic underdog picks
- **Team Favoritism Limits**: Teams favored by 16.5+ points are ineligible
- **National Championship Odds**: Displays championship odds for each team

### User Experience
- **Responsive Design**: Mobile-first Bootstrap interface
- **Real-Time Standings**: Live updates of pool standings and picks
- **Conference Coverage Tracking**: Helps users manage conference championship picks
- **Weekly Results**: Comprehensive results display with pick distribution analytics
- **Personal Pick History**: Detailed pick tracking with spread information

### Admin Tools
- **Comprehensive Dashboard**: Complete pool management interface
- **Game Import System**: Automated game importing from The Odds API
- **Results Management**: Easy game result entry and pick processing
- **User Management**: Password resets and user administration
- **Payment Tracking**: Built-in payment status tracking
- **Auto-Pick Processing**: Manual trigger for missed deadline processing

### Technical Features
- **Timezone-Aware**: Consistent Chicago/Central timezone handling throughout
- **Database Backups**: Comprehensive backup system with metadata
- **Email Notifications**: Automated reminder system for upcoming deadlines
- **Security**: Password hashing and secure authentication

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip package manager
- SQLite3
- (Optional) PythonAnywhere account for deployment

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/cfb-survivor-pool.git
cd cfb-survivor-pool
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///picks.db
POOL_TIMEZONE=America/Chicago
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
POOL_URL=http://localhost:5000
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

5. **Initialize the database**
```bash
python app.py
# Visit http://localhost:5000/init-db in your browser
# Then run:
python populate_teams.py
```

6. **Create your first week**
- Log in as admin (username: admin)
- Navigate to Admin Dashboard
- Create Week 1 with appropriate dates and deadline

7. **Import games**
```bash
python import_games.py
```

## 📋 Configuration

### Email Configuration
For email reminders, create `email_config.py`:
```python
EMAIL_ADDRESS = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-specific-password"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
POOL_URL = "https://your-domain.com"
```

### The Odds API
Get your API key from [The Odds API](https://the-odds-api.com/) and update in `import_games.py`:
```python
self.api_key = "your-api-key-here"
```

## 🎮 Usage

### For Players
1. **Register**: Create an account at the registration page
2. **Make Picks**: Navigate to "My Picks & Strategy" to see available teams
3. **Submit Weekly Picks**: Pick your team before the deadline each week
4. **Track Progress**: Monitor standings and your pick history

### For Administrators
1. **Create Weeks**: Set up each week with start date and pick deadline
2. **Import Games**: Use the import script to fetch games and spreads
3. **Activate Week**: Make the week active so players can submit picks
4. **Mark Results**: Enter game results and automatically process picks
5. **Monitor Pool**: Track payments, user activity, and standings

## 📂 Project Structure

```
cfb-survivor-pool/
├── app.py                      # Main Flask application
├── models.py                   # Database models
├── config.py                   # Configuration settings
├── extensions.py               # Flask extensions
├── display_utils.py            # Week display helpers
├── datetime_utils.py           # Timezone utilities
├── timezone_utils.py           # Additional timezone helpers
├── import_games.py             # Game import from The Odds API
├── populate_teams.py           # Initial team population
├── send_reminders.py           # Email reminder script
├── run_autopicks.py            # Auto-pick processing
├── backup_database.py          # Database backup system
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in repo)
├── templates/                  # HTML templates
│   ├── base.html
│   ├── index.html             # Main standings page
│   ├── pick.html              # Pick submission page
│   ├── my_picks.html          # Personal pick history
│   ├── weekly_results.html    # Weekly results display
│   ├── admin/                 # Admin templates
│   │   ├── dashboard.html
│   │   ├── manage_games.html
│   │   ├── mark_results.html
│   │   └── ...
│   └── ...
├── static/                     # Static assets
│   └── style.css              # Custom CSS
└── backups/                    # Database backups (auto-created)
```

## 🎯 Key Features Explained

### Playoff System
The application automatically handles the College Football Playoff with special rules:
- Teams used in regular season (Weeks 1-15) can be reused in playoffs (Week 16+)
- Teams that lose playoff games are automatically removed from future availability
- Custom round names display appropriately (e.g., "CFP Round 1", "CFP Semifinals")

### Spread Calculation
The cumulative spread system rewards strategic play:
- Picking favorites (negative spread) adds to your total: -7 spread → +7 points
- Picking underdogs (positive spread) subtracts from your total: +3 spread → -3 points
- Lower cumulative spread is better for tiebreaking

### Auto-Pick System
If a player misses the deadline, the system automatically:
1. Finds the biggest favorite they haven't used (up to 16 points)
2. If no favorites available, picks the smallest underdog
3. Excludes teams that have been eliminated from the CFP (if playoff week)
4. Records the pick with a timestamp after the deadline

## 🔧 Maintenance Tasks

### Weekly Workflow
1. Import games: `python import_games.py`
2. Verify games in admin dashboard
3. Activate the week
4. After deadline, run auto-picks: `python run_autopicks.py`
5. After games complete, mark results in admin panel
6. Create next week

### Backups
```bash
python backup_database.py
# Choose option 1 for weekly backup
```

### Email Reminders
Set up a cron job or scheduled task:
```bash
# Friday 9:59 AM: 25-hour warning
# Saturday 9:59 AM: 1-hour FINAL warning
0 9 * * 5,6 cd /path/to/project && python send_reminders.py
```

## 🐛 Troubleshooting

### Common Issues

**Database not found**
```bash
python app.py
# Visit http://localhost:5000/init-db
```

**Timezone issues**
- Ensure all datetimes use Chicago timezone (America/Chicago)
- Check that `pytz` is installed correctly

**Import games failing**
- Verify API key in `import_games.py`
- Check API quota at The Odds API dashboard
- Ensure date range includes games with available odds

**Email reminders not sending**
- Use Gmail app-specific passwords, not regular password
- Enable "Less secure app access" or use OAuth2
- Verify SMTP settings in `.env`

## 🚀 Deployment

### PythonAnywhere (Recommended for Free Tier)
1. Create PythonAnywhere account
2. Upload code via Git or Files interface
3. Create virtual environment in Bash console
4. Configure web app with WSGI file
5. Set environment variables
6. Upload production database
7. Reload web app

### Other Platforms
- **Heroku**: Use Postgres instead of SQLite
- **DigitalOcean**: Deploy with gunicorn/nginx
- **AWS EC2**: Use application load balancer

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **The Odds API** for game data and spreads
- **Flask** framework and community
- **Bootstrap** for responsive UI components
- All the participants who make survivor pools fun!

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact the maintainer

## 🗺️ Roadmap

Future enhancements planned:
- [ ] Mobile app version
- [ ] Multiple pool types (confidence, spread, etc.)
- [ ] Real-time WebSocket updates
- [ ] Social features (comments, trash talk)
- [ ] AI-powered pick suggestions
- [ ] Advanced analytics dashboard
- [ ] Team logos integration
- [ ] Historical season archives

## 📊 Stats

- **Lines of Code**: ~5,000+
- **Templates**: 15+
- **Database Tables**: 5 core models
- **Features**: 40+ including admin tools
- **Season Coverage**: Full CFB season + playoffs

---

**Built with ❤️ for college football fans**

*Go support your favorite team... but pick strategically!* 🏈
