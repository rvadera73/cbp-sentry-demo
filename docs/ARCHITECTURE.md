# CBP Sentry - System Architecture Documentation

## 1. SYSTEM OVERVIEW

**Purpose:** AI-powered risk scoring system for CBP illegal transshipment detection
**Technology Stack:** Python 3.12, FastAPI, React 19, SQLite, Docker, Google Cloud Run
**Deployment:** Microservices on Cloud Run with secure inter-service communication

---

## 2. CURRENT SYSTEM STATE

### 2.1 Running Containers (Local)
```
sentry-ui:3001          → React frontend (Nginx)
sentry-api:8000         → FastAPI gateway + H1/H2/H3 scoring
sentry-data:8005        → SQLite CRUD abstraction layer
```

### 2.2 Missing/Stubbed Components
- **Senzing SDK**: Not yet integrated (entity resolution)
- **VesselAPI**: Not yet integrated (vessel tracking data)
- **CORD RAG**: Partially implemented (local SQLite, not live API)
- **Altana Atlas**: Not yet integrated (supply chain intelligence)

---

## 3. SERVICE ARCHITECTURE

### 3.1 Service Responsibilities

| Service | Port | Purpose | Current Status |
|---------|------|---------|-----------------|
| **sentry-api** | 8000 | H1/H2/H3 scoring, orchestration | ✓ Running |
| **sentry-data** | 8005 | SQLite CRUD layer | ✓ Running |
| **sentry-ui** | 3001 | React frontend | ✓ Running |
| **Senzing** | 8250 | Entity resolution | ✗ Not integrated |
| **VesselAPI** | (external) | AIS vessel tracking | ✗ Not integrated |

### 3.2 Data Flow & Service Topology

**ASCII Flow (simplified):**
```
User → sentry-ui (3001)
  ↓ (HTTPS)
API Gateway (8000)
  ├→ H1 Scorer (corridor risk)
  ├→ H2 Scorer (vessel anomaly)
  ├→ H3 Scorer (intelligence)
  └→ sentry-data (8005)
       ├→ SQLite database
       └→ External APIs (fixture mode)
```

**Mermaid Service Topology:**
```mermaid
graph TB
    User["👤 CBP Officer Browser"]
    
    LB["🌐 Load Balancer<br/>SSL/TLS"]
    
    UI["🎨 sentry-ui:3001<br/>React + Nginx<br/>Case Viewer, Referral Package"]
    API["⚙️ sentry-api:8000<br/>FastAPI Gateway<br/>H1/H2/H3 Scoring"]
    DATA["💾 sentry-data:8005<br/>SQLite CRUD Layer<br/>Shipments, Manifests, Scores"]
    ER["🔗 entity_resolution<br/>CORD RAG + Senzing<br/>Entity Matching"]
    
    OCorp["🏢 OpenCorporates<br/>Company Registries"]
    AIS["🚢 VesselAPI / AIS<br/>Vessel Tracking"]
    OFAC["⚠️ OFAC/SDN<br/>Sanction Lists"]
    
    DB["🗄️ SQLite File<br/>data/cbp_sentry.db<br/>1,191 shipments"]
    CORDDB["🔍 CORD RAG DB<br/>cord_rag.db<br/>244K entities"]
    
    User -->|HTTP/HTTPS| LB
    LB --> UI
    LB --> API
    LB --> DATA
    
    UI -->|/api/*| API
    API -->|OIDC Token| DATA
    API -->|HTTP| ER
    API -->|Fixture/Live| OCorp
    API -->|Fixture/Live| AIS
    API -->|API Key| OFAC
    
    DATA -->|Read/Write| DB
    ER -->|Read| CORDDB
```

---

## 4. SCORING SYSTEM (100 POINTS MAX)

### 4.1 Three-Level Horizons

| Horizon | Points | Components | Data Sources |
|---------|--------|------------|--------------|
| **H1: Corridor Risk** | 40 | Origin/dest country, HS code, tariff rates, pricing | OpenCorporates, Comtrade, ITC |
| **H2: Vessel Anomaly** | 35 | AIS dwell time, ISF Element 9 mismatch, port calls | VesselAPI, PortAuthority, ISF |
| **H3: Intelligence** | 25 | Entity ownership depth, shipper age, OFAC match, watch list | Senzing, OFAC, Watchlists |

**Mermaid Scoring Pipeline:**
```mermaid
graph LR
    Manifest["📦 Shipment Manifest"]
    
    H1["<b>H1: Corridor Risk</b><br/>40 points<br/><br/>🌍 Origin/Dest Country<br/>📊 HS Code Tariff<br/>💰 AD/CVD Rates<br/>💵 Price Anomaly"]
    H1Score["H1 Score<br/>0-40 pts"]
    
    H2["<b>H2: Vessel Anomaly</b><br/>35 points<br/><br/>⚓ AIS Dwell Time<br/>✈️ ISF Element 9<br/>🛢️ Port Sequence<br/>⏱️ Transit Delta"]
    H2Score["H2 Score<br/>0-35 pts"]
    
    H3["<b>H3: Intelligence</b><br/>25 points<br/><br/>🏢 Entity Chain Depth<br/>📜 Shipper Age<br/>⚠️ OFAC Match<br/>👁️ Watch List Hit"]
    H3Score["H3 Score<br/>0-25 pts"]
    
    Total["<b>Total Score</b><br/>0-100 points<br/><br/>🔴 RED ≥70<br/>🟡 YELLOW 40-69<br/>🟢 GREEN <40"]
    
    Manifest --> H1 --> H1Score
    Manifest --> H2 --> H2Score
    Manifest --> H3 --> H3Score
    
    H1Score --> Total
    H2Score --> Total
    H3Score --> Total
    
    Total --> |Risk Classification| Referral["📋 CBP Referral<br/>Package<br/>14 Tables"]
```

### 4.2 Risk Classification

- **RED** (≥70): EXAMINE ON ARRIVAL
- **YELLOW** (40-69): REVIEW / RECOMMEND EXAM
- **GREEN** (<40): CLEAR

Current distribution (1,191 records):
- RED: 37 cases
- YELLOW: 590 cases
- GREEN: 564 cases

---

## 5. DATABASE LAYER

### 5.1 SQLite Schema

```
shipments (1,191 records)
├── id (PK): SHP-000001
├── manifest_id: MNF-2026-SHP-000001
├── shipper_name, consignee_name
├── origin_country, destination_country (ISO-2)
├── hs_code (tariff classification)
├── declared_value_usd, declared_weight_kg
├── vessel_name
├── risk_score (computed, 0-100)
├── h1_score, h2_score (nullable)
├── ofac_match, status
└── created_at, updated_at

scoring_overrides (analyst feedback)
├── shipment_id (FK)
├── original_score, override_decision
├── analyst_id, analyst_name
└── notes

weight_configurations (H1/H2/H3 tuning)
├── corridor (e.g., "VN→US")
├── w_corridor, w_vessel, w_manifest
└── created_by, notes
```

---

## 6. MISSING INTEGRATIONS

### 6.1 Senzing Entity Resolution

**Status:** ✗ Not integrated in production

**What it does:**
- Matches entities across data sources
- Builds ownership chains (shipper ↔ manufacturer)
- Resolves beneficial owners
- Provides confidence scores

**Required:**
- Docker: `senzing/senzing-api-server:3.5.x`
- G2 database (PostgreSQL)
- License key

**Integration:** Replace stub in `services/api/external_apis/entity_resolution.py`

### 6.2 VesselAPI Integration

**Status:** ✗ Stubbed in `h2_adapters.py`

**What it does:**
- Real-time AIS vessel positions
- Dwell time: port arrival → departure
- ISF Element 9 validation
- Port call sequences

**Options:**
- AISStream.io WebSocket
- MarineTraffic REST API
- Both require paid subscription

**Integration:** Replace stub in `services/api/external_apis/h2_adapters.py`

### 6.3 Altana Atlas

**Status:** ✗ Not integrated

**What it does:**
- Supply chain visibility
- Trader risk flags
- Transaction patterns
- Anomaly detection vs baseline

**Integration:** New endpoint `/api/altana/supply-chain`

---

## 7. CLOUD DEPLOYMENT ARCHITECTURE

### 7.1 Google Cloud Run Services

```
┌─────────────────────────────────────────┐
│  Google Cloud Platform                  │
├─────────────────────────────────────────┤
│                                         │
│  Cloud Load Balancer (SSL/TLS)          │
│  ├─ sentry-ui:latest (React SPA)        │
│  ├─ sentry-api:latest (FastAPI)         │
│  ├─ sentry-data:latest (CRUD)           │
│  ├─ sentry-senzing:latest               │
│  └─ sentry-vessel:latest                │
│         │              │                │
│         └──────┬───────┘                │
│                │                        │
│  ┌─────────────▼──────────────┐        │
│  │ Cloud SQL (PostgreSQL)     │        │
│  │ - shipments, scores        │        │
│  │ - Senzing G2 database      │        │
│  └────────────────────────────┘        │
│                                         │
│  ┌────────────────────────────┐        │
│  │ Secret Manager             │        │
│  │ - API keys                 │        │
│  │ - DB credentials           │        │
│  │ - Senzing license          │        │
│  └────────────────────────────┘        │
│                                         │
│  ┌────────────────────────────┐        │
│  │ Cloud Logging & Monitoring │        │
│  │ - Application logs         │        │
│  │ - Metrics & alerts         │        │
│  │ - Audit trail              │        │
│  └────────────────────────────┘        │
│                                         │
└─────────────────────────────────────────┘
```

### 7.2 Service-to-Service Communication

```
Authentication: Google Service Accounts + OIDC tokens

sentry-api (SA: sentry-api@project.iam.gserviceaccount.com)
    ↓ (OIDC token + HTTPS)
sentry-data (SA: sentry-data@project.iam.gserviceaccount.com)
    ↓ (Cloud SQL Proxy, IAM authentication)
Cloud SQL

sentry-api
    ↓ (Senzing SDK library call, embedded)
Senzing (G2 database in Cloud SQL)

sentry-api (API key from Secret Manager)
    ↓ (HTTPS)
VesselAPI (AISStream.io or MarineTraffic)
```

### 7.3 Environment Variables (Secret Manager)

```yaml
DATABASE_URL: postgresql://user:pass@localhost:5432/sentry
DATABASE_SSL_MODE: require

SENZING_LICENSE: <base64-encoded-license>
SENZING_G2_DATABASE_URL: postgresql://...

VESSELAPI_KEY: <api-key>
VESSELAPI_PROVIDER: aisstream  # or marinetraffic

ALTANA_API_KEY: <api-key>
OFAC_API_KEY: <api-key>

API_MODE: live  # not fixture
DEBUG: false

# Cloud Run specific
PORT: 8080  # Container port
```

---

## 8. GITHUB ACTIONS DEPLOYMENT

### 8.1 CI/CD Pipeline Structure

**File:** `.github/workflows/deploy.yml`

**Triggers:**
```yaml
on:
  push:
    branches: [main, dev]
    paths:
      - 'services/**'
      - 'ui/**'
      - '.github/workflows/**'
  pull_request:
    branches: [main, dev]
```

**Pipeline Stages:**
1. **Setup** → Authenticate to GCP
2. **Test** → Run pytest, TypeScript checks
3. **Build** → Docker build → Artifact Registry
4. **Deploy** → gcloud run deploy
5. **Smoke Tests** → Verify endpoints
6. **Notify** → Slack, email

### 8.2 Docker Image Strategy

```
Artifact Registry: gcr.io/project-id/cbp-sentry/

sentry-api:
  ├─ build from services/api/Dockerfile
  ├─ layers: base → dependencies → code
  ├─ size: ~500MB

sentry-data:
  ├─ build from services/data/Dockerfile
  ├─ layers: base → dependencies → code
  ├─ size: ~300MB

sentry-ui:
  ├─ build from ui/Dockerfile
  ├─ multi-stage: build → nginx
  ├─ size: ~50MB

sentry-senzing:
  ├─ from senzing/senzing-api-server:3.5.x
  ├─ wrapper: initialization script
  ├─ size: ~2GB (includes G2 engine)
```

### 8.3 Deployment Strategy

**Staging (dev branch):**
```
git push origin dev
  ↓
  ├─ Build images
  ├─ Push to staging tags
  ├─ Deploy to Cloud Run (--region us-central1)
  ├─ Run smoke tests
  └─ Notify #deployments Slack
```

**Production (main branch):**
```
git push origin main
  ↓
  ├─ Build images
  ├─ Push to gcr.io (release tags)
  ├─ Manual approval required
  ├─ Blue/green deploy (canary 10% → 100%)
  ├─ Run smoke tests + performance tests
  ├─ Monitor error rate (5 min, <1%)
  └─ Notify #deployments Slack
```

---

## 9. SECURITY ARCHITECTURE

### 9.1 Authentication Layers

```
┌─ External Users (CBP Officers)
│  ├─ OAuth 2.0 (Google Identity)
│  ├─ SAML (CBP SSO) - future
│  └─ Roles: cbp_officer, analyst, admin
│
├─ Service-to-Service
│  ├─ OIDC tokens (Google-signed JWT)
│  ├─ Service accounts with minimal IAM
│  └─ No shared credentials
│
└─ External APIs
   ├─ API keys (Secret Manager)
   ├─ Rotated every 90 days
   └─ Per-service keys (not shared)
```

### 9.2 Data Protection

| Layer | Method |
|-------|--------|
| **At Rest** | Cloud SQL encryption, Cloud Storage encryption |
| **In Transit** | HTTPS only, TLS 1.3 minimum |
| **Database Access** | Cloud SQL Proxy (no public IP) |
| **Secrets** | Google Secret Manager (automatic rotation) |

### 9.3 Network Security

```
VPC (Private)
  ├─ All services: no public IPs
  ├─ Ingress: only from Load Balancer
  ├─ Egress: only to allowed external APIs
  ├─ Cloud SQL: private service connection
  └─ Cloud Armor: DDoS protection

Load Balancer
  ├─ SSL/TLS termination
  ├─ Rate limiting
  ├─ WAF (Web Application Firewall)
  └─ DDoS protection
```

---

## 10. MONITORING & OBSERVABILITY

### 10.1 Logging (Cloud Logging)

```
Application logs → Cloud Logging
  ├─ Structured JSON format
  ├─ Request logs: latency, status, user_id
  ├─ Error logs: exceptions, stack traces
  └─ Audit logs: upload, score, export actions

Log retention:
  ├─ Application: 30 days
  ├─ Audit: 1 year
  └─ Shipment records: 7 years
```

### 10.2 Metrics (Cloud Monitoring)

```
Performance:
  ├─ Latency: p50, p95, p99
  ├─ Error rate: 4xx, 5xx by endpoint
  ├─ Throughput: requests/sec
  └─ Cache hit rate

Resource:
  ├─ CPU: container, database
  ├─ Memory: container, database
  ├─ Disk: database, storage
  └─ Connections: database pool

Custom:
  ├─ Scoring distribution: RED/YELLOW/GREEN %
  ├─ Manifest ingest rate: records/sec
  ├─ Entity resolution match rate
  └─ OFAC hits per day
```

### 10.3 Alerting

```
PagerDuty:
  ├─ Latency p95 > 5s (page after 5 min)
  ├─ Error rate > 5% (page immediately)
  └─ Database CPU > 90% (page immediately)

Slack (#alerts channel):
  ├─ Latency p95 > 3s (warn after 10 min)
  ├─ Error rate > 1% (warn after 5 min)
  ├─ Database CPU > 80% (warn)
  └─ Disk space < 10% (warn)
```

---

## 11. COMPLIANCE & AUDIT

### 11.1 Data Retention

```
Shipment records: 7 years (CBP requirement per 19 CFR 123.2)
Scoring audit trail: 2 years
API logs: 30 days (cost), archived to Cloud Storage
User audit logs: 1 year
```

### 11.2 Compliance Frameworks

- **FedRAMP Moderate** (eventual requirement)
- **FISMA** (Federal Information Security Management Act)
- **CBP Data Handling** (19 CFR 123.2)
- **SOC 2 Type II** (audit recommendations)

---

## 12. CONTAINER INVENTORY

### Current (Running)
| Container | Image | Port | Status |
|-----------|-------|------|--------|
| sentry-ui | sentry-ui:latest | 3001 | ✓ |
| sentry-api | sentry-api:latest | 8000 | ✓ |
| sentry-data | sentry-data:latest | 8005 | ✓ |

### Required (Not Yet)
| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| sentry-senzing | senzing/senzing-api-server:3.5.x | 8250 | Entity resolution |
| sentry-vessel | custom | (none) | VesselAPI wrapper (Cloud Run) |

### Total Containers on Cloud Run: 5
- sentry-ui (1 instance min)
- sentry-api (1 instance min, scales to 100)
- sentry-data (1 instance min, scales to 50)
- sentry-senzing (1 instance always-on, stateful)
- sentry-vessel (2 instances min, scales to 20, stateless)

---

## 13. NEXT STEPS (PRIORITY ORDER)

**Phase 1: Cloud Infrastructure (Week 1-2)**
- [ ] GCP project setup
- [ ] Service accounts & IAM roles
- [ ] Cloud SQL instance (PostgreSQL)
- [ ] Secret Manager populated
- [ ] Artifact Registry repo
- [ ] Cloud Load Balancer

**Phase 2: GitHub Actions (Week 2-3)**
- [ ] `.github/workflows/deploy.yml` created
- [ ] Artifact Registry authentication
- [ ] Cloud Run deployment automation
- [ ] Smoke tests in CI/CD
- [ ] Slack notifications

**Phase 3: Senzing Integration (Week 3-4)**
- [ ] Senzing license acquired
- [ ] G2 database schema in Cloud SQL
- [ ] Senzing Docker image configured
- [ ] `/api/entity-resolution` endpoint
- [ ] Integration tests

**Phase 4: VesselAPI Integration (Week 4-5)**
- [ ] AISStream.io or MarineTraffic subscription
- [ ] API key in Secret Manager
- [ ] `/api/h2/vessel-analysis` endpoint
- [ ] ISF Element 9 validation logic
- [ ] Integration tests

**Phase 5: Security Hardening (Week 5-6)**
- [ ] Network policies (VPC, Cloud Armor)
- [ ] RBAC configuration
- [ ] Audit logging setup
- [ ] Backup & disaster recovery
- [ ] Security testing

**Phase 6: Testing & Launch (Week 6-7)**
- [ ] Load testing (1K concurrent users)
- [ ] Performance testing
- [ ] UAT environment setup
- [ ] Documentation & runbooks
- [ ] Incident response procedures

