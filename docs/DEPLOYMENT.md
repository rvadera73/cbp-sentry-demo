# CBP Sentry — Deployment Guide

**Version:** 2.2 | **Updated:** 2026-06-24 | **Audience:** DevOps Engineers, Developers, Operators

> **Current state:** `cbp-risk-engine` (port 8010) is a standalone service not yet in docker-compose.
> `precise-risk-engine` is deprecated and scheduled for removal.
> See `CLAUDE.md` for current service ports and start commands.

---

## 1. Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| **Docker** | 24.0+ | 26.0+ |
| **Docker Compose** | 2.20+ | 2.30+ |
| **Node.js** | 18 | 20 LTS |
| **Python** | 3.11 | 3.12 |
| **npm** | 9+ | 10+ |
| **Git** | Any | Latest |
| **RAM (local dev)** | 4GB | 8GB+ |
| **Disk (local dev)** | 2GB free | 5GB+ |

### Cloud Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI v475+ installed and authenticated
- GitHub repository with Secrets and Actions enabled

### API Keys (Optional, for AI Features)

- `GOOGLE_API_KEY` — Google Gemini Pro (get from [Google AI Studio](https://makersuite.google.com/app/apikey))
- `ALTANA_API_KEY` — Altana Atlas supply chain verification
- `VESSELAPI_KEY` — VesselFinder AIS data
- `OFAC_API_KEY` — OFAC SDN feeds

---

## 2. Local Deployment

### 2.1 Quick Start with Script (Recommended)

```bash
# Clone repo
git clone https://github.com/rahulvadera/cbp-sentry.git
cd cbp-sentry

# Full clean build and start
./scripts/local_startup.sh [clean]

# With 'clean' argument: wipes previous volumes, rebuilds from scratch
# Without argument: reuses existing images, stops/restarts containers

# Expected startup time: 30-45 seconds
# Services deployed: sentry-ui (3001), sentry-api (8000), sentry-data (8005),
#                   sentry-cord-integration (8004)
# Note: precise-risk-engine (8007) is deprecated — scheduled for removal
# Note: cbp-risk-engine (8010) is standalone — start separately (see below)
```

### 2.1b Starting cbp-risk-engine (MLOps MCP Service)

```bash
# cbp-risk-engine is not yet in docker-compose — start manually:
cd /home/rahulvadera/cbp-risk-engine
MODEL_DIR=/home/rahulvadera/cbp-sentry/models \
SENTRY_SRC=/home/rahulvadera/cbp-sentry/services/api \
nohup .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8010 \
  > /tmp/mcp_server.log 2>&1 &
curl http://localhost:8010/health    # verify
```

### 2.2 Advanced Local Deployment (Custom Configuration)

For custom environment variables or manual control:

```bash
# Start with Docker Compose
docker compose up -d

# Verify all services are healthy
docker compose ps
curl http://localhost:8000/health      # sentry-api
curl http://localhost:8005/health      # sentry-data
curl http://localhost:8004/health      # sentry-cord-integration
curl http://localhost:8010/health      # cbp-risk-engine (if running)

# Note: USE_PRECISE_RISK_MODEL feature flag is REMOVED
# Scoring now uses risk_scoring_engine.py directly (XGBoost + rule engine blend)
```

### 2.3 Manual Local Deployment (Development, Multi-Terminal)

If you want to run services separately for debugging:

```bash
# Terminal 1: Data Service
cd services/data
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8005 --reload

# Terminal 2: CORD Integration
cd services/cord-integration
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8004 --reload

# Terminal 3: Precise Risk Engine (Phase 2)
cd services/risk-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m flask run --port 8004  # Note: runs on 8004 (internal only in this mode)
# OR: python app.py

# Terminal 4: API Service
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATA_SERVICE_URL=http://localhost:8005
export CORD_SERVICE_URL=http://localhost:8004
export USE_PRECISE_RISK_MODEL=false              # Start with legacy model (safe)
export PRECISE_RISK_ENGINE_URL=http://localhost:8004
export PRECISE_RISK_ENGINE_TIMEOUT=5
export TRAFFIC_PERCENTAGE=0
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 5: UI Dev Server
cd ui
npm install
npm run dev
# → Open http://localhost:5173
```

**To test Phase 2 in this setup:**
```bash
# Once all services running, enable the feature flag
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 50}'

# Then score a shipment (50% will use precise-risk-engine, 50% will use legacy)
curl -X POST http://localhost:8000/api/shipment/score ...
```

### 2.4 Verification

```bash
# Check all core services are healthy
curl http://localhost:8005/health              # Data service
curl http://localhost:8004/health              # CORD integration
curl http://localhost:8000/health              # API service
curl http://localhost:3001                     # UI (should return HTML)
# Optional: cbp-risk-engine if running
curl http://localhost:8010/health              # MLOps MCP service

# Open in browser
open http://localhost:3001  # macOS
xdg-open http://localhost:3001  # Linux
```

---

## 2.5 ~~Phase 2 — Feature Flag & Traffic Ramping~~ (Removed)

> **The `USE_PRECISE_RISK_MODEL` feature flag has been removed.**
> Scoring now goes directly through `risk_scoring_engine.py` in sentry-api
> (XGBoost 60% + rule engine 40% blend). `precise-risk-engine` container is deprecated.
>
> MLOps model lifecycle is managed by `cbp-risk-engine` at port 8010 (MCP service).
> See `docs/ARCHITECTURE.md § MLOps Architecture` for the new model management approach.

---

## 3. Local Docker (Production Build)

### 3.1 Build All Images

```bash
cd /path/to/cbp-sentry

# Full clean build (no cache)
docker compose build --no-cache

# Or specific services
docker compose build --no-cache sentry-api sentry-ui
```

### 3.2 Start Services

```bash
# Start in background
docker compose up -d

# Monitor startup
docker compose logs -f

# Check status
docker compose ps
```

**Expected startup sequence (30-60 seconds):**
1. `sentry-data` starts, seeds SQLite from manifest JSON
2. `sentry-cord-integration` waits for sentry-data healthy, loads CORD index
3. `sentry-api` waits for sentry-data + sentry-cord; starts scoring engine
4. `sentry-api` waits for all three dependencies, loads feature flag state
5. `sentry-ui` (nginx) starts, ready for browser traffic

**Risk Scoring Model Used:**
- If `USE_PRECISE_RISK_MODEL=false` (default): Uses legacy rule-based model
- If `USE_PRECISE_RISK_MODEL=true` with `TRAFFIC_PERCENTAGE=N`: Routes N% traffic to precise-risk-engine, (100-N)% to legacy
- If precise-risk-engine unavailable: Automatic fallback to legacy (no downtime)

### 3.3 Stop Services

```bash
docker compose down       # Stop (keep volumes)
docker compose down -v    # Stop and remove volumes (full clean)
```

---

## 4. Cloud Run Automated Deployment

**All Cloud Run deployments are automatic via GitHub Actions. Do NOT manually deploy to Cloud Run.**

### 4.1 Automatic Deployment Flow (Selective Build+Deploy)

As of May 2026, the workflow uses intelligent path-based change detection to skip building unchanged services:

```
Your local commit
  ↓ (git push origin dev/stage or stable)
  ↓ GitHub Actions: deploy.yml or deploy-production.yml triggered
  ├─ Setup: Determine branch & environment
  ├─ Changes: Detect which service directories changed
  ├─ Test: pytest + TypeScript check (always includes Phase 2 tests)
  ├─ Build (conditional, only if changed):
  │  ├─ sentry-api (if services/api/** changed)
  │  ├─ sentry-data (if services/data/** changed)
  │  ├─ sentry-cord-integration (if services/cord-integration/** changed)
  │  ├─ precise-risk-engine (if services/risk-engine/** changed) ← NEW Phase 2
  │  └─ sentry-ui (if ui/** or services/api/** changed)
  ├─ Push: Images to Artifact Registry (us-central1-docker.pkg.dev)
  ├─ Deploy (conditional, only if built):
  │  ├─ sentry-data (GCS FUSE mount, gen2 execution)
  │  ├─ sentry-cord-integration (GCS FUSE mount, dynamic data URL)
  │  ├─ precise-risk-engine (1Gi memory, 1 CPU, gen2) ← NEW Phase 2
  │  ├─ sentry-api (resolves all URLs, sets Phase 2 env vars)
  │  └─ sentry-ui (gets fresh API URL)
  ├─ Smoke Tests: Health checks for all 5 services + feature flag
  └─ Notify: Slack webhook with deployment status
  ↓
Cloud Run services updated (5-10 minutes, less if unchanged services skipped)
```

**Selective Deployment Rules:**
- **dev/stage branches (staging)**: Only changed services built/deployed; Phase 2 enabled with 10% traffic
- **stable branch (production)**: Always deploy all 5 services; Phase 2 enabled with 0% traffic (safe default)
- **Workflow file change**: Triggers all 5 services regardless of branch

**Services & Change Paths:**
| Service | Build if Changed | Deployment | Phase 2 Config |
|---|---|---|---|
| sentry-api | `services/api/**` | Always | Includes phase2_integration.py |
| sentry-data | `services/data/**` | Conditional | Unchanged |
| sentry-cord-integration | `services/cord-integration/**` | Conditional | Unchanged |
| precise-risk-engine | `services/risk-engine/**` | Conditional | NEW — XGBoost model + config |
| sentry-ui | `ui/**` or `services/api/**` | Conditional | Unchanged |

### 4.2 How to Deploy

Deployment is fully automated on push. Just commit to the appropriate branch:

**Staging (dev branch):**
```bash
git checkout dev
git commit -m "feature: your changes"
git push origin dev
# → GitHub Actions auto-triggers
# → Detects changed services
# → Builds only changed services
# → Deploys to staging (5-8 minutes)
```

**Production (main branch):**
```bash
git checkout main
git commit -m "release: version bump"
git push origin main
# → GitHub Actions auto-triggers
# → Full deploy of all 4 services (regardless of changes)
# → Deploys to production (8-10 minutes)
```

**Example deployment times (staging):**
- UI only changed: ~5 minutes (skip api/data/cord builds)
- API changed: ~7 minutes (rebuild api + ui, redeploy both)
- Data changed: ~6 minutes (rebuild data, redeploy all dependents)
- Workflow changed: ~8 minutes (full rebuild like main branch)

### 4.3 Monitor Deployment

**GitHub Actions:**
```bash
# View workflow runs
open https://github.com/rahulvadera/cbp-sentry/actions

# Or use gh CLI
gh run list --repo rahulvadera/cbp-sentry --limit 10
gh run view <RUN_ID> --repo rahulvadera/cbp-sentry
```

**Cloud Run Services:**
```bash
# List services
gcloud run services list --region us-central1

# View service details
gcloud run services describe sentry-api --region us-central1

# Stream logs
gcloud run logs read sentry-api --region us-central1 --follow --limit 50
gcloud run logs read sentry-ui --region us-central1 --limit 100
```

### 4.4 Get Service URLs

After successful deployment:

```bash
export API_URL=$(gcloud run services describe sentry-api --region us-central1 --format='value(status.url)')
export DATA_URL=$(gcloud run services describe sentry-data --region us-central1 --format='value(status.url)')
export UI_URL=$(gcloud run services describe sentry-ui --region us-central1 --format='value(status.url)')

echo "API:  $API_URL"
echo "Data: $DATA_URL"
echo "UI:   $UI_URL"

# Open UI in browser
open ${UI_URL}  # macOS
xdg-open ${UI_URL}  # Linux
```

---

## 4.5 Phase 2 — Traffic Ramping & Feature Flag Management

### Deployment Defaults

| Environment | USE_PRECISE_RISK_MODEL | TRAFFIC_PERCENTAGE | Status |
|---|---|---|---|
| **Local** | false | 0 | OFF (safe default, uses legacy) |
| **Staging** | true | 10 | Gradual rollout (90% legacy, 10% precise) |
| **Production** | true | 0 | OFF initially (manual increase after validation) |

### Traffic Ramping Timeline (Production)

After production deployment, follow this schedule to gradually increase traffic to the Precise Risk Model:

```
Day 0, Deployment Time:
  TRAFFIC_PERCENTAGE=0   (100% legacy model)
  → Monitor error rates, latency, score consistency
  
Day 1, 10am:
  TRAFFIC_PERCENTAGE=10  (90% legacy, 10% precise)
  → Score a sample of 50+ shipments
  → Compare legacy vs precise scores
  → Monitor for anomalies

Day 2, 10am (if Day 1 clean):
  TRAFFIC_PERCENTAGE=50  (50% legacy, 50% precise)
  → Score larger sample
  → Analyze score distribution
  → Validate accuracy improvements

Day 3, 10am (if Day 2 clean):
  TRAFFIC_PERCENTAGE=90  (90% precise, 10% legacy)
  → Most shipments now using new model
  → Continue monitoring

Day 4, 10am (if Day 3 clean):
  TRAFFIC_PERCENTAGE=100 (100% precise model)
  → Full migration complete
  
DECISION POINT (Day 4 EOD):
  If any issues detected: Instant rollback to TRAFFIC_PERCENTAGE=0
```

### Manual Traffic Control

Traffic percentage can be adjusted immediately without redeployment using the feature flag API:

```bash
# Get current feature flag status
curl https://sentry-api-prod.example.com/api/feature-flag \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"

# Increase traffic to 25%
curl -X POST https://sentry-api-prod.example.com/api/feature-flag \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 25}'

# Disable immediately (instant rollback to 0%)
curl -X POST https://sentry-api-prod.example.com/api/feature-flag \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, "traffic_percentage": 0}'
```

### Validation During Ramping

1. **Latency**: Compare response times (should be <5s for both models)
2. **Accuracy**: Score samples with both models side-by-side
3. **Errors**: Monitor sentry-api logs for fallback events
4. **Coverage**: Ensure precise-risk-engine remains healthy and responsive

```bash
# Compare models side-by-side (staging/production)
curl -X POST https://sentry-api.example.com/api/shipment/score/compare \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "SHP-test-001",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 2.5
  }'
# Returns: {legacy_score: 65, precise_score: 72, confidence: 0.94, differences: [...]}
```

### Monitoring During Ramping

**Cloud Logging Dashboard:**
```bash
# Watch precise-risk-engine errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=precise-risk-engine" \
  --limit 50 --follow

# Watch API fallback events
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sentry-api AND jsonPayload.event=fallback_to_legacy" \
  --limit 50 --follow
```

**Slack Notifications:**
- GitHub Actions sends deployment status automatically
- Configure Slack webhook for Phase 2 milestones (10%, 50%, 90%, 100%)

---

### 4.6 Deployed Service Configuration

| Service | Memory | CPU | Min Instances | Max Instances | Persistence | Env Variables |
|---|---|---|---|---|---|---|
| **sentry-api** | 2Gi | 2 | 1 | 10 | None | API_MODE=live, DATA_SERVICE_URL, CORD_SERVICE_URL, USE_PRECISE_RISK_MODEL, PRECISE_RISK_ENGINE_URL, TRAFFIC_PERCENTAGE, VESSELAPI_KEY, OFAC_API_KEY |
| **sentry-data** | 1Gi | 1 | 1 | 1 | GCS FUSE `/app/data/cbp_sentry.db` | DEPLOYMENT_ENV |
| **sentry-cord-integration** | 2Gi | 2 | 1 | 1 | GCS FUSE `/app/data/senzing.db` | CORD_DATA_DIR, DATA_SERVICE_URL, DEPLOYMENT_ENV |
| **precise-risk-engine** (Phase 2) | 1Gi | 1 | 1 | 3 | Model cache (ephemeral) | FLASK_ENV, LOG_LEVEL |
| **sentry-ui** | 512Mi | 1 | 0 | 10 | None (static) | None (baked at build) |

**Persistence Details:**
- **GCS FUSE**: sentry-data and sentry-cord-integration both mount `gs://cbp-sentry-appdata` as `/app/data`
- **Execution**: data and cord use gen2 execution environment (required for GCS FUSE)
- **Single Writer**: Both data and cord have max-instances=1 to avoid SQLite write contention
- **Bucket Creation**: Automatic via `bootstrap-bucket` job; reused across deployments
- **Precise Risk Engine**: Loads XGBoost model from /app/models/* at startup; ephemeral cache; no persistent storage needed

Configuration defined in `.github/workflows/deploy.yml` (jobs: deploy-api, deploy-data, deploy-cord, deploy-risk-engine, deploy-ui).

---

## 5. One-Time GCP Setup

### 5.1 Run Setup Script

If infrastructure doesn't exist:

```bash
bash scripts/setup_gcp_staging.sh
```

This creates:
- Artifact Registry
- Service accounts
- IAM roles
- Secret Manager secrets
- GCS bucket (for SQLite persistence)
- GitHub Secrets list to copy

### 5.2 Manual Alternative: Service Account Key

If setup script not available:

```bash
# Create service account
gcloud iam service-accounts create sentry-deploy

# Grant Cloud Run Admin
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
  --member=serviceAccount:sentry-deploy@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/run.admin

# Create and encode key
gcloud iam service-accounts keys create key.json \
  --iam-account=sentry-deploy@${GCP_PROJECT_ID}.iam.gserviceaccount.com

# Encode as base64 for GitHub Secrets
cat key.json | base64

# Add to GitHub Secrets as GCP_SA_KEY
gh secret set GCP_SA_KEY --repo rahulvadera/cbp-sentry < <(cat key.json | base64)
```

---

## 6. GitHub Secrets Configuration

### 6.1 Required Secrets

Add to `https://github.com/rahulvadera/cbp-sentry/settings/secrets/actions`:

```
GCP_PROJECT_ID        Your GCP project ID (e.g., cbp-sentry-prod)
GCP_SA_KEY             Service account JSON key (base64-encoded)
DATABASE_URL           Database connection string:
                       - SQLite: sqlite:///./data/cbp_sentry.db
                       - PostgreSQL: postgresql://user:pass@host/dbname
```

### 6.2 Optional Secrets (for AI Features)

```
GOOGLE_API_KEY         Google Gemini Pro API key
ALTANA_API_KEY         Altana Atlas API key
VESSELAPI_KEY          VesselFinder AIS API key
OFAC_API_KEY           OFAC SDN API key
SLACK_WEBHOOK          Slack webhook URL for deployment notifications
```

### 6.3 Setting Secrets

```bash
# Using gh CLI
gh secret set GCP_PROJECT_ID --repo rahulvadera/cbp-sentry --body "my-project"
gh secret set DATABASE_URL --repo rahulvadera/cbp-sentry --body "sqlite:///./data/cbp_sentry.db"
gh secret set GCP_SA_KEY --repo rahulvadera/cbp-sentry < key.json.base64

# Or via GitHub web UI
# → Settings → Secrets and variables → Actions → New repository secret
```

---

## 7. Database Configuration

### 7.1 SQLite (for Staging/Local)

```bash
# Set DATABASE_URL
gh secret set DATABASE_URL --repo rahulvadera/cbp-sentry --body "sqlite:///./data/cbp_sentry.db"
```

**Pros:** No cloud resources, persistent across Cloud Run revisions (with GCS FUSE mount)
**Cons:** Single-writer constraint, not suitable for high concurrency

### 7.2 PostgreSQL (for Production)

**Option A: Cloud SQL**

```bash
# Create Cloud SQL instance
gcloud sql instances create sentry-prod \
  --database-version POSTGRES_15 \
  --tier db-custom-4-16384 \
  --region us-central1

# Create database + user
gcloud sql databases create cbp_sentry --instance sentry-prod
gcloud sql users create dbuser --instance sentry-prod --password

# Get connection string
CONNECTION_NAME=$(gcloud sql instances describe sentry-prod --format='value(connectionName)')
echo "postgresql://dbuser:PASSWORD@/cbp_sentry?host=/cloudsql/${CONNECTION_NAME}"

# Create VPC Connector (for Cloud Run → Cloud SQL)
gcloud compute networks vpc-access connectors create sentry-sql-connector \
  --network default --region us-central1 --min-throughput 200 --max-throughput 1000
```

**Option B: External PostgreSQL**

```bash
# Set connection string directly
gh secret set DATABASE_URL --repo rahulvadera/cbp-sentry \
  --body "postgresql://user:password@db.example.com:5432/cbp_sentry"
```

---

## 8. Troubleshooting

### Docker Compose Won't Start

**Symptom:** `docker compose up` hangs or fails.

**Fix:**
```bash
# 1. Check Docker daemon
docker ps

# 2. Review logs
docker compose logs sentry-data

# 3. Check port conflicts
lsof -i :8005 :8004 :8000

# 4. Rebuild without cache
docker compose build --no-cache

# 5. Full clean
docker compose down -v
docker system prune -af
```

### API Not Responding

**Symptom:** `curl http://localhost:8000/health` → connection refused

**Fix:**
```bash
# Check if service is running
docker compose ps | grep sentry-api

# Check logs
docker compose logs sentry-api

# Restart service
docker compose restart sentry-api

# Check port is correct
netstat -tulnp | grep 8000  # Linux
lsof -i :8000              # macOS
```

### UI Shows "Cannot Connect to API"

**Symptom:** Browser shows CORS error or 502 Bad Gateway

**Fix:**
```bash
# Check API is healthy
curl http://localhost:8000/health

# Check VITE_API_URL is correct
grep VITE_API_URL ui/vite.config.ts

# For dev server: should proxy to http://localhost:8000
# For docker: should be http://sentry-api:8000 (internal)
```

### Cloud Run Deployment Failed

**Symptom:** GitHub Actions workflow shows red X

**Fix:**
```bash
# View workflow logs
gh run view <RUN_ID> --repo rahulvadera/cbp-sentry --log

# Check specific step
gh run view <RUN_ID> --repo rahulvadera/cbp-sentry --log | grep -A 20 "error"

# Common causes:
# - GCP_SA_KEY invalid or expired
# - DATABASE_URL secret missing or wrong format
# - Docker build failed (check Dockerfile)
# - Insufficient Cloud Run quota
```

### SQLite Lock Error

**Symptom:** `database is locked` in logs

**Cause:** Multiple instances writing to same SQLite file

**Fix:**
```bash
# Local: Only one sentry-data instance
docker compose ps | grep sentry-data

# Cloud Run: Ensure max-instances=1 on sentry-data
# (Already configured in deploy.yml)

# Check Cloud Run settings
gcloud run services describe sentry-data --region us-central1 | grep max-instances
```

### Cloud Run Service Timeout

**Symptom:** `504 Gateway Timeout`

**Fix:**
```bash
# Increase timeout (default 900s)
gcloud run services update sentry-api --timeout 1800 --region us-central1
```

### Entity Resolution Not Working (Empty Results)

**Symptom:** UI shows "No entities found" when searching shipment entities (works in local, not in staging)

**Root Cause:** sentry-cord-integration service not deployed or not initialized with demo entities

**Fix - Check if service is deployed:**
```bash
# List all Cloud Run services
gcloud run services list --region us-central1

# If sentry-cord-integration is missing:
# → Run full deployment (push to main branch)
# OR manually trigger GitHub Actions workflow
```

**Fix - Check service health:**
```bash
# Get service URL
CORD_URL=$(gcloud run services describe sentry-cord-integration --region us-central1 --format 'value(status.url)')

# Test health endpoint
curl -f "$CORD_URL/health"

# Should return JSON with entity_count > 0
# If entity_count is 0, service didn't load demo entities
```

**Fix - Check service logs for initialization errors:**
```bash
# Stream latest logs
gcloud run logs read sentry-cord-integration --region us-central1 --follow --limit 50

# Look for these log lines:
# ✓ Senzing engine initialized
# Loading CORD data...
# Seeding demo entities...
# ✓ Senzing engine ready with N entities

# If you see errors (✗):
# 1. Check GCS FUSE mount is working
# 2. Check /app/data/senzing.db file permissions
# 3. Redeploy the service
```

**Fix - Verify GCS FUSE persistence is working:**
```bash
# Check if data service has shipments (prerequisite for cord augmentation)
DATA_URL=$(gcloud run services describe sentry-data --region us-central1 --format 'value(status.url)')
curl "$DATA_URL/shipments/meta/count"

# Should return {"total": N} with N > 0
# If N is 0, sentry-data didn't load manifest → check its logs

# Then check if cord service is calling data service correctly
# Look in cord logs for: "Augmenting with CBP shipment data..."
```

**Fix - Force redeployment of cord service:**
```bash
# Change something in services/cord-integration/ (e.g., add a comment)
# Then push to dev
git add services/cord-integration/
git commit -m "fix: trigger cord redeployment"
git push origin dev

# GitHub Actions will rebuild and deploy only sentry-cord-integration
# Wait for workflow to complete
```

---

## 9. Rollback Procedure

### Via GitHub Actions

```bash
# Revert last commit
git revert HEAD
git push origin main  # or dev

# GitHub Actions will auto-deploy the reverted code
```

### Via Cloud Run Traffic Splitting

```bash
# List recent revisions
gcloud run revisions list --service sentry-api --region us-central1 --limit 5

# Route 100% traffic to previous revision
gcloud run services update-traffic sentry-api \
  --to-revisions PREVIOUS=100 \
  --region us-central1

# Gradual rollback (10% old, 90% new for monitoring)
gcloud run services update-traffic sentry-api \
  --to-revisions PREVIOUS=10 LATEST=90 \
  --region us-central1
```

### Database Backup/Restore

**SQLite (GCS FUSE):**
```bash
# Backup
gsutil cp gs://cbp-sentry-staging-data/app/data/cbp_sentry.db ./backup_$(date +%Y%m%d_%H%M%S).db

# Restore
gsutil cp ./backup_20260523_120000.db gs://cbp-sentry-staging-data/app/data/cbp_sentry.db
```

**PostgreSQL (Cloud SQL):**
```bash
# Create on-demand backup
gcloud sql backups create --instance sentry-prod

# List backups
gcloud sql backups list --instance sentry-prod

# Restore (if needed)
gcloud sql backups restore <BACKUP_ID> --backup-instance sentry-prod
```

---

## 10. Monitoring & Logs

### Cloud Run Logs

```bash
# Stream API logs
gcloud run logs read sentry-api --region us-central1 --follow

# Last 100 lines
gcloud run logs read sentry-api --region us-central1 --limit 100

# Filter by severity
gcloud run logs read sentry-api --region us-central1 --limit 50 --severity=ERROR

# Search for pattern
gcloud run logs read sentry-api --region us-central1 | grep "risk_score"
```

### Docker Compose Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f sentry-api

# Last 50 lines
docker compose logs --tail 50 sentry-data

# By timestamp
docker compose logs --since 10m  # Last 10 minutes
```

### Cloud Monitoring Metrics

Auto-exported to Cloud Monitoring (console.cloud.google.com):
- Request count, latency, error rate per endpoint
- Cold start time
- Memory/CPU usage
- Deployment frequency

---

## 11. Production Hardening Checklist

- [ ] Enable Cloud Armor (DDoS protection)
- [ ] Enable VPC Service Controls (restrict external API calls)
- [ ] Enable audit logging (gcloud logging sinks create ...)
- [ ] Set Cloud Run min-instances ≥1 (avoid cold starts)
- [ ] Implement rate limiting on `/api/*` endpoints
- [ ] Rotate API keys monthly
- [ ] Enable Cloud SQL backup (automated daily)
- [ ] Enable encryption at rest (KMS keys)
- [ ] Regular security scanning (gcloud container images scan)
- [ ] Document runbooks for common incidents

---

## Next Steps

- **Architecture details:** See [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **UI/UX design:** See [`DESIGN.md`](DESIGN.md)
- **Support:** File issue on GitHub or contact DevOps team
