# Cloud Run Deployment Architecture

**Status:** Staging (dev branch) on Google Cloud Run  
**Database:** Neon PostgreSQL (free tier) or SQLite  
**Authentication:** OIDC service-to-service, OAuth 2.0 for users  
**Region:** us-central1  

---

## 1. Cloud Run Service Topology

```mermaid
graph TB
    subgraph GCP["Google Cloud Platform"]
        LB["☁️ Cloud Load Balancer<br/>SSL/TLS Termination<br/>Rate Limiting"]
        
        subgraph Services["Cloud Run Services"]
            UI["🎨 sentry-ui<br/>Memory: 512MB<br/>CPU: 0.5<br/>Min: 1, Max: 10<br/>Port: 80"]
            API["⚙️ sentry-api<br/>Memory: 2GB<br/>CPU: 2<br/>Min: 1, Max: 100<br/>Port: 8000"]
            DATA["💾 sentry-data<br/>Memory: 1GB<br/>CPU: 1<br/>Min: 1, Max: 50<br/>Port: 8005"]
        end
        
        subgraph Storage["Storage & Secrets"]
            SQL["🗄️ Neon PostgreSQL<br/>prod schema<br/>Serverless<br/>Free tier"]
            SM["🔐 Secret Manager<br/>DATABASE_URL<br/>API_MODE<br/>VESSELAPI_KEY<br/>OFAC_API_KEY"]
            AR["📦 Artifact Registry<br/>gcr.io/cbp-sentry<br/>Docker images"]
            GCS["☁️ Google Cloud Storage<br/>cord_rag.db backup<br/>Manifests archive"]
        end
        
        subgraph Network["Network & Security"]
            VPC["🔒 Private VPC<br/>No public IPs<br/>Cloud SQL Connector"]
            WIF["🔑 Workload Identity<br/>Federation<br/>GitHub Actions OIDC"]
        end
    end
    
    External["🌐 External<br/>OpenCorporates<br/>VesselAPI<br/>OFAC Treasury"]
    
    LB --> UI
    LB --> API
    LB --> DATA
    
    UI -.->|OIDC Token| API
    API -.->|OIDC Token| DATA
    
    API --> SM
    DATA --> SM
    
    DATA --> SQL
    DATA --> GCS
    
    API --> AR
    API --> GCS
    
    API --> External
    
    WIF -.->|GitHub Actions| AR
```

---

## 2. GitHub Actions CI/CD Pipeline

```mermaid
graph LR
    Trigger["📤 git push<br/>dev branch"]
    
    Setup["🔧 Setup<br/>- Detect branch/env<br/>- Auth to GCP"]
    Test["🧪 Test<br/>- Python pytest<br/>- TypeScript check"]
    Build["🏗️ Build<br/>- Docker build<br/>- 3 matrix services"]
    Push["📤 Push Images<br/>Artifact Registry<br/>Tags: SHA, latest, branch"]
    Deploy["🚀 Deploy to Cloud Run<br/>- sentry-api<br/>- sentry-data<br/>- sentry-ui"]
    Smoke["✅ Smoke Tests<br/>- /health checks<br/>- Endpoint tests"]
    Notify["📢 Notify Slack<br/>Success/Failure<br/>+ Deployment details"]
    
    Trigger --> Setup
    Setup --> Test
    Test --> Build
    Build --> Push
    Push --> Deploy
    Deploy --> Smoke
    Smoke --> Notify
    
    style Trigger fill:#e1f5ff
    style Deploy fill:#c8e6c9
    style Notify fill:#fff9c4
```

---

## 3. Service-to-Service OIDC Authentication Flow

```mermaid
sequenceDiagram
    participant UI as sentry-ui<br/>Cloud Run
    participant API as sentry-api<br/>Cloud Run
    participant DATA as sentry-data<br/>Cloud Run
    participant Meta as GCP Metadata<br/>Server
    participant SM as Secret<br/>Manager
    
    API->>Meta: Request OIDC token<br/>audience=sentry-data URL
    Meta->>API: Return signed JWT<br/>(service account identity)
    
    API->>API: Attach JWT as Bearer token<br/>Authorization: Bearer [JWT]
    
    API->>DATA: GET /shipments<br/>+ Bearer token
    
    DATA->>DATA: Verify JWT signature<br/>Validate service account
    
    DATA->>SM: Fetch DATABASE_URL secret
    SM->>DATA: Return PostgreSQL connection string
    
    DATA->>DATA: Query database
    DATA->>API: Return 200 OK + data
    
    API->>UI: Return results
```

---

## 4. Environment Variables & Secret Management

**Local Development (docker-compose.yml):**
```yaml
API_MODE: fixture                          # Mock external APIs
DATA_SERVICE_URL: http://sentry-data:8005  # Internal service
SENZING_URL: http://senzing:8250
DATABASE_URL: sqlite:////app/data/cbp_sentry.db
```

**Staging (Cloud Run, dev branch):**
```yaml
API_MODE: live                             # Real external APIs
DATA_SERVICE_URL: https://sentry-data-staging.run.app
DATABASE_URL: [from Secret Manager]
VESSELAPI_KEY: [from Secret Manager]
OFAC_API_KEY: [from Secret Manager]
CORD_DB_PATH: /tmp/cord_rag.db             # Download on startup
```

**All secrets in Secret Manager** (NEVER in code or environment variables):
- `DATABASE_URL` — PostgreSQL URI
- `API_MODE` — 'live' or 'fixture'
- `VESSELAPI_KEY` — AISStream.io key
- `OFAC_API_KEY` — Treasury SDN API key
- `ALTANA_API_KEY` — Supply chain API key (future)

---

## 5. Database Strategy

### Local/Dev (SQLite):
- File-based: `data/cbp_sentry.db`
- Auto-seed on startup from `seed_data/manifests_2026_2000_records.json`
- No schema migrations needed (idempotent table creation)

### Staging (Neon PostgreSQL):
- Serverless, free tier (perfect for low-traffic demos)
- Auto-scaling to zero when idle
- Connection pooling built-in
- Migration path: `sqlite3 cbp_sentry.db ".dump"` → Neon SQL importer

### Production (Cloud SQL PostgreSQL):
- Managed Google instance (higher SLA)
- Private service connection (no public IP)
- Automated backups every 6 hours
- Point-in-time recovery enabled

**Migration Command:**
```bash
# Export SQLite to SQL dump
sqlite3 data/cbp_sentry.db ".dump" > dump.sql

# Import to Neon via psql
psql "postgresql://user:password@host/dbname" < dump.sql
```

---

## 6. CORD RAG Data Handling

**Local:** Embedded in code as `data/cord_rag.db` (19MB SQLite)

**Staging/Production:** Download on cold start
```python
# services/api/main.py startup
import os
from google.cloud import storage

@app.on_event("startup")
async def download_cord_db():
    if not os.path.exists("/tmp/cord_rag.db"):
        client = storage.Client()
        bucket = client.bucket("cbp-sentry-data")
        blob = bucket.blob("cord_rag.db")
        blob.download_to_filename("/tmp/cord_rag.db")
        logger.info("Downloaded CORD RAG database")
```

---

## 7. Deployment Checklist

**Before first staging deploy:**
- [ ] GCP project `cbp-sentry` created
- [ ] GitHub Secrets configured (GCP_PROJECT_ID, GCP_WORKLOAD_IDENTITY_PROVIDER, etc.)
- [ ] Service accounts created (sentry-api, sentry-data, sentry-deploy)
- [ ] Artifact Registry repository `cbp-sentry` created
- [ ] Neon database provisioned (free tier)
- [ ] Secret Manager populated (DATABASE_URL, API_MODE, etc.)
- [ ] Docker images build locally without errors
- [ ] `git push origin dev` triggers GitHub Actions pipeline

**Post-deploy verification:**
- [ ] All three services healthy (Cloud Run console shows 1+ instances)
- [ ] `/health` endpoints return 200 OK
- [ ] `/api/shipments` returns manifest records
- [ ] UI loads at Cloud Run service URL
- [ ] Smoke tests in pipeline report success
- [ ] Slack notification received

---

## 8. Cost Estimates (Monthly)

| Service | Tier | Monthly Cost |
|---------|------|---|
| Cloud Run (3 services) | dev=free, prod=on-demand | ~$0-50 |
| Neon PostgreSQL | free tier | $0 |
| Cloud Storage | 1GB CORD data | ~$0.02 |
| Cloud Logging | 50GB logs | ~$15 |
| **Total** | | ~$15-65 |

*Reduced to ~$5/mo with reserved capacity and log retention tuning.*

---

## 9. Rollback Strategy

**If new deployment breaks:**

```bash
# Cloud Run keeps last 100 revisions automatically
gcloud run services describe sentry-api --region us-central1

# Traffic split: 90% → new revision, 10% → previous
gcloud run services update-traffic sentry-api \
  --to-revisions LATEST=10,PREVIOUS=90 \
  --region us-central1

# Rollback: 100% → previous
gcloud run services update-traffic sentry-api \
  --to-revisions PREVIOUS=100 \
  --region us-central1
```

Alternatively, re-run GitHub Actions on previous commit:
```bash
git revert HEAD          # Create new commit that undoes changes
git push origin dev      # Re-trigger pipeline
```

---

## 10. Monitoring & Alerting

**Cloud Logging & Monitoring dashboards:**
- Endpoint latency: p50, p95, p99 per service
- Error rate by endpoint (4xx, 5xx)
- Container CPU/Memory utilization
- Database connection pool status
- Cold start duration (Cloud Run revisions)

**Alert thresholds (non-demo):**
- Latency p95 > 5s for 5 minutes → Page oncall
- Error rate > 5% for 2 minutes → Page oncall
- Database CPU > 90% for 3 minutes → Page oncall
- Disk space < 10% → Warn to Slack

For demo: Only Slack notifications (no PagerDuty).
