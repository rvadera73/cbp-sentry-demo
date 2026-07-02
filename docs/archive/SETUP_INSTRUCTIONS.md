# Setup Instructions: Shipping Intelligence Feature

## Local Setup - Fix "Failed to fetch corridors" Error

### Root Cause
When code changes include database schema changes, Docker may use cached images/volumes. The solution is to:
1. Clear old images and volumes
2. Rebuild without cache
3. Start fresh with new schema + seed data

### Exact Steps (No Trial & Error)

**Step 1: Stop all services and clear cache**
```bash
cd /home/rahulvadera/cbp-sentry

# Stop containers
docker-compose down

# Remove old volumes (this DELETES the database - intentional for fresh start)
docker volume rm cbp-sentry_sentry_data_volume 2>/dev/null || true

# Remove cached images
docker rmi sentry-data:latest 2>/dev/null || true
docker rmi sentry-api:latest 2>/dev/null || true
docker rmi sentry-ui:latest 2>/dev/null || true
docker rmi sentry-cord-integration:latest 2>/dev/null || true

# Clear Docker build cache
docker builder prune -af
```

**Step 2: Rebuild all images (this takes ~3-5 minutes)**
```bash
# Rebuild with --no-cache to pick up all new code
docker-compose build --no-cache
```

**Step 3: Start services in order**
```bash
docker-compose up

# Services will start in this order (wait for output to show all healthy):
# 1. sentry-data (port 8005) - initializes DB + seeds corridors
# 2. sentry-cord-integration (port 8004) - waits for data service healthy
# 3. sentry-api (port 8000) - waits for data service + cord service healthy
# 4. sentry-ui (port 3001) - waits for api service healthy
```

**Step 4: Verify initialization in logs**
```bash
# In a NEW terminal, check the sentry-data initialization:
docker logs sentry-data | grep -A 20 "INITIALIZING CORRIDORS"

# Expected output:
# 📦 INITIALIZING CORRIDORS from seed data (7 corridors)
#    Loading corridor: VN→US
#    Loading corridor: MY→US
#    Loading corridor: CN→US
#    Loading corridor: HK→US
#    Loading corridor: TH→US
#    Loading corridor: SG→US
#    Loading corridor: IN→US
# ✅ Corridors initialized: 7 corridors with duties and enforcement actions
```

**Step 5: Test API directly**
```bash
# Test sentry-data endpoint (port 8005 - internal service)
curl -s http://localhost:8005/corridors | jq '.count'

# Expected output: 7

# Full corridor list
curl -s http://localhost:8005/corridors | jq '.data[0]'

# Expected: Object with id="VN→US", display_name, risk_level, computed_stats, duties[], enforcement_actions[]
```

**Step 6: Test via sentry-api proxy (port 8000)**
```bash
# Via API gateway (the path UI uses)
curl -s http://localhost:8000/api/corridors | jq '.count'

# Expected output: 7
```

**Step 7: Test UI (port 3001)**
```bash
# Open browser or curl
curl -s http://localhost:3001 > /dev/null && echo "UI healthy"

# Or visit: http://localhost:3001
# Navigate to "Shipping Intelligence" in the left menu
# You should see:
# - Left panel: "7 Active Corridors"
# - Corridor cards showing: VN→US, MY→US, CN→US, etc.
# - Each card shows: Risk level badge, Shipment count, Avg risk, Mismatch %, Unique shippers
```

**Step 8: Test clicking on corridor**
```bash
# UI test (manual):
1. Click on "VN→US" corridor card
2. Should see tabs on right: "Pre-Manifest", "Active Shipments", "Duties & Enforcement"
3. Click "Duties & Enforcement" tab
4. Should show:
   - AD/CVD duties with case numbers (A-552-824, USTR-301, etc.)
   - Rates (150.5%, 25%, etc.)
   - Source URLs (ustr.gov, cbp.gov)
   - EAPA enforcement actions with entity names and duty evasion amounts
```

### Troubleshooting Local Setup

**Problem: Still getting 404**
```bash
# Check database has tables
docker exec sentry-data sqlite3 /app/data/cbp_sentry.db ".tables"

# Should show: corridors corridor_duties corridor_enforcement_actions ...
# If not, schema not applied

# Check corridor count
docker exec sentry-data sqlite3 /app/data/cbp_sentry.db "SELECT COUNT(*) FROM corridors;"

# Should output: 7
# If 0, seed_corridors() didn't run
```

**Problem: Seed file not found**
```bash
# Check seed file exists in image
docker exec sentry-data ls -la /app/seed_data/

# Should show: corridors_seed.json
# If missing, Dockerfile didn't copy it

# Verify file is in repo
ls -la services/data/seed_data/corridors_seed.json

# If missing, create it:
git status services/data/seed_data/corridors_seed.json
```

**Problem: Services not connecting**
```bash
# Check docker network
docker network ls | grep sentry

# Check service connectivity
docker exec sentry-api curl -s http://sentry-data:8005/health

# Should return: {"status": "healthy", "service": "sentry-data"}
```

---

## Staging Deployment - Ready to Push

### Prerequisites
✅ Local testing complete (corridors showing in UI)
✅ All changes committed to `dev` branch
✅ Seed file committed: `services/data/seed_data/corridors_seed.json`
✅ Code changes in: `services/data/`, `services/api/`, `ui/src/v2/`

### Deployment Steps

**Step 1: Commit everything and push to dev**
```bash
cd /home/rahulvadera/cbp-sentry

# Verify status (should be clean)
git status

# Should show:
# On branch dev
# nothing to commit, working tree clean

# Push to dev (triggers GitHub Actions)
git push origin dev

# This triggers .github/workflows/deploy.yml
```

**Step 2: Monitor GitHub Actions**
```bash
# Open: https://github.com/YOUR_ORG/cbp-sentry/actions

# Wait for workflow to complete:
# 1. setup: Determines environment (staging)
# 2. changes: Detects changed files
#    - api: true (changed)
#    - data: true (changed - NEW TABLES + SEED)
#    - cord: false
#    - ui: true (changed)
# 3. test: Runs pytest (should pass)
# 4. build-data: Builds Docker image for sentry-data
#    - Includes seed_data/ directory
# 5. build-api: Builds Docker image for sentry-api
# 6. build-ui: Builds Docker image for sentry-ui
# 7. bootstrap-bucket: Ensures GCS bucket exists
# 8. deploy-data: Deploys to Cloud Run with:
#    - gen2 execution environment
#    - GCS FUSE volume at /app/data
#    - Lifespan runs: init_db() → seed_corridors()
# 9. deploy-api: Deploys to Cloud Run
# 10. deploy-ui: Deploys to Cloud Run

# Total time: ~5-10 minutes
```

**Step 3: Verify Staging Deployment**

```bash
# Get service URLs
gcloud run services list --platform=managed --region=us-central1 --format='table(NAME,URL)'

# Should show:
# sentry-data    https://sentry-data-xxxxx.run.app
# sentry-api     https://sentry-api-xxxxx.run.app
# sentry-ui      https://sentry-ui-xxxxx.run.app

# Test API (no auth needed with --allow-unauthenticated)
curl -s https://sentry-data-xxxxx.run.app/corridors | jq '.count'

# Expected output: 7

# Test via API gateway
curl -s https://sentry-api-xxxxx.run.app/api/corridors | jq '.count'

# Expected output: 7

# Check logs for initialization
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=sentry-data" \
  --limit=20 \
  --format='table(timestamp,jsonPayload.message)' \
  | grep -i "corridors\|initialized"

# Expected to see:
# INITIALIZING CORRIDORS from seed data
# Loading corridor: VN→US
# ...
# Corridors initialized: 7 corridors
```

**Step 4: Test Staging UI**
```bash
# Get UI URL
gcloud run services describe sentry-ui \
  --region=us-central1 \
  --format='value(status.url)'

# Open in browser and navigate to Shipping Intelligence
# Should see "7 Active Corridors" in left panel

# Click on VN→US corridor
# Should see duties with source URLs
```

**Step 5: Verify Data Persistence**
```bash
# Restart the sentry-data pod (simulates crash recovery)
gcloud run services update sentry-data \
  --region=us-central1 \
  --no-traffic 2>/dev/null || true

# Wait 30 seconds, then restart with traffic
sleep 30

gcloud run services update sentry-data \
  --region=us-central1 \
  --traffic LATEST=100 2>/dev/null || true

# Test API again - data should still be there
curl -s https://sentry-data-xxxxx.run.app/corridors | jq '.count'

# Expected output: 7 (data persisted via GCS FUSE)
```

---

## What Changed Between Local & Staging

| Aspect | Local | Staging |
|--------|-------|---------|
| Database persistence | Docker volume (`sentry_data_volume`) | GCS FUSE bucket (`cbp-sentry-appdata`) |
| Schema initialization | Happens on `docker-compose up` | Happens on Cloud Run pod startup (lifespan) |
| Seed data loading | From `services/data/seed_data/` | Baked into Docker image |
| Data survives pod restart | Yes (volume persists) | Yes (GCS FUSE persists) |
| Logs location | `docker logs sentry-data` | `gcloud logging read ...` |
| Network between services | Docker network bridge | Cloud Run service-to-service auth (OIDC) |

---

## Verification Checklist

### Local ✅
- [ ] `docker-compose down && docker volume rm && docker builder prune -af` completed
- [ ] `docker-compose build --no-cache` completed without errors
- [ ] `docker-compose up` shows all services healthy
- [ ] `docker logs sentry-data | grep "INITIALIZING CORRIDORS"` shows 7 corridors
- [ ] `curl localhost:8005/corridors` returns 7 with computed_stats
- [ ] `curl localhost:8000/api/corridors` returns 7
- [ ] UI loads at `localhost:3001`
- [ ] "Shipping Intelligence" page shows "7 Active Corridors"
- [ ] Clicking corridor shows duties with source URLs
- [ ] Refresh button works and shows timestamp

### Staging ✅
- [ ] Code pushed to dev branch
- [ ] GitHub Actions workflow completed successfully
- [ ] All 3 services deployed to Cloud Run
- [ ] `curl https://sentry-data-xxxxx.run.app/corridors` returns 7
- [ ] `curl https://sentry-api-xxxxx.run.app/api/corridors` returns 7
- [ ] UI loads at staging URL
- [ ] "Shipping Intelligence" page shows "7 Active Corridors"
- [ ] Duties show USITC case numbers and source URLs
- [ ] Enforcement actions show CBP press release links
- [ ] Pod restart test: data still present after restart
- [ ] Logs show corridor initialization on first deploy

---

## Next Steps After Verification

1. **Monitor Staging** for 24 hours
   - Check Cloud Run logs for errors
   - Verify no null values in responses
   - Test corridor selection multiple times

2. **API Integration Ready** (when credentials available)
   - Add `VESSEL_FINDER_API_KEY` to Cloud Run secrets
   - Add trade.gov API key (optional)
   - Scheduler jobs will automatically run (30-min / daily)
   - Pre-manifest vessels will populate from VesselFinder

3. **Promote to Production**
   - Same deployment process (merge dev → main)
   - GitHub Actions will deploy to prod environment
   - Same architecture, only GCP project changes

---

## Support

**If Something Goes Wrong**:
1. Check the "Troubleshooting" section above
2. Check logs:
   - Local: `docker logs sentry-data | tail -50`
   - Staging: `gcloud logging read "resource.labels.service_name=sentry-data" --limit=50`
3. Verify database:
   - Local: `docker exec sentry-data sqlite3 /app/data/cbp_sentry.db ".tables"`
   - Staging: Query via Cloud SQL proxy (if configured)
4. Check seed file:
   - `git ls-files services/data/seed_data/corridors_seed.json`
   - Should show the file path

**Key Principle**: Everything is idempotent. Running setup multiple times is safe.
