# Sentry — CBP Illegal Transshipment Detection MVP

A serverless AI-powered platform for detecting illegal transshipment of goods through false country-of-origin declarations. Built for CBP's CSOP-BP-GS-26-0001 Illegal Transshipment Pilot.

## Quick Links

- **Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md) — Three Horizon design, Firestore + Neo4j + Senzing + LLM
- **Live Demo**: Will be deployed to Cloud Run (TBD)
- **GitHub**: [rvadera73/cbp-sentry](https://github.com/rvadera73/cbp-sentry)

## What It Does

Sentry detects illegal transshipment via **three sequential intelligence horizons**:

1. **Horizon 1 — Structural Corridor Intelligence** (Daily, runs in background)
   - Pre-classifies high-risk trade corridors using Comtrade/GACC/USITC data
   - Example: "China→Vietnam→US aluminum extrusions" = CRITICAL STRUCTURAL RISK
   - Intelligence exists before any shipment is booked

2. **Horizon 2 — Pre-Manifest ISF & Maritime Intelligence** (14-22 days before arrival)
   - Analyzes ISF Data Element 9 (container stuffing location) for origin fraud
   - Processes AIS vessel tracking for routing anomalies
   - Flags issues weeks before the manifest arrives

3. **Horizon 3 — 72-Hour Manifest Trigger** (When manifest received)
   - Full Senzing entity resolution across shipper/consignee networks
   - 4-tier AI risk scoring (entity chains → anomaly detection → supervised classification → Bayesian reasoning)
   - LLM-generated referral package with XAI transparency

## Four-Part Live Demo

1. **Manifest Ingestion** — Upload sample CBP manifest (Excel, password-protected)
2. **Entity Resolution** — Senzing surfaces hidden ownership chains (e.g., Vietnam shipper → Chinese parent)
3. **Risk Scoring** — Confidence-scored referral package (0-100 scale, 91/100 = HIGH)
4. **Graph Explorer** — Interactive Neo4j visualization of entity relationships

## Tech Stack

### Backend (Cloud Run)
- **FastAPI** (Python 3.12) + async handlers
- **Senzing v4 SDK** — entity resolution (pre-loaded in container)
- **Vertex AI Gemini 1.5 Pro** — HTS contextualization, XAI narration, manifest analysis
- **scikit-learn** (Isolation Forest) — AIS anomaly detection
- **LightGBM** — transshipment classification
- **pgmpy** — Bayesian Belief Network
- **networkx** — graph algorithms

### Frontend (Cloud Run)
- **React 19 + TypeScript 5.8 + Vite 6**
- **Tailwind CSS v4** — styling
- **Recharts** — score breakdown charts
- **TBD: Graph viz** (react-force-graph or D3.js, pending Neo4j integration)

### Databases (Serverless)
- **Firestore** — manifests, shipment records, scores, referral packages
- **Neo4j Aura Free (GCP)** — entity relationship graph (200K nodes / 400K relationships)
- **Cloud Storage** — Excel uploads, generated referral PDFs

### CI/CD
- **GitHub** → **Cloud Build** → **Artifact Registry** → **Cloud Run**

## Local Development Setup

### Prerequisites
- Docker + Docker Compose v2.27+
- Python 3.12 (for model building)
- Node.js 22+ (for React UI)
- GCP credentials (for Firestore/Vertex AI access)
- Neo4j Aura connection string

### 1. Clone & Install

```bash
git clone https://github.com/rvadera73/cbp-sentry.git
cd cbp-sentry

# Backend dependencies
cd api && pip install -r requirements.txt
cd ..

# Frontend dependencies
cd ui && npm install
cd ..
```

### 2. Build ML Models & Senzing Index

```bash
# Generates Isolation Forest, LightGBM, BBN artifacts
python api/scripts/build_models.py

# Generates Senzing SQLite index (baked into container)
python api/scripts/build_senzing_index.py

# Generates all fixture JSON files (mocked external APIs)
python api/scripts/generate_fixtures.py
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with:
#   FIRESTORE_PROJECT=your-gcp-project
#   SENZING_URL=http://localhost:8250  (for local Senzing container)
#   NEO4J_URI=neo4j+s://your-aura-instance.neo4j.io
#   GEMINI_PROJECT=your-gcp-project
```

### 4. Run Locally (Docker Compose)

```bash
docker-compose up -d

# Services:
#   sentry-api     → http://localhost:8000
#   sentry-ui      → http://localhost:3000
#   senzing        → http://localhost:8250
```

### 5. Run Demo

1. Navigate to `http://localhost:3000`
2. Upload `api/seed_data/sample_manifest_greenfield.xlsx` (password: `CBPDemo2026`)
3. Follow the 4-step demo flow (Ingest → ER → Score → Graph)

## Project Structure

```
api/                          FastAPI backend (Cloud Run service)
├── core/
│   ├── config.py            Pydantic settings from env vars
│   ├── firestore.py         Firestore async client
│   ├── neo4j_client.py      Neo4j Aura connection
│   ├── senzing_client.py    Senzing SDK wrapper
│   └── gemini_client.py     Vertex AI Gemini client
├── horizons/
│   ├── h1_corridor.py       Horizon 1: corridor risk scoring
│   ├── h2_isf_ais.py        Horizon 2: ISF + AIS pre-manifest analysis
│   └── h3_manifest.py       Horizon 3: manifest trigger + full pipeline
├── services/
│   ├── ingest/              Manifest parsing, Excel → structured data
│   ├── entity_resolution/   Senzing integration, Neo4j graph building
│   ├── scoring/             4-tier ML pipeline + XAI assertions
│   ├── referral/            Referral package builder (Tables 3-1 through 3-14)
│   └── graph/               Neo4j queries for Graph Explorer
├── fixtures/                Mocked external API responses (AIS, OpenCorporates, etc.)
├── models/                  Pre-trained ML artifacts (pkl, txt files)
├── seed_data/               Sample manifests, Senzing entity seed, pre-built indices
├── scripts/
│   ├── build_models.py      Trains Isolation Forest, LightGBM, BBN
│   ├── build_senzing_index.py   Pre-loads Senzing entities into SQLite
│   ├── generate_fixtures.py     Generates all mocked API response JSON files
│   └── demo_reset.sh            Resets Firestore + Neo4j for repeat demo runs
└── tests/                   Unit tests

ui/                           React frontend (Cloud Run service)
├── src/
│   ├── pages/
│   │   ├── IngestPage.tsx           Manifest upload + H1/H2 pre-intelligence display
│   │   ├── EntityResolutionPage.tsx Senzing results + Neo4j integration
│   │   ├── ScoringPage.tsx          4-tier score breakdown + AI transparency tab
│   │   └── GraphPage.tsx            Neo4j Graph Explorer
│   ├── components/
│   │   ├── layout/
│   │   │   ├── SentryHeader.tsx
│   │   │   └── HorizonTimeline.tsx   Visual H1/H2/H3 timeline strip
│   │   ├── ingest/
│   │   ├── entity-resolution/
│   │   ├── scoring/
│   │   │   ├── ScoreGauge.tsx       Radial gauge (SVG)
│   │   │   ├── ScoreBreakdown.tsx   Bar chart (Recharts)
│   │   │   ├── ReferralPackage.tsx  Formatted referral document
│   │   │   └── AITransparencyPanel.tsx  Gemini conversational XAI
│   │   └── graph/
│   │       ├── GraphExplorer.tsx
│   │       ├── NodeTooltip.tsx
│   │       └── EntitySidebar.tsx
│   ├── api/sentryClient.ts          Typed fetch wrappers for all API routes
│   └── types/sentry.ts              Shared TypeScript interfaces
└── public/                  Static assets

terraform/                    Infrastructure as Code (GCP)
├── main.tf                  Cloud Run services, Firestore, Neo4j
├── variables.tf
└── outputs.tf

docker-compose.yml           Local dev orchestration
cloudbuild.yaml             Cloud Build CI/CD config
.env.example                Environment variable template
.gitignore
README.md
ARCHITECTURE.md             Detailed technical architecture
```

## Deployment to Google Cloud Run

### 1. Authenticate with GCP

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT
```

### 2. Deploy via Cloud Build

```bash
git push origin main

# Cloud Build automatically triggers on push to main
# Builds docker images → pushes to Artifact Registry → deploys to Cloud Run

# Monitor the build:
gcloud builds log --stream
```

### 3. Verify Deployment

```bash
# Get Cloud Run service URLs
gcloud run services describe sentry-api --region us-central1
gcloud run services describe sentry-ui --region us-central1
```

## Sample Data

Two complete demo cases included:

1. **Greenfield Aluminum** (Primary)
   - HTS 7604.10.1000 (aluminum extrusions)
   - Vietnam shipper → Chinese parent (Senzing resolves)
   - MV Pacific Horizon: 11.2-day Guangzhou dwell
   - Final score: **91/100 HIGH**
   - File: `api/seed_data/sample_manifest_greenfield.xlsx`

2. **Solaria Solar** (Supporting)
   - HTS 8541.40.6020 (solar modules)
   - Malaysia → China parent
   - **Same consignee as Greenfield** (demonstrates cross-case entity linking)
   - File: `api/seed_data/sample_manifest_solaria.xlsx`

All manifests password-protected: `CBPDemo2026`

## Key Features

✅ **Three-Horizon Intelligence** — H1/H2/H3 explicitly modeled as distinct pipeline stages  
✅ **Senzing Entity Resolution** — Hidden ownership chains surfaced via probabilistic matching  
✅ **4-Tier ML Pipeline** — Entity chains → anomaly detection → supervised classification → Bayesian reasoning  
✅ **LLM-Powered XAI** — Vertex AI Gemini explains every score decision in plain English  
✅ **Neo4j Graph Explorer** — Interactive entity relationship graph with "Why Connected" explanations  
✅ **Referral Package** — Structured JSON matching proposal Tables 3-1 through 3-14  
✅ **Serverless Architecture** — Cloud Run + Firestore + Neo4j Aura (no persistent infrastructure)  
✅ **Offline Demo Mode** — All external APIs mocked; runs without internet

## Roadmap

- [ ] **Phase 1** (Days 1-2) — Infrastructure skeleton, Docker Compose, FastAPI health endpoint, React router
- [ ] **Phase 2** (Days 3-4) — Manifest ingestion (Excel parsing, field normalization)
- [ ] **Phase 3** (Days 5-7) — Senzing entity resolution, Neo4j graph building
- [ ] **Phase 4** (Days 8-10) — 4-tier scoring pipeline, Bayesian Belief Network
- [ ] **Phase 5** (Days 11-12) — Graph Explorer UI, "Why Connected" feature
- [ ] **Phase 6** (Days 13-14) — AI Transparency panel, referral package builder, demo polish
- [ ] **Deployment** — Cloud Build CI/CD, Cloud Run services live

## Testing

```bash
# Unit tests
pytest api/tests/

# Integration tests (requires Firestore emulator + Neo4j sandbox)
pytest api/tests/ --integration

# Load test
locust -f api/tests/load_test.py
```

## License

Internal use only — Precise Software Solutions, Inc.

## Support

- Architecture questions: See [ARCHITECTURE.md](./ARCHITECTURE.md)
- Demo questions: See [DEMO.md](./DEMO.md) (TBD)
- GCP setup: See [GCP_SETUP.md](./GCP_SETUP.md) (TBD)
