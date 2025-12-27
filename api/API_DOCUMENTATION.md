# ChoreBoard API Documentation

## Accessing the API Documentation

The ChoreBoard API provides interactive documentation through Swagger UI and ReDoc.

### Swagger UI (Interactive)
**URL:** `http://localhost:8000/api/index.html`

The Swagger UI provides:
- Interactive API testing
- Request/response examples
- Schema definitions
- Try-it-out functionality for all endpoints

### ReDoc (Alternative Documentation)
**URL:** `http://localhost:8000/api/redoc/`

ReDoc provides a clean, three-panel documentation layout.

### OpenAPI Schema
**URL:** `http://localhost:8000/api/schema/`

Raw OpenAPI 3.0 schema in YAML format.

## API Endpoints

### Actions (Require Authentication)

- `POST /api/claim/` - Claim a pool chore
- `POST /api/complete/` - Complete a chore with optional helpers
- `POST /api/undo/` - Undo a completion (admin only)

### Chores (No Authentication Required)

- `GET /api/late-chores/` - Get all overdue chores
- `GET /api/outstanding/` - Get all outstanding chores
- `GET /api/my-chores/` - Get chores assigned to authenticated user (empty if not authenticated)

### Leaderboard (No Authentication Required)

- `GET /api/leaderboard/` - Get leaderboard rankings
  - Query param: `?type=weekly` (default) or `?type=alltime`

## Authentication

### HMAC Authentication

POST endpoints require HMAC authentication with a Bearer token:

```
Authorization: Bearer username:timestamp:signature
```

**Generate token using Python:**
```python
from api.auth import HMACAuthentication
token = HMACAuthentication.generate_token('username')
```

**Use in request:**
```bash
curl -X POST http://localhost:8000/api/claim/ \
  -H "Authorization: Bearer username:timestamp:signature" \
  -H "Content-Type: application/json" \
  -d '{"instance_id": 123}'
```

### No Authentication for GET Endpoints

All GET endpoints work without authentication, but can accept authentication for personalized results (e.g., `my-chores` returns user's chores when authenticated, empty list otherwise).

## Testing the API

1. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

2. **Open Swagger UI:**
   Navigate to `http://localhost:8000/api/index.html`

3. **Try an unauthenticated endpoint:**
   - Click on `GET /api/leaderboard/`
   - Click "Try it out"
   - Click "Execute"
   - View the response

4. **Try an authenticated endpoint:**
   - Generate an HMAC token for your user
   - Click the "Authorize" button in Swagger UI
   - Enter `Bearer your_token_here`
   - Try the `POST /api/claim/` endpoint

## Response Format

All API responses return JSON:

```json
{
  "message": "Success message",
  "data": { ... }
}
```

Error responses:
```json
{
  "error": "Error message"
}
```

## Rate Limiting

Currently no rate limiting is implemented.

## API Versioning

Current version: **1.0.0**

API version is included in the OpenAPI schema but not in the URL path.

## Schema Definitions

### Chore Schema

The Chore object represents a task template with the following key fields:

- `id` (integer): Unique chore identifier
- `name` (string): Name of the chore
- `description` (string): Optional description
- `points` (decimal): Points awarded for completion
- `is_pool` (boolean): If true, chore is available in the pool; if false, assigned to specific user
- `is_difficult` (boolean): Indicates if chore is marked as difficult
- `is_undesirable` (boolean): Indicates if chore is marked as undesirable
- `is_late_chore` (boolean): Indicates if chore is considered a late chore
- **`complete_later` (boolean)**: If true, this chore can be completed later in the day (e.g., "Clean Kitchen After Dinner"). If false, it should be completed immediately (e.g., "Make Your Bed"). External systems can use this to determine if a user has completed all immediate chores for restriction management.
- `schedule_type` (string): Type of schedule (DAILY, WEEKLY, etc.)

### ChoreInstance Schema

The ChoreInstance object represents a specific occurrence of a chore:

- `id` (integer): Unique instance identifier
- `chore` (Chore): Nested Chore object (includes `complete_later` field)
- `assigned_to` (User): User assigned to this chore (null if in pool)
- `status` (string): Current status (POOL, ASSIGNED, COMPLETED, etc.)
- `points_value` (decimal): Points for this specific instance
- `due_at` (datetime): When the chore is due
- `is_overdue` (boolean): Whether the chore is overdue
- `completed_at` (datetime): When the chore was completed (null if not completed)

## Use Case: Restriction Management

The `complete_later` field enables external restriction management systems (e.g., parental control apps) to determine if a user has completed their immediate responsibilities:

**Example Logic:**
```python
# Get user's assigned chores
response = requests.get('http://localhost:8000/api/my-chores/',
                        headers={'Authorization': f'Bearer {token}'})
my_chores = response.json()

# Filter immediate chores (complete_later = false)
immediate_chores = [c for c in my_chores if not c['chore']['complete_later']]

# Check if all immediate chores are complete
incomplete_immediate = [c for c in immediate_chores if c['status'] != 'COMPLETED']

if len(incomplete_immediate) == 0:
    # Remove restrictions (allow screen time, activities, etc.)
    print("All immediate chores complete - restrictions lifted!")
else:
    # Keep restrictions in place
    print(f"{len(incomplete_immediate)} immediate chores remaining")
```

This allows for intelligent restriction systems that don't penalize users for chores that legitimately cannot be done until later in the day.
