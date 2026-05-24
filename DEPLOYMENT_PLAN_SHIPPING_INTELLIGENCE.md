# Deployment Plan: Shipping Intelligence with Schema Migration

## Problem Analysis

**Local Error**: "Failed to fetch corridors: Not Found" (404)

**Root Cause**: When deploying schema changes, the database initialization and seed data must be executed in the correct order:
1. Database schema (tables) created
2. Seed data loaded
3. API endpoints available

**Why It Fails Without Proper Sequence**:
- Docker images may use cached layers
- Database volume may persist old schema without new tables
- Seed function may not execute if conditions aren't met

---

## Local Deployment Fix

### Prerequisites
- Docker & docker-compose installed
- All code changes committed locally
- Seed data file exists: `services/data/seed_data/corridors_seed.json`

### Step 1: Clean Local Environment
```bash
cd /home/rahulvadera/cbp-sentry

# Stop all containers
docker-compose down

# Remove volumes (CAREFUL - deletes data!)
docker volume rm cbp-sentry_sentry_data_volume

# Remove cached images
docker rmi sentry-data:latest sentry-api:latest sentry-ui:latest sentry-cord-integration:latest
```

### Step 2: Rebuild and Start Fresh
```bash
# Rebuild images (no cache)
docker-compose build --no-cache

# Start services
docker-compose up

# Services start in order:
# 1. sentry-data → init_db() → creates tables → seed_corridors() → loads 7 corridors
# 2. sentry-api  → waits for sentry-data healthy
# 3. sentry-ui   → waits for sentry-api healthy
```

### Step 3: Verify Initialization
```bash
# Check sentry-data logs
docker logs sentry-data | grep -E "Corridors|INITIALIZING|✅"

# Expected output:
# 📦 INITIALIZING CORRIDORS from seed data (7 corridors)
# Loading corridor: VN→US
# Loading corridor: MY→US
# ... (7 total)
# ✅ Corridors initialized: 7 corridors with duties and enforcement actions
```

### Step 4: Test API Endpoint
```bash
# Direct to sentry-data (port 8005)
curl http://localhost:8005/corridors

# Via sentry-api proxy (port 8000)
curl http://localhost:8000/api/corridors

# Expected: JSON array with 7 corridors, each with computed_stats
```

### Step 5: Test UI
```
Open http://localhost:3001
Navigate to Shipping Intelligence
Left panel should show: "7 Active Corridors"
```

---

## Staging Deployment Architecture

### Challenge
Cloud Run doesn't persist state between deployments. Need to ensure:
1. Schema migrations applied on deploy
2. Seed data loaded on first deploy only
3. Subsequent deploys skip re-seeding (idempotent)

### Solution: Deploy-Time Initialization

#### Approach A: Init Container (Recommended for Cloud Run)
Use Cloud Run's service startup to run init before API starts.

**File**: `services/data/init_container.sh` (NEW)
```bash
#!/bin/bash
set -e

# Run database initialization
python -c "from db import init_db; init_db()"

# Seed corridors if not already present
python -c "from main import seed_corridors; seed_corridors()"

# Start the application
uvicorn main:app --host 0.0.0.0 --port 8005
```

**Update Dockerfile**:
```dockerfile
COPY init_container.sh /app/init_container.sh
RUN chmod +x /app/init_container.sh
CMD ["/app/init_container.sh"]
```

#### Approach B: Startup Hook in Lifespan (Current - Works)
Already implemented in `services/data/main.py`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()           # Creates tables if missing (idempotent)
    seed_demo_data()    # Loads manifest if table empty (idempotent)
    seed_corridors()    # Loads corridors if table empty (idempotent)
    yield
    logger.info("Shutdown")
```

**Why This Works**:
- `init_db()` uses `CREATE TABLE IF NOT EXISTS` (idempotent)
- `seed_corridors()` checks `SELECT COUNT(*) FROM corridors` before loading (idempotent)
- No manual migration scripts needed
- Works on every deploy, safe to repeat

### Updated `.github/workflows/deploy.yml`

Need to ensure:
1. Schema changes in code → picked up by `init_db()`
2. Seed file in image → `COPY seed_data/ /app/seed_data/`
3. Lifespan runs on startup → FastAPI does this automatically

**Key Changes**:
```yaml
deploy-data:
  # Existing build already includes COPY . . which gets seed_data/
  # Existing lifespan already calls init_db() and seed_corridors()
  
  # Just ensure GCS FUSE volume is set up for SQLite persistence:
  - name: Deploy sentry-data
    run: |
      gcloud run deploy sentry-data \
        --image ${{ env.GCR_REGISTRY }}/sentry-data:${{ env.IMAGE_TAG }} \
        --region ${{ env.REGION }} \
        --allow-unauthenticated \
        --set-cloudsql-instances ${{ env.CLOUDSQL_INSTANCE }} \
        --volume /app/data=${{ env.GCS_BUCKET }}/cbp-sentry-data \
        --execution-environment gen2 \
        --memory 2Gi \
        --max-instances 1 \
        --timeout 3600 \
        --update-env-vars DATA_SERVICE_URL=auto

deploy-api:
  # Ensure it resolves sentry-data URL at runtime (already done)
  # Scheduler will call sentry-data endpoints for data refresh
```

---

## Step-by-Step Staging Deployment

### Phase 1: Code Commit (Already Done ✅)
```
e1d28c1 refactor: Rewrite V2ShippingIntelligencePage with DB-driven architecture
e116c72 feat: Backend-first Shipping Intelligence with DB-driven corridors and pre-manifest vessels
```

### Phase 2: Build & Push Images
```bash
git push origin dev

# GitHub Actions workflow trigger:
# 1. paths-filter detects changes in:
#    - services/data/ (new tables, new endpoints, seed file)
#    - services/api/ (scheduler, refresh jobs, proxy routes)
#    - ui/src/v2/ (new hooks, page rewrite)
#
# 2. Conditional jobs:
#    - build-data: RUNS (code changed)
#    - build-api: RUNS (code changed)
#    - build-ui: RUNS (code changed)
#    - build-cord: SKIPS (no changes)
#
# 3. Deploy jobs (parallel):
#    - deploy-data: Creates tables + seeds 7 corridors
#    - deploy-api: Gets sentry-data URL from gcloud query
#    - deploy-ui: Connects to sentry-api via URL
```

### Phase 3: Verify Staging Deployment
```bash
# Get Cloud Run service URLs
gcloud run services describe sentry-data --region us-central1 --format='value(status.url)'
# Output: https://sentry-data-xxxxx.run.app

gcloud run services describe sentry-api --region us-central1 --format='value(status.url)'
# Output: https://sentry-api-xxxxx.run.app

# Test API (no auth needed for --allow-unauthenticated)
curl https://sentry-data-xxxxx.run.app/corridors

# Test with jq for pretty output
curl https://sentry-data-xxxxx.run.app/corridors | jq '.data | length'
# Expected output: 7
```

### Phase 4: Check Data Persistence
```bash
# Cloud Run logs should show:
gcloud logging read "resource.type=cloud_run_revision AND 
  resource.labels.service_name=sentry-data" \
  --limit=50 --format=json | \
  grep -E "Corridors|INITIALIZING"

# Expected output:
# "📦 INITIALIZING CORRIDORS from seed data (7 corridors)"
# "✅ Corridors initialized: 7 corridors with duties"

# Verify GCS FUSE volume mounted:
gcloud logging read "resource.labels.service_name=sentry-data" \
  --limit=10 --format=json | grep -i "gcs\|fuse\|mount"
```

### Phase 5: Test UI
```bash
# Get sentry-ui URL
gcloud run services describe sentry-ui --region us-central1 --format='value(status.url)'

# Open in browser and navigate to Shipping Intelligence
# Should see: "7 Active Corridors" in left panel
```

---

## Idempotency Verification

### Database Schema
✅ **Idempotent**: All `CREATE TABLE IF NOT EXISTS` statements
- Can run multiple times safely
- New deploys won't drop/recreate tables
- Preserves existing data

### Seed Data
✅ **Idempotent**: `seed_corridors()` checks if data exists
```python
cursor.execute("SELECT COUNT(*) FROM corridors")
count = cursor.fetchone()[0]
if count > 0:
    logger.info(f"✅ Corridors already seeded ({count} records), skipping")
    return  # Skip if already loaded
```

### Lifespan Execution
✅ **Idempotent**: Runs on every startup
- Cloud Run restarts pod = lifespan runs again
- init_db() safe to run multiple times
- seed_corridors() safe to run multiple times
- No manual intervention needed

---

## Troubleshooting Deployment Issues

### Issue 1: "Failed to fetch corridors: Not Found"

**Check 1: Are tables created?**
```bash
# SSH into Cloud SQL instance or use Cloud Run shell
gcloud beta run connect sentry-data --region us-central1
# Inside container:
python
>>> from db import init_db
>>> import sqlite3
>>> conn = sqlite3.connect("/app/data/cbp_sentry.db")
>>> cursor = conn.cursor()
>>> cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
>>> print(cursor.fetchall())
# Should show: ('shipments', 'manifests', 'scores', 'corridors', 'corridor_duties', ...)
```

**Check 2: Is seed data loaded?**
```python
>>> cursor.execute("SELECT COUNT(*) FROM corridors")
>>> print(cursor.fetchone()[0])
# Should show: 7
```

**Check 3: API endpoint working?**
```bash
curl -v https://sentry-data-xxxxx.run.app/corridors
# Should return 200 with JSON array
```

### Issue 2: "Corridors already seeded (0 records), skipping"

**Cause**: corridors table exists but is empty

**Solution**:
```bash
# Delete data volume (loses all data!)
gcloud compute disks delete cbp-sentry-data --zone us-central1-a

# Or manually clear table:
# (Connect to instance, run: DELETE FROM corridors;)

# Redeploy sentry-data
gcloud run deploy sentry-data --image ...
```

### Issue 3: "Seed file not found at /app/seed_data/corridors_seed.json"

**Cause**: COPY command in Dockerfile didn't include seed_data

**Solution**: Update Dockerfile
```dockerfile
WORKDIR /app
COPY requirements.txt .
COPY . .  # This should copy seed_data/ if it exists locally
RUN mkdir -p /app/seed_data  # Ensure directory exists
```

---

## Summary: What Changes Between Local & Staging

| Aspect | Local | Staging |
|--------|-------|---------|
| **Database** | Docker volume (sentry_data_volume) | GCS FUSE (/app/data) |
| **Schema Init** | Happens on `docker-compose up` | Happens on Cloud Run startup |
| **Seed Data** | Loaded from local file system | Baked into Docker image |
| **Idempotency** | Safe to restart containers | Safe to redeploy pods |
| **Data Persistence** | Survives container restart | Survives pod restart (GCS) |
| **Logs** | `docker logs sentry-data` | `gcloud logging read ...` |

**Key Insight**: Both use the SAME code path (lifespan + init_db + seed_corridors). Only infrastructure differs.

---

## Deployment Checklist

- [ ] Local: `docker-compose down && docker volume rm ... && docker rmi ... && docker-compose build --no-cache && docker-compose up`
- [ ] Local: Verify 7 corridors in DB (`curl localhost:8005/corridors`)
- [ ] Local: Verify UI loads Shipping Intelligence page
- [ ] Code: All changes committed to `dev` branch
- [ ] Staging: `git push origin dev` triggers GitHub Actions
- [ ] Staging: All images built successfully (check Actions tab)
- [ ] Staging: Services deployed to Cloud Run
- [ ] Staging: `gcloud run services list` shows 3 services healthy
- [ ] Staging: `curl https://sentry-data-xxxxx.run.app/corridors` returns 7 corridors
- [ ] Staging: UI loads at sentry-ui URL
- [ ] Staging: Shipping Intelligence page shows 7 corridors in left panel

---

## Files That Changed (For Deployment Context)

**Backend**:
- `services/data/db.py` — +4 new tables (CREATE TABLE IF NOT EXISTS)
- `services/data/main.py` — +seed_corridors() function + API endpoints
- `services/data/seed_data/corridors_seed.json` — NEW (7 corridors)
- `services/data/Dockerfile` — no changes needed (COPY . . includes seed_data/)

**Middleware**:
- `services/api/main.py` — +proxy routes + scheduler init
- `services/api/refresh_jobs.py` — NEW (background jobs)

**Fixes**:
- `api/services/risk_corridors/db.py` — fixed column names

**Frontend**:
- `ui/src/v2/hooks/` — new hooks
- `ui/src/v2/pages/V2ShippingIntelligencePage.tsx` — rewritten

---

## Key Principle

**No manual migrations needed.** The lifespan startup handles everything:
- Init on every deploy (idempotent)
- Seed on first deploy (idempotent)
- Works locally and in staging identically

This ensures consistency and reliability across all environments.
