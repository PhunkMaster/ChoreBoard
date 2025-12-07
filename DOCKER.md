# ChoreBoard Docker Deployment

## Quick Start

1. **Build and start the container:**
   ```bash
   docker-compose up -d --build
   ```

2. **Create admin user (first time only):**
   ```bash
   docker exec -it choreboard python manage.py setup
   ```

3. **Access the application:**
   - Admin interface: http://localhost:8000/admin
   - API endpoints: http://localhost:8000/api/

## Volume Mounts

The following directories are mounted for data persistence:
- `./data` - Database and uploaded files
- `./staticfiles` - Static assets

## Environment Variables

Copy `.env.example` to `.env` and customize:
- `SECRET_KEY` - Django secret key (change in production!)
- `DEBUG` - Set to False in production
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DATABASE_PATH` - Path to SQLite database

## Useful Commands

**View logs:**
```bash
docker-compose logs -f
```

**Stop container:**
```bash
docker-compose down
```

**Restart container:**
```bash
docker-compose restart
```

**Run migrations:**
```bash
docker exec -it choreboard python manage.py migrate
```

**Access Django shell:**
```bash
docker exec -it choreboard python manage.py shell
```

**Backup database:**
```bash
docker cp choreboard:/app/data/db.sqlite3 ./backup_$(date +%Y%m%d).sqlite3
```

**Restore database:**
```bash
docker cp ./backup.sqlite3 choreboard:/app/data/db.sqlite3
docker-compose restart
```

## Production Deployment

For production:
1. Set `DEBUG=False` in .env
2. Generate a secure `SECRET_KEY`
3. Update `ALLOWED_HOSTS` with your domain
4. Use a reverse proxy (nginx) for SSL/TLS
5. Set up regular database backups

