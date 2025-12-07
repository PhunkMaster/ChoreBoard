#!/bin/bash
set -e

echo "Starting ChoreBoard..."

# Wait for database to be ready (if using external DB in future)
echo "Checking database connection..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Initialize settings if needed
echo "Initializing application settings..."
python manage.py shell << EOF
from core.models import Settings
settings = Settings.get_settings()
print(f"Settings initialized: Points rate = {settings.points_to_dollar_rate}")
EOF

echo "ChoreBoard startup complete!"

# Execute the main command
exec "$@"
