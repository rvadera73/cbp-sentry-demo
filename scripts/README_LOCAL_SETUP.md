# CBP Sentry - Local Development Setup

Complete guide for setting up and running CBP Sentry locally using Docker Compose.

## Quick Start

```bash
# One-command startup (builds, starts services, runs tests)
./scripts/local_startup.sh

# Or with full rebuild
./scripts/local_startup.sh clean
```

After startup completes:
- **UI**: http://localhost:3001
- **API**: http://localhost:8000
- **Data Service**: http://localhost:8005

## Scripts Overview

### 1. `local_startup.sh` - Full Deployment
Complete local deployment with Docker image building, service startup, and health checks.

**Usage:**
```bash
./scripts/local_startup.sh           # Start/restart services (reuse images)
./scripts/local_startup.sh clean     # Full rebuild (clean images)
```

**What it does:**
1. ✓ Verifies Docker is installed
2. ✓ Stops existing containers (preserves volumes)
3. ✓ Builds all Docker images (sentry-data, sentry-api, sentry-ui)
4. ✓ Starts services with docker-compose
5. ✓ Waits for all services to reach healthy state (max 120s)
6. ✓ Runs smoke tests (API endpoints, data loading)
7. ✓ Reports final status

**Output:**
```
=== CBP Sentry Local Startup ===
... (detailed setup logs) ...
✓ All smoke tests passed (3/3)
✓ CBP Sentry is running locally
```

### 2. `local_test.sh` - Integration Testing
Comprehensive integration tests for all services.

**Usage:**
```bash
./scripts/local_test.sh
```

**Tests include:**
- ✓ Sentry-Data API endpoints and data fields
- ✓ Sentry-API enrichment layers
- ✓ UI static asset serving
- ✓ Service-to-service communication (via bridge network)
- ✓ Container health status

**Output:**
```
=== Test: Sentry-Data API - GET /shipments ===
✓ Found 50 shipments
✓ First shipment ID: SHP-000211
✓ Shipment has risk_score: 95.0

... (more tests) ...

✓ All tests passed (15/15)
```

### 3. `setup_database.sh` - Database Management
Database initialization, backup, restore, and verification.

**Usage:**
```bash
# Setup and seed local database
./scripts/setup_database.sh local

# Create backup of current database
./scripts/setup_database.sh backup local

# Restore from backup
./scripts/setup_database.sh restore ./backups/cbp_sentry_local_20260520_082212.db

# Verify database contains data
./scripts/setup_database.sh verify local

# Export database for staging/production
./scripts/setup_database.sh export
```

**Available commands:**
| Command | Purpose |
|---------|---------|
| `local` | Set up and seed local database |
| `backup [local]` | Create database backup |
| `restore <file>` | Restore from backup file |
| `verify [local]` | Verify database has data |
| `export` | Export for other environments |

## Architecture

### Services
- **sentry-data** (port 8005): FastAPI service for database CRUD operations
  - SQLite database at `/app/data/cbp_sentry.db`
  - Auto-seeds on startup from `services/data/seed_data/manifest_feb_march_2026_with_isf.json`
  - HTTP-only on bridge network, no auth needed locally

- **sentry-api** (port 8000): FastAPI gateway and business logic
  - Enriches shipment data (adds H1/H2 scores, entity resolution)
  - Routes requests to sentry-data
  - Uses bridge network to communicate with sentry-data

- **sentry-ui** (port 3001): React SPA + Nginx
  - Built with Vite, served by Nginx
  - Detects API URL based on hostname (localhost vs Cloud Run)
  - API calls routed through React → Nginx → sentry-api

### Network
All services on `sentry-network` bridge:
- `sentry-ui` → `sentry-api` (via localhost:8000 on host, via hostname on bridge)
- `sentry-api` → `sentry-data` (via hostname sentry-data:8005)

### Volumes
Only data persists across restarts:
- `sentry_data_volume` → `/app/data` in sentry-data container

Source code is NOT mounted (Docker image contains everything).

## Common Tasks

### Check Service Status
```bash
docker compose ps
```

### View Service Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f sentry-api

# Last 100 lines of sentry-data
docker compose logs sentry-data --tail 100
```

### Test API Endpoint
```bash
# List shipments
curl http://localhost:8005/shipments | head -c 200

# Get enriched shipments through API
curl http://localhost:8000/api/shipments | head -c 200
```

### Restart a Service
```bash
docker compose restart sentry-api
```

### Stop All Services (preserve data)
```bash
docker compose down
```

### Clean Everything (start fresh)
```bash
docker compose down -v  # Remove volumes too
./scripts/local_startup.sh clean
```

## Database Seeding

### Automatic Seeding
On first startup, `sentry-data` automatically seeds from:
```
services/data/seed_data/manifest_feb_march_2026_with_isf.json
```

Check logs to verify:
```bash
docker compose logs sentry-data | grep -i "seed\|shipments"
```

### Manual Reseed
```bash
./scripts/setup_database.sh local
```

This will:
1. Backup current database
2. Restart sentry-data service
3. Verify new seeding worked

## Backup and Export

### Create Backup
```bash
./scripts/setup_database.sh backup local

# Backup saved to: backups/cbp_sentry_local_YYYYMMDD_HHMMSS.db
```

### Export for Staging
```bash
./scripts/setup_database.sh export

# Check available backups
ls -lh backups/*.db
```

### Restore from Backup
```bash
# List available backups
ls -lh backups/

# Restore specific backup
./scripts/setup_database.sh restore backups/cbp_sentry_local_20260520_082212.db
```

## Troubleshooting

### Services Not Starting
```bash
# Check detailed logs
docker compose logs

# Verify Docker daemon is running
docker ps

# Check available disk space
df -h
```

### Port Already in Use
```bash
# Kill process on specific port
lsof -i :3001
kill -9 <PID>

# Then restart
./scripts/local_startup.sh
```

### Database Empty
```bash
# Verify database has data
./scripts/local_test.sh

# Reseed if empty
./scripts/setup_database.sh local

# Check seed file exists
ls -l services/data/seed_data/manifest_feb_march_2026_with_isf.json
```

### API Not Responding
```bash
# Check service health
curl -v http://localhost:8000/api/shipments

# Check service logs
docker compose logs sentry-api | tail -50

# Restart service
docker compose restart sentry-api
```

### UI Not Accessible
```bash
# Check nginx logs
docker compose logs sentry-ui | tail -50

# Verify Nginx process
docker compose exec sentry-ui ps aux | grep nginx

# Check UI assets were built
docker compose exec sentry-ui ls -la /usr/share/nginx/html/
```

## Integration with GitHub Actions

For CI/CD on remote server:
1. SSH into server
2. Pull latest code: `git pull origin main`
3. Run startup script: `./scripts/local_startup.sh clean`
4. Run tests: `./scripts/local_test.sh`

## Performance Notes

- First build (with `clean`): ~2-3 minutes (downloads base images, builds all services)
- Subsequent starts: ~30 seconds (reuses cached images)
- Service health checks: ~15-30 seconds (depends on system load)
- Database seeding: ~10 seconds (depends on JSON file size)

## Next Steps

- **Local testing complete?** → Push to GitHub to trigger Cloud Run staging deployment
- **Need to debug API?** → Check `docker compose logs sentry-api`
- **Database issues?** → Use `./scripts/setup_database.sh` commands
- **Port conflicts?** → Modify docker-compose.yml ports section

## Support

For issues, check:
1. Docker Compose logs: `docker compose logs`
2. Service logs: `docker compose logs <service>`
3. GitHub Actions logs: https://github.com/your-repo/actions
4. Test output: `./scripts/local_test.sh`
