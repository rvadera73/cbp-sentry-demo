# Phase 2 Deployment Summary - Updated Scripts & CI/CD

## What Was Updated

### 1. ✅ docker-compose.yml (Updated)
- Added `precise-risk-engine` service (port 8007, maps to 8004 internally)
- Added Phase 2 environment variables to `sentry-api` service
- Made `sentry-api` depend on `precise-risk-engine` service
- Full backward compatibility (existing services unchanged)

### 2. ✅ scripts/deploy-phase2.sh (New)
- Automated deployment script for Phase 2
- Supports: local, staging, production environments
- Configurable traffic percentage (0-100%)
- Built-in health checks
- Feature flag configuration

### 3. ✅ .github/workflows/deploy-phase2.yml (New)
- GitHub Actions CI/CD pipeline
- Builds all 3 services (API, Risk Engine, UI)
- Runs tests before deployment
- Auto-deploys to GCP Cloud Run
- Staging on `develop` branch
- Production on `main` branch (with manual traffic control)
- Slack notifications for deployments

### 4. ✅ phase2_integration.py (New)
- Phase 2 integration module for CBP Sentry API
- PreciseRiskClient for HTTP communication
- Feature flag management
- Fallback mechanism

---

## How to Deploy

### LOCAL DEPLOYMENT

**Option 1: Using docker-compose (Recommended)**

```bash
# Clone/navigate to repo
cd /home/rahulvadera/cbp-sentry

# Deploy with feature flag OFF (safe default)
docker-compose up -d

# Wait for services to start
sleep 30

# Verify all services
curl http://localhost:8000/health  # API
curl http://localhost:8007/health  # Risk Engine
curl http://localhost:3001/health  # UI

# Check feature flag (should be false)
curl http://localhost:8000/api/feature-flag
```

**Option 2: Using deploy script**

```bash
# Deploy to local
./scripts/deploy-phase2.sh local

# Deploy with 10% traffic
./scripts/deploy-phase2.sh local traffic=10
```

### STAGING DEPLOYMENT

```bash
# Automatic: Push to develop branch
git commit -am "Phase 2 staging deployment"
git push origin develop

# GitHub Actions will:
# 1. Build all services
# 2. Run tests
# 3. Deploy to Cloud Run (staging)
# 4. Set traffic to 10% on new model
```

### PRODUCTION DEPLOYMENT

```bash
# Automatic: Push to main branch
git commit -am "Phase 2 production release"
git push origin main

# GitHub Actions will:
# 1. Build all services
# 2. Run tests
# 3. Deploy to Cloud Run (production)
# 4. Set traffic to 0% on new model (safe default)
# 5. Send Slack notification
```

**Manual traffic control (after production deployment):**

```bash
# Increase to 10%
curl -X POST https://sentry-api-prod.example.com/api/feature-flag \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 10}'

# Increase to 50%
curl -X POST ... -d '{"enabled": true, "traffic_percentage": 50}'

# Go to 100%
curl -X POST ... -d '{"enabled": true, "traffic_percentage": 100}'

# Emergency rollback
curl -X POST ... -d '{"enabled": false}'
```

---

## Docker Compose Structure

```
┌─────────────────────────────────────────┐
│  Docker Compose (updated)               │
├─────────────────────────────────────────┤
│                                         │
│  precise-risk-engine (NEW)              │
│  ├─ Flask API                           │
│  ├─ XGBoost model                       │
│  ├─ Port: 8007 → 8004                   │
│  └─ Depends on: sentry-data             │
│                                         │
│  sentry-api (UPDATED)                   │
│  ├─ FastAPI                             │
│  ├─ Phase 2 env vars added              │
│  ├─ Port: 8000                          │
│  └─ Depends on: precise-risk-engine ✨  │
│                                         │
│  sentry-ui                              │
│  ├─ React Vite                          │
│  ├─ Port: 3001                          │
│  └─ Unchanged                           │
│                                         │
│  sentry-data                            │
│  sentry-cord-integration                │
│  senzing (optional)                     │
│                                         │
└─────────────────────────────────────────┘
```

---

## Environment Variables

### Phase 2-Specific Env Vars

```bash
# Feature flag control
USE_PRECISE_RISK_MODEL=false              # OFF = legacy only, TRUE = enable routing

# Microservice communication
PRECISE_RISK_ENGINE_URL=http://precise-risk-engine:8004
PRECISE_RISK_ENGINE_TIMEOUT=5             # seconds

# Traffic ramping
TRAFFIC_PERCENTAGE=0                      # 0-100% on new model
```

### .env File (for local development)

```bash
# Phase 2 Configuration
USE_PRECISE_RISK_MODEL=false
PRECISE_RISK_ENGINE_URL=http://precise-risk-engine:8004
PRECISE_RISK_ENGINE_TIMEOUT=5
TRAFFIC_PERCENTAGE=0

# Other services (existing)
DEPLOYMENT_ENV=local
API_MODE=live
DATA_SERVICE_URL=http://sentry-data:8005
GOOGLE_API_KEY=...
```

---

## GitHub Actions Pipeline

### On `develop` push (Staging):
```
Checkout → Build → Test → Deploy to Cloud Run (staging) → Notify
```

### On `main` push (Production):
```
Checkout → Build → Test → Deploy to Cloud Run (prod, 0% traffic) → Smoke tests → Notify
```

### Manual workflow trigger:
```
GitHub UI → Run workflow → Select environment + traffic % → Deploy
```

---

## Services and Ports

| Service | Port | Docker | Status |
|---------|------|--------|--------|
| Precise Risk Engine | 8007 | 8004 | ✨ NEW |
| CBP Sentry API | 8000 | 8000 | Updated |
| CBP Sentry UI | 3001 | 80 | Unchanged |
| Data Service | 8005 | 8005 | Unchanged |
| CORD Integration | 8004 | 8004 | Unchanged |
| Senzing | 8250 | 8250 | Optional |
| PostgreSQL | 5432 | 5432 | Unchanged |

---

## Testing After Deployment

### Local Testing (docker-compose)

```bash
# 1. Verify services
curl http://localhost:8000/health
curl http://localhost:8007/health
curl http://localhost:3001/health

# 2. Check feature flag
curl http://localhost:8000/api/feature-flag

# 3. Score with legacy
curl -X POST http://localhost:8000/api/shipment/score -d '...'

# 4. Enable new model (10% traffic)
curl -X POST http://localhost:8000/api/feature-flag \
  -d '{"enabled": true, "traffic_percentage": 10}'

# 5. Score with new model
curl -X POST http://localhost:8000/api/shipment/score -d '...'

# 6. Compare models
curl -X POST http://localhost:8000/api/shipment/score/compare -d '...'
```

### Cloud Run Testing (staging/production)

```bash
# Get service URL
API_URL=$(gcloud run services describe sentry-api --platform managed --region us-central1 --format 'value(status.url)')

# Test with auth token
TOKEN=$(gcloud auth print-identity-token)

curl -H "Authorization: Bearer $TOKEN" $API_URL/health
curl -H "Authorization: Bearer $TOKEN" $API_URL/api/feature-flag
```

---

## Rollback Procedure

### Emergency Rollback (Instant)

```bash
# Disable Phase 2 (back to legacy model)
curl -X POST https://sentry-api-prod.example.com/api/feature-flag \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Immediate effect: All traffic on legacy model
# No redeployment needed
# No downtime
```

### Docker Rollback

```bash
# Revert to previous docker-compose
git revert HEAD
git push origin main

# GitHub Actions auto-deploys previous version
```

---

## Continuous Integration

### Automated Tests on Every Push

```bash
# tests/test_api.py
# tests/test_risk_model.py
# tests/test_phase2_integration.py

# Run locally:
cd services/api && pytest tests/ -v
cd services/risk-engine && pytest tests/ -v
```

### Build Caching

- Docker layer caching enabled in GitHub Actions
- Faster deployments on subsequent pushes
- GHA cache shared across runs

---

## Monitoring Deployment

### Docker Logs

```bash
# API logs
docker-compose logs -f sentry-api

# Risk Engine logs
docker-compose logs -f precise-risk-engine

# UI logs
docker-compose logs -f sentry-ui

# All logs
docker-compose logs -f
```

### Cloud Run Logs

```bash
# API logs
gcloud run logs read sentry-api-prod --platform managed --region us-central1 --limit 50

# Risk Engine logs
gcloud run logs read precise-risk-engine-prod --platform managed --region us-central1 --limit 50
```

### Metrics

- Feature flag status: `curl /api/feature-flag`
- Traffic split: `echo $TRAFFIC_PERCENTAGE`
- Model version in response: `"model_version"` field
- Route in response: `"route"` field (legacy/new/fallback)

---

## Comparison: Old vs New Deployment

| Aspect | Old | New |
|--------|-----|-----|
| **Services** | 5 (data, api, ui, cord, senzing) | 6 (+ risk-engine) |
| **Deployment** | Manual docker-compose | Automated CI/CD + manual |
| **Feature flag** | None | Integrated in API |
| **Traffic control** | Restart required | Runtime API call |
| **Rollback** | Redeploy | API call (instant) |
| **Testing** | Manual | Automated in GitHub Actions |
| **Monitoring** | Logs only | Logs + feature flag API |

---

## Next Steps

1. ✅ **Files updated**: docker-compose.yml, new deployment script, new CI/CD workflow
2. ⏳ **Commit changes**: `git add . && git commit -m "Phase 2: Updated deployment scripts & CI/CD"`
3. ⏳ **Test locally**: `docker-compose up` and run tests
4. ⏳ **Push to develop**: Triggers staging deployment
5. ⏳ **Push to main**: Triggers production deployment (traffic at 0%)
6. ⏳ **Monitor**: Check Slack notifications and logs
7. ⏳ **Ramp traffic**: Gradually increase traffic percentage

---

## Quick Reference

```bash
# Start local
docker-compose up -d

# Deploy via script
./scripts/deploy-phase2.sh local

# Check status
curl http://localhost:8000/api/feature-flag

# Enable 10% traffic
curl -X POST http://localhost:8000/api/feature-flag \
  -d '{"enabled": true, "traffic_percentage": 10}'

# Disable (rollback)
curl -X POST http://localhost:8000/api/feature-flag \
  -d '{"enabled": false}'

# View logs
docker-compose logs -f sentry-api
```

---

**Status**: ✅ All deployment scripts and CI/CD updated for Phase 2  
**Ready for**: Local testing, staging deployment, production release

