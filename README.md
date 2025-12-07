# ChoreBoard

A Django-based household chore management system with points tracking, automated scheduling, and fair assignment algorithms.

## Features

### Core Features
- **Points System**: Earn points for completing chores, convertible to cash weekly
- **Configurable Points Label**: Customize the terminology used for "points" throughout the system (e.g., "stars", "coins", "experience")
- **Smart Scheduling**: Support for daily, weekly, every-N-days, cron, and RRULE schedules
- **Fair Assignment**: Automated rotation for undesirable chores with purple state logic
- **Pool & Fixed Chores**: Pool chores can be claimed; fixed chores assigned to specific users
- **Streak Tracking**: Perfect week bonuses for completing all chores on time
- **Immediate Instance Creation**: Newly created chores appear on the board immediately via Django signals
- **Comprehensive Admin**: Django admin interface for all models and configurations

### Scheduled Jobs (Phase 2 Complete ✅)
- **Midnight Evaluation** (00:00 daily): Creates new chore instances, marks overdue chores, resets daily claims
- **Distribution Check** (17:30 daily): Auto-assigns chores at distribution time
- **Weekly Snapshot** (Sunday 00:00): Creates snapshots for weekly reset and conversion

### Assignment & Rotation Logic (Phase 3 Complete ✅)
- **Smart Assignment**: Selects users based on eligibility, fairness (least assigned today), and constraints
- **Undesirable Rotation**: Tracks last_completed_date, rotates to oldest, skips yesterday completers (purple state)
- **Difficult Constraint**: Prevents assigning two difficult chores to same user on same day
- **Purple States**: Assignment-blocked reasons (no eligible users, all completed yesterday)
- **Dependency Spawning**: Child chores spawn after parent completion with offset_hours
- **Circular Detection**: Prevents circular dependency configurations

### Models (Phase 1 Complete ✅)
- **13 Models**: User, Chore, ChoreInstance, Completion, CompletionShare, PointsLedger, WeeklySnapshot, Streak, Settings, ActionLog, EvaluationLog, ChoreInstanceArchive, RotationState
- **Full Validation**: Soft delete, points snapshotting, database locking for concurrency
- **Admin Configured**: All models registered with custom list displays, filters, and search

### REST API (Phase 4 Complete ✅)
- **HMAC Authentication**: Token-based auth with 24-hour expiry, secure signature validation
- **Chore Operations**: Claim pool chores, complete chores with helper selection, undo completions (admin)
- **Chore Queries**: Late chores, outstanding chores, my chores (assigned to user)
- **Leaderboard**: Weekly and all-time rankings with points tracking
- **Database Locking**: Pessimistic locking for concurrent claims using `select_for_update()`
- **Point Splitting**: Automatic point distribution with rounding (2 decimal places)
- **Integration**: Full integration with assignment service, dependency spawning, and rotation logic

### Frontend UI (Phase 5 Mostly Complete ✅)
- **Dark Theme**: Custom ChoreBoard color palette with Tailwind CSS
- **Main Board**: Stats cards, color-coded chore sections (green/amber/red), interactive cards
- **Pool Page**: View and claim unclaimed chores
- **User Page**: Personalized view with points display and user switcher
- **Leaderboard**: Weekly and all-time rankings with medal icons (🥇🥈🥉)
- **Interactive Dialogs**: Claim and complete modals with helper selection
- **Toast Notifications**: Auto-dismissing success/error messages
- **Accessibility**: WCAG 2.1 Level AA (skip links, ARIA labels, keyboard navigation, focus management)
- **Responsive Design**: Mobile-first approach with grid layouts
- **API Integration**: Full integration with REST API for real-time operations

## Project Status

**Overall Progress**: 36/64 tasks (56%)

- ✅ **Phase 1 Complete**: Project Setup & Models (11/11 tasks)
- ✅ **Phase 2 Complete**: Scheduled Jobs (6/6 tasks)
- ✅ **Phase 3 Complete**: Assignment & Rotation Logic (5/5 tasks)
- ✅ **Phase 4 Complete**: REST API (6/6 tasks)
- ✅ **Phase 5 Mostly Complete**: Frontend UI (8/9 tasks)
- ⏳ **Phase 6**: Admin Features (0/8 tasks)
- ⏳ **Phase 7**: Testing (0/8 tasks)
- ⏳ **Phase 8**: Documentation & Deployment (0/8 tasks)

## Installation

### Requirements
- Python 3.11+
- pip
- Virtual environment (recommended)

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ChoreBoard2
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**:
   - Windows: `.venv\Scripts\activate`
   - Unix/Mac: `source .venv/bin/activate`

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Start development server**:
   ```bash
   python manage.py runserver
   ```

6. **Access the application and complete first-run setup**:
   - Open your browser to http://127.0.0.1:8000
   - The first-run wizard will automatically:
     - Create the database if it doesn't exist
     - Run all migrations
     - Redirect you to the setup wizard
   - Complete the web-based setup form to create your admin account
   - Once created, you'll be logged in and redirected to the main board

**Note**: The first-run wizard only appears when the database is empty (no users exist). After creating your first user, you can access:
- Main board: http://127.0.0.1:8000
- Admin interface: http://127.0.0.1:8000/admin

### Docker Deployment

See [DOCKER.md](DOCKER.md) for detailed Docker deployment instructions.

Quick start:
```bash
docker-compose up -d --build
docker exec -it choreboard python manage.py setup
```

## Usage

### Admin Interface
Access the Django admin at `/admin` to:
- Create and manage users
- Create and configure chores with scheduling
- View chore instances and completions
- Monitor points ledger and weekly snapshots
- View action logs and evaluation logs
- Configure global settings

### Manual Job Triggers
Run scheduled jobs manually for testing:

```bash
# Run midnight evaluation
python manage.py run_midnight_evaluation

# Run distribution check
python manage.py run_distribution_check

# Run weekly snapshot
python manage.py run_weekly_snapshot
```

### Scheduled Jobs
When the server is running, jobs execute automatically:
- **Midnight** (00:00): Creates new chore instances, marks overdue chores
- **Evening** (17:30): Auto-assigns pool chores
- **Sunday** (00:00): Creates weekly snapshots for reset

### Database Reset
Reset the database to a clean state (useful for clearing test/development data):

```bash
# Interactive mode with confirmation prompt
python manage.py reset_database

# Non-interactive mode (use with caution!)
python manage.py reset_database --no-confirm
```

**⚠️ WARNING:** This deletes ALL data (users, chores, completions, logs, settings). The schema is preserved. After reset, run `python manage.py setup` to create your first user. See [RESET_DATABASE.md](RESET_DATABASE.md) for detailed instructions.

## Configuration

### Settings
Configure via Django admin `/admin/core/settings/`:
- **Points to Dollar Rate**: Conversion rate (default: 0.01 = 100 points = $1)
- **Max Claims Per Day**: How many chores users can claim daily (default: 1)
- **Undo Time Limit**: Hours after completion for undo (default: 24)
- **Weekly Reset Undo**: Hours after reset for undo (default: 24)
- **Home Assistant Webhook**: Optional webhook URL for notifications

### Site Settings
Configure via Django admin `/admin/board/sitesettings/`:
- **Points Label**: Full form terminology used throughout the site (default: "points")
- **Points Label Short**: Abbreviated form for compact displays (default: "pts")

**Examples**:
- Gaming theme: "experience" / "xp"
- Financial theme: "coins" / "$"
- Achievement theme: "stars" / "★"

Changes to these labels update immediately across all pages and displays.

### Environment Variables
Copy `.env.example` to `.env` and customize:
- `SECRET_KEY`: Django secret key (change in production!)
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_PATH`: Path to SQLite database (for Docker)
- `TZ`: Timezone (default: America/Chicago)

## API Documentation

### Authentication

All API endpoints use HMAC token authentication with 24-hour expiry.

**Token Format**: `username:timestamp:signature`
- Signature: HMAC-SHA256(username:timestamp, SECRET_KEY)
- Include in header: `Authorization: Bearer <token>`
- Or as query param: `?token=<token>`

**Generate Token** (in Django shell or management command):
```python
from api.auth import HMACAuthentication
token = HMACAuthentication.generate_token('username')
```

### API Endpoints

**Base URL**: `/api/`

#### Chore Operations

**Claim a Pool Chore** - `POST /api/claim/`
```json
{
  "instance_id": 123
}
```
- Requires authentication
- Enforces daily claim limit (1 per day by default)
- Uses database locking to prevent race conditions
- Returns: ChoreInstance with updated status

**Complete a Chore** - `POST /api/complete/`
```json
{
  "instance_id": 123,
  "helper_ids": [1, 2, 3]  // Optional
}
```
- Requires authentication
- Splits points among helpers (or completer if none specified)
- Creates Completion, CompletionShare, and PointsLedger records
- Spawns dependent chores if configured
- Updates rotation state for undesirable chores
- Returns: Completion with shares and spawned child count

**Undo a Completion** - `POST /api/undo/` (Admin Only)
```json
{
  "completion_id": 123
}
```
- Requires admin privileges
- Enforces 24-hour undo window
- Restores ChoreInstance to previous state
- Reverses point awards
- Returns: Restored ChoreInstance

#### Chore Queries

**Get Late Chores** - `GET /api/late-chores/`
- Returns all overdue chores (not completed, past due date)
- Includes chore details and assigned user

**Get Outstanding Chores** - `GET /api/outstanding/`
- Returns non-overdue, non-completed chores
- Sorted by due date

**Get My Chores** - `GET /api/my-chores/`
- Returns chores assigned to authenticated user for today
- Sorted by due date

#### Leaderboard

**Get Leaderboard** - `GET /api/leaderboard/?type=weekly`
- Query params:
  - `type=weekly` - Weekly points (default)
  - `type=alltime` - All-time points
- Returns ranked list with user, points, and rank

### Example Usage

```python
import requests

# Generate token (in Django shell)
from api.auth import HMACAuthentication
token = HMACAuthentication.generate_token('john')

# Make API request
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/api/my-chores/', headers=headers)
chores = response.json()

# Claim a chore
response = requests.post(
    'http://localhost:8000/api/claim/',
    headers=headers,
    json={'instance_id': 123}
)

# Complete a chore with helpers
response = requests.post(
    'http://localhost:8000/api/complete/',
    headers=headers,
    json={'instance_id': 123, 'helper_ids': [1, 2]}
)
```

### Testing the API

Run the comprehensive test suite:
```bash
python test_api.py
```

The test suite covers:
- All endpoints (claim, complete, undo, queries, leaderboard)
- HMAC authentication (valid, invalid, missing tokens)
- Point splitting and calculation
- Database locking and concurrency
- Error handling and validation

## Project Structure

```
ChoreBoard2/
├── chores/          # Chore models and admin
├── core/            # Core models, scheduler, and jobs
├── users/           # User model
├── api/             # REST API (Phase 4)
├── planning/        # Documentation and requirements
├── templates/       # HTML templates (Phase 5)
├── staticfiles/     # Static assets
├── manage.py        # Django management
├── requirements.txt # Python dependencies
├── Dockerfile       # Docker image
├── docker-compose.yml
└── README.md        # This file
```

## Development

### Models Overview
- **User**: Custom user with points tracking, claims counter, eligibility flags
- **Chore**: Template with schedule (daily/weekly/every-n/cron/rrule)
- **ChoreInstance**: Daily instance with status (pool/assigned/completed)
- **Completion**: Records who completed, with undo tracking
- **PointsLedger**: Immutable audit trail of all point transactions
- **WeeklySnapshot**: Weekly summary for conversion to cash
- **Streak**: Perfect week streak tracking per user

### Key Design Decisions
- **Point Values**: Snapshotted at ChoreInstance creation (not live from template)
- **Rounding**: Accept loss in point splits (e.g., 10/3 = 3.33 each = 9.99 total)
- **Concurrency**: Uses `select_for_update()` for claims and completions
- **Deletion**: Soft delete (`is_active=False`) for chores and users
- **Data Retention**: 1 year active, archive older records
- **Accessibility**: WCAG 2.1 Level AA target

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_models.py
```

### Manual Testing
```bash
# Test models
python test_all_models.py

# Test scheduled jobs
python manage.py run_midnight_evaluation
```

## Contributing

1. Follow existing code style and patterns
2. Write tests for new features
3. Update documentation
4. Test thoroughly before committing

## License

[Add license information]

## Support

For issues or questions:
- Check the planning documentation in `/planning`
- Review the Implementation Tasks for current status
- See [DOCKER.md](DOCKER.md) for deployment help

---

**Last Updated**: 2025-12-07
**Phase Status**: 7/8 phases mostly complete (Phases 1-7)
**Next Up**: Phase 8 - Documentation & Deployment
