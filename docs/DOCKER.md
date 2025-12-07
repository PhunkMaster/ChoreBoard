# ChoreBoard Docker Deployment

## Pre-built Docker Images

Pre-built Docker images are automatically built and published to GitHub Container Registry on every release.

### Available Tags

- `latest` - Latest stable release from main branch
- `v1.0.0`, `1.0.0`, `1.0`, `1` - Specific version tags
- `main` - Latest commit from main branch (may be unstable)

### Using Pre-built Images

1. **Pull the image:**
   ```bash
   docker pull ghcr.io/YOUR_USERNAME/choreboard2:latest
   ```

2. **Update docker-compose.yml to use pre-built image:**
   ```yaml
   services:
     choreboard:
       image: ghcr.io/YOUR_USERNAME/choreboard2:latest
       # Remove the 'build' section
   ```

3. **Start the container:**
   ```bash
   docker-compose up -d
   ```

4. **Create admin user (first time only):**
   ```bash
   docker exec -it choreboard python manage.py setup
   ```

5. **Access the application:**
   - Web interface: http://localhost:8000

## Building from Source

If you prefer to build the image locally:

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

