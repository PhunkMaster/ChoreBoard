# ChoreBoard

**A smart household chore management system that makes chores fair, fun, and rewarding.**

ChoreBoard helps families and roommates manage household chores with a points-based reward system, automated scheduling,
and fair task rotation. Turn chores into a game where everyone knows what needs to be done and gets rewarded for their
contributions!

---

## Disclaimer

- ChoreBoard is provided "as is" without warranty of any kind, express or implied. Use at your own risk. Always consult
  with a professional before making any changes to your household management system.
- ChoreBoard was created with the help of ClaudeCode (AI). If you have moral opposition to using software created by AI,
  please do not use this.

---

## ✨ What is ChoreBoard?

ChoreBoard is a web-based chore management system designed to:

- **Make chores fair** - Automated rotation ensures everyone gets their turn at undesirable tasks
- **Make chores rewarding** - Earn points for completing chores, convertible to cash weekly
- **Make chores visible** - Real-time board shows what needs to be done and who's responsible
- **Make chores automatic** - Smart scheduling creates chores daily, weekly, or on custom schedules

### Key Features

🎯 **Points & Rewards**

- Earn points for completing chores
- Convert points to cash weekly (customizable rate)
- Streak bonuses for perfect weeks

📋 **Smart Scheduling**

- Daily, weekly, every-N-days, or custom (cron/RRULE) schedules
- One-time tasks for non-recurring work
- Automatic chore creation and assignment
- Fair rotation for undesirable tasks

🏆 **Gamification**

- Weekly and all-time leaderboards
- Streak tracking with bonuses
- Real-time updates

👥 **Household Management**

- Multiple users with different roles
- Pool chores anyone can claim
- Fixed chores assigned to specific people
- Admin panel for easy management

🔔 **Notifications**

- Optional webhook notifications to Home Assistant
- Track overdue chores and achievements
- Weekly reset notifications

---

## 🚀 Quick Start

### Installation (5 minutes)

1. **Download ChoreBoard**
   ```bash
   git clone <repository-url>
   cd ChoreBoard2
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv

   # On Windows:
   .venv\Scripts\activate

   # On Mac/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start ChoreBoard**
   ```bash
   python manage.py runserver
   ```

5. **Open your browser and visit:**
   ```
   http://localhost:8000
   ```

That's it! ChoreBoard will automatically:

- Create the database
- Run all necessary setup
- Show you a welcome wizard to create your admin account

### First-Run Setup

When you first visit ChoreBoard, you'll see a setup wizard that guides you through:

1. **Create Admin Account** - Set up your administrator account
2. **Configure Settings** - Set points conversion rate and other preferences
3. **Create Users** - Add household members
4. **Create Chores** - Set up your household chores with schedules and point values

After setup, you're ready to start using ChoreBoard!

---

## 📖 Documentation

Complete guides for using and managing ChoreBoard:

### 👤 For Household Members

- **[User Guide](docs/USER_GUIDE.md)** - How to view, claim, and complete chores
    - Understanding the main board
    - Claiming chores from the pool
    - Completing chores and earning points
    - Viewing your points and streaks

### 👨‍💼 For Administrators

- **[Admin Guide](docs/ADMIN_GUIDE.md)** - How to manage ChoreBoard
    - Creating and managing users
    - Setting up chores and schedules
    - Weekly reset and points conversion
    - System settings and customization
    - Notifications and webhooks
- **[Schedule Reference](docs/SCHEDULE_REFERENCE.md)** - Quick reference for CRON and RRULE schedules
    - CRON syntax and examples
    - RRULE JSON format and examples
    - Common patterns and troubleshooting

### 🐳 Deployment & Advanced

- **[Docker Deployment](docs/DOCKER.md)** - Deploy with Docker for production use
- **[Database Reset](docs/RESET_DATABASE.md)** - Reset database to start fresh
- **[All Documentation](docs/)** - Browse all documentation files

---

## 💡 How It Works

### Daily Flow

1. **Morning** - ChoreBoard automatically creates today's chores based on schedules
2. **Throughout the day** - Household members view the board, claim, and complete chores
3. **Evening** (5:30 PM) - Unclaimed chores are automatically assigned fairly
4. **Midnight** - Points are awarded, chores marked overdue, new day begins

### Weekly Flow

1. **During the week** - Complete chores, earn points, build streaks
2. **Sunday midnight** - Weekly reset happens automatically:
    - Weekly points are converted to cash (e.g., 100 points = $1)
    - Streaks are updated (perfect week = bonus!)
    - Points reset for the new week
    - All-time points continue accumulating

### Chore Types

- **Pool Chores** - First-come, first-served. Anyone can claim these.
- **Fixed Chores** - Assigned to specific people automatically
- **Undesirable Chores** - Rotate fairly among eligible household members

---

## 🎮 Using ChoreBoard

### Main Board

View all chores at a glance:

- 🟢 **On Time** - Chores due today or later
- 🟡 **Getting Late** - Due within 4 hours
- 🔴 **Overdue** - Past due date

### Pool Page

Browse unclaimed chores and claim the ones you want to do.

### User Pages

View your personal stats:

- Weekly and all-time points
- Current streak
- Your assigned chores
- Leaderboard ranking

### Admin Panel

Manage everything:

- Create and edit chores
- Manage users
- Adjust points manually
- View logs and backups
- Configure system settings

---

## 🔧 Configuration

### System Settings

Access via Admin Panel → Settings:

- **Points Conversion Rate** - How many points equal $1 (default: 100 points = $1)
- **Daily Claim Limit** - How many pool chores users can claim per day (default: 1)
- **Points Label** - Customize what points are called (e.g., "stars", "coins")
- **Webhook Notifications** - Optional Home Assistant integration

### Customization

ChoreBoard is highly customizable:

- Custom chore schedules (cron expressions, RRULE patterns)
- Flexible point values per chore
- Configurable rotation rules
- Custom points terminology
- Timezone support

---

## 🐳 Docker Deployment

For production use, deploy ChoreBoard with Docker:

### Using Pre-built Images

Pre-built Docker images are available from GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/YOUR_USERNAME/choreboard2:latest

# Or use a specific version
docker pull ghcr.io/YOUR_USERNAME/choreboard2:v1.0.0
```

### Building from Source

```bash
docker-compose up -d --build
docker exec -it choreboard python manage.py setup
```

See [Docker Deployment Guide](docs/DOCKER.md) for detailed instructions.

---

## 🔄 Resetting the Database

To start fresh and clear all data:

```bash
python manage.py reset_database
```

This will delete all users, chores, and points while keeping the database structure intact. Perfect for testing or
starting over.

**⚠️ Warning:** This is irreversible! See [Database Reset Guide](docs/RESET_DATABASE.md) for details.

---

## 📊 Project Status

ChoreBoard is feature-complete and production-ready!

- ✅ Core chore management
- ✅ Points and rewards system
- ✅ Smart scheduling and assignment
- ✅ Web interface with real-time updates
- ✅ Admin panel for easy management
- ✅ REST API
- ✅ Webhook notifications
- ✅ Docker deployment
- ✅ Comprehensive documentation

---

## 🆘 Support & Help

### Getting Help

1. **Documentation** - Check the [docs folder](docs/) for detailed guides
2. **User Guide** - See [USER_GUIDE.md](docs/USER_GUIDE.md) for basic usage
3. **Admin Guide** - See [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) for management

### Common Issues

**Chores not appearing?**

- Check if the chore is active (Admin Panel → Chores)
- Verify the schedule is correct
- Run midnight evaluation: `python manage.py run_midnight_evaluation`

**Points not calculating correctly?**

- Check the points value on the chore
- Verify completion shares (did you add helpers?)
- Review the points ledger (Admin Panel → Logs)

**Need to start over?**

- Use the database reset: `python manage.py reset_database`
- See [Database Reset Guide](docs/RESET_DATABASE.md)

---

## ⚠️ Database Recommendations

**For Development & Single User:**
- ✅ SQLite (included, no setup required)
- Perfect for testing, personal use, or households with 1-2 users

**For Production & Multiple Users:**
- ⚠️ **SQLite has concurrency limitations** - Not recommended for production with 3+ concurrent users
- ✅ **Use PostgreSQL** for multi-user production deployments
- PostgreSQL provides proper database locking and handles concurrent claims/completions safely

**Why PostgreSQL for production?**

ChoreBoard uses database-level row locking (`select_for_update()`) to prevent race conditions when multiple users:
- Claim the same pool chore simultaneously
- Complete chores at the same time
- Access the weekly snapshot feature concurrently

SQLite's limited concurrency support means these protections may not work correctly with multiple simultaneous users, potentially causing:
- Database lock errors ("database table is locked")
- Duplicate claims or completions
- Data integrity issues

**Production Setup:**

For production deployments with multiple users, use PostgreSQL:
1. Install PostgreSQL
2. Update `DATABASES` in `ChoreBoard/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'choreboard',
           'USER': 'your_db_user',
           'PASSWORD': 'your_db_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```
3. Run migrations: `python manage.py migrate`

---

## 🛠️ Technical Details

**Built with:**

- Python 3.11+ & Django 4.2
- SQLite database (development/single-user) or PostgreSQL (production/multi-user)
- Tailwind CSS for beautiful, responsive UI
- REST API with HMAC authentication
- APScheduler for automated jobs

**Requirements:**

- Python 3.11 or higher
- ~50 MB disk space
- Works on Windows, Mac, and Linux
- PostgreSQL recommended for production with 3+ concurrent users

---

## 📝 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

**Key Points:**
- ✅ Free to use, modify, and distribute
- ✅ Must share source code of any modifications
- ✅ Network use requires source sharing (if you run ChoreBoard as a web service with modifications, you must share your changes)
- ✅ Patent protections included
- ✅ All derivatives must use AGPL-3.0

See the [LICENSE](LICENSE) file for full details.

**Why AGPL?** ChoreBoard uses AGPL-3.0 to ensure that improvements to the project benefit the entire community, even when deployed as a web service.

---

## 🙏 Acknowledgments

ChoreBoard was designed to make household chores fair, transparent, and rewarding for families and roommates.

**Made with ❤️ for busy households everywhere.**

---

**Questions? Check out the [documentation](docs/) or the detailed [Admin Guide](docs/ADMIN_GUIDE.md)!**