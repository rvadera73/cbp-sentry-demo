# CBP Sentry — Deployment Guide

**Version:** 2.0 | **Updated:** 2026-05-23 | **Audience:** DevOps Engineers, Developers, Operators

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

### 2.1 Quick Start with Script

```bash
# Clone repo
git clone https://github.com/rahulvadera/cbp-sentry.git
cd cbp-sentry

# Full clean build and start
./scripts/deploy-local.sh full
# → Builds all images and starts services
# → Opens http://localhost:3001 when ready
```

### 2.2 Deploy Script Options

```bash
./scripts/deploy-local.sh full          # Full clean build (wipes everything, rebuilds)
./scripts/deploy-local.sh ui            # Rebuild UI only (fastest for frontend changes)
./scripts/deploy-local.sh api           # Rebuild sentry-api only
./scripts/deploy-local.sh data          # Rebuild sentry-data only
./scripts/deploy-local.sh cord          # Rebuild sentry-cord-integration only
./scripts/deploy-local.sh quick         # Quick restart (no rebuild, containers already built)
./scripts/deploy-local.sh status        # Show container status
./scripts/deploy-local.sh logs          # Stream logs (Ctrl+C to exit)
./scripts/deploy-local.sh down          # Stop all containers
./scripts/deploy-local.sh clean         # Full system cleanup
./scripts/deploy-local.sh help          # Show all options
```

### 2.3 Manual Local Deployment (Development)

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

# Terminal 3: API Service
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATA_SERVICE_URL=http://localhost:8005
export CORD_SERVICE_URL=http://localhost:8004
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 4: UI Dev Server
cd ui
npm install
npm run dev
# → Open http://localhost:5173
```

### 2.4 Verification

```bash
# Check container health
curl http://localhost:8005/health  # Data service
curl http://localhost:8004/health  # CORD integration
curl http://localhost:8000/health  # API service
curl http://localhost:3001         # UI (should return HTML)

# Open in browser
open http://localhost:3001  # macOS
xdg-open http://localhost:3001  # Linux
```

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

**Expected startup sequence (30-45 seconds):**
1. `sentry-data` starts, seeds SQLite from manifest JSON
2. `sentry-cord-integration` waits for sentry-data healthy, loads CORD index
3. `sentry-api` waits for both dependencies
4. `sentry-ui` (nginx) starts, ready for browser traffic

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
  ↓ (git push origin dev/main)
  ↓ GitHub Actions: deploy.yml triggered
  ├─ Setup: Determine branch (dev/staging or main/prod)
  ├─ Changes: Detect which service directories changed (dorny/paths-filter)
  ├─ Test: pytest + TypeScript check (always)
  ├─ Build (conditional, only if changed):
  │  ├─ sentry-api (if services/api/** changed)
  │  ├─ sentry-data (if services/data/** changed)
  │  ├─ sentry-cord-integration (if services/cord-integration/** changed)
  │  └─ sentry-ui (if ui/** or services/api/** changed)
  ├─ Push: Images to Artifact Registry (us-central1-docker.pkg.dev)
  ├─ Deploy (conditional, only if built):
  │  ├─ sentry-data (GCS FUSE mount, gen2 execution)
  │  ├─ sentry-cord-integration (GCS FUSE mount, dynamic data URL)
  │  ├─ sentry-api (resolves data + cord URLs dynamically)
  │  └─ sentry-ui (gets fresh API URL)
  ├─ Smoke Tests: Health checks for all 4 services
  └─ Notify: Slack webhook with deployment status
  ↓
Cloud Run services updated (5-10 minutes, less if unchanged services skipped)
```

**Selective Deployment Rules:**
- **dev branch (staging)**: Only changed services are built/deployed (faster feedback)
- **main branch (production)**: Always deploy all 4 services (consistency + safety)
- **Workflow file change**: Triggers all 4 services regardless of branch

**Services & Change Paths:**
| Service | Build if Changed | Redeploy if Built |
|---|---|---|
| sentry-api | `services/api/**` | Yes |
| sentry-data | `services/data/**` | Yes |
| sentry-cord-integration | `services/cord-integration/**` | Yes |
| sentry-ui | `ui/**` or `services/api/**` changed | Yes |

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

### 4.5 Deployed Service Configuration

| Service | Memory | CPU | Min Instances | Max Instances | Persistence | Env Variables |
|---|---|---|---|---|---|---|
| **sentry-api** | 2Gi | 2 | 1 | 10 | None | API_MODE=live, DATA_SERVICE_URL, CORD_SERVICE_URL, VESSELAPI_KEY, OFAC_API_KEY |
| **sentry-data** | 1Gi | 1 | 1 | 1 | GCS FUSE `/app/data/cbp_sentry.db` | DEPLOYMENT_ENV |
| **sentry-cord-integration** | 2Gi | 2 | 1 | 1 | GCS FUSE `/app/data/senzing.db` | CORD_DATA_DIR, DATA_SERVICE_URL, DEPLOYMENT_ENV |
| **sentry-ui** | 512Mi | 1 | 0 | 10 | None (static) | None (baked at build) |

**Persistence Details:**
- **GCS FUSE**: sentry-data and sentry-cord-integration both mount `gs://cbp-sentry-appdata` as `/app/data`
- **Execution**: data and cord use gen2 execution environment (required for GCS FUSE)
- **Single Writer**: Both data and cord have max-instances=1 to avoid SQLite write contention
- **Bucket Creation**: Automatic via `bootstrap-bucket` job; reused across deployments

Configuration defined in `.github/workflows/deploy.yml` (jobs: deploy-api, deploy-data, deploy-cord, deploy-ui).

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
