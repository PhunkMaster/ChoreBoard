# ChoreBoard CI/CD Workflows

This directory contains GitHub Actions workflows for automated testing, building, and deployment.

## Workflows

### `docker-build-push.yml` - Docker Build and Push

Automatically builds and publishes Docker images to GitHub Container Registry (ghcr.io).

#### Triggers

- **Push to `main` branch** - Builds and pushes with `latest` and `main` tags
- **Git tags** (`v*.*.*`) - Builds and pushes with version tags (e.g., `v1.0.0`, `1.0.0`, `1.0`, `1`)
- **Pull requests** - Builds only (no push) to verify the image builds successfully
- **Manual dispatch** - Can be triggered manually from GitHub Actions UI

#### Jobs

##### 1. Test Job
- Runs on every trigger (push, PR, tag)
- Sets up Python 3.11 environment
- Installs dependencies from `requirements.txt`
- Runs Django migrations
- Executes full test suite with `python manage.py test`
- **Must pass** before build jobs run

##### 2. Build and Push Job
- Runs after tests pass
- Only runs for pushes to `main` and git tags (not PRs)
- Uses Docker Buildx for advanced building features
- Implements layer caching using GitHub Actions cache
- Builds for `linux/amd64` platform
- Adds OCI image metadata (labels)
- Pushes to GitHub Container Registry

**Image tags generated:**
- `main` - Latest commit on main branch
- `latest` - Only on main branch pushes
- `v1.0.0`, `1.0.0`, `1.0`, `1` - Semantic version tags from git tags
- `main-abc1234` - Branch name with commit SHA

##### 3. Build PR Job
- Runs after tests pass
- Only runs for pull requests
- Builds the Docker image without pushing
- Verifies the image builds successfully
- Uses layer caching for faster builds

##### 4. Vulnerability Scan Job
- Runs after successful build and push
- Only runs for main branch and tags (not PRs)
- Uses Trivy to scan the published image for vulnerabilities
- Checks for CRITICAL and HIGH severity issues
- Uploads results to GitHub Security tab in SARIF format
- Helps identify security issues before deployment

## Image Tags

Published images follow this tagging strategy:

### Main Branch
- `ghcr.io/YOUR_USERNAME/choreboard2:latest` - Latest stable build
- `ghcr.io/YOUR_USERNAME/choreboard2:main` - Latest main branch
- `ghcr.io/YOUR_USERNAME/choreboard2:main-abc1234` - Specific commit

### Version Tags (from git tags)
When you push a tag like `v1.2.3`, these images are created:
- `ghcr.io/YOUR_USERNAME/choreboard2:v1.2.3` - Full version with v prefix
- `ghcr.io/YOUR_USERNAME/choreboard2:1.2.3` - Full version without v
- `ghcr.io/YOUR_USERNAME/choreboard2:1.2` - Major.minor
- `ghcr.io/YOUR_USERNAME/choreboard2:1` - Major only
- `ghcr.io/YOUR_USERNAME/choreboard2:latest` - Also tagged as latest

This allows users to pin to specific versions or always use the latest.

## Usage

### Pulling Images

```bash
# Latest stable
docker pull ghcr.io/YOUR_USERNAME/choreboard2:latest

# Specific version
docker pull ghcr.io/YOUR_USERNAME/choreboard2:1.0.0

# Latest from main (may be unstable)
docker pull ghcr.io/YOUR_USERNAME/choreboard2:main
```

### Creating a Release

1. **Commit your changes to main:**
   ```bash
   git add .
   git commit -m "Release v1.0.0"
   git push origin main
   ```

2. **Create and push a version tag:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **GitHub Actions will automatically:**
   - Run all tests
   - Build the Docker image
   - Push with version tags (`v1.0.0`, `1.0.0`, `1.0`, `1`, `latest`)
   - Scan for vulnerabilities
   - Publish to ghcr.io

4. **Create a GitHub Release** (optional but recommended):
   - Go to GitHub → Releases → "Draft a new release"
   - Select the tag you created
   - Add release notes
   - Publish

## Permissions

The workflow requires these permissions (automatically granted):
- `contents: read` - Read repository contents
- `packages: write` - Push to GitHub Container Registry
- `security-events: write` - Upload security scan results

## Secrets

No additional secrets needed! The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions.

## Performance Features

### Docker Layer Caching
- Uses GitHub Actions cache to store Docker layers
- Significantly speeds up builds (especially for unchanged dependencies)
- Cache is shared between all builds

### Parallel Jobs
- Tests and builds run in parallel when possible
- PR builds don't wait for vulnerability scans

## Security Features

### Trivy Vulnerability Scanning
- Scans images for known vulnerabilities
- Checks for CRITICAL and HIGH severity issues
- Results visible in GitHub Security tab
- Runs on every main branch and tag build

### Image Metadata
- All images include OCI-compliant labels:
  - Creation date
  - Version information
  - Git commit SHA
  - Source repository
  - Documentation links

## Monitoring

### Viewing Workflow Runs
1. Go to GitHub → Actions tab
2. Select "Build and Push Docker Image" workflow
3. View run history, logs, and status

### Checking Image Vulnerabilities
1. Go to GitHub → Security tab
2. Select "Code scanning alerts"
3. Filter by "Trivy" to see image scan results

### Available Images
1. Go to GitHub → Packages
2. Select "choreboard2"
3. View all published tags and metadata

## Troubleshooting

### Build Fails on Tests
- Check the test job logs in GitHub Actions
- Run tests locally: `python manage.py test`
- Fix failing tests and push again

### Build Fails on Docker Build
- Check for syntax errors in Dockerfile
- Verify all files are committed
- Try building locally: `docker build -t test .`

### Image Not Appearing
- Ensure the workflow completed successfully
- Check package visibility settings (should be public)
- Verify you're looking at the correct registry (ghcr.io)

### Vulnerability Scan Failures
- Check Security tab for details
- High/Critical vulnerabilities may need dependency updates
- Update `requirements.txt` and rebuild

## Local Testing

Test the workflow locally before pushing:

```bash
# Run tests
python manage.py test

# Build Docker image
docker build -t choreboard2:local .

# Run the container
docker run -p 8000:8000 choreboard2:local

# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image choreboard2:local
```
