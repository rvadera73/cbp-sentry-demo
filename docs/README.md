# CBP Sentry Documentation

**Updated:** 2026-05-23 | **Version:** 2.0

---

## Three Canonical Documents

This directory contains the authoritative documentation for CBP Sentry. Start here:

### 1. **[ARCHITECTURE.md](ARCHITECTURE.md)** — System Architecture

For engineers, DevOps, and integration partners.

- Service topology (4 Python services + optional Senzing)
- Data flow diagrams (manifest → risk scoring → officer decision)
- Risk scoring engine (7-factor ML model, Three-Horizon pipeline)
- Entity resolution (CORD 21M records, Senzing SDK integration)
- External integrations (Gemini Pro, Altana Atlas, OFAC/SDN)
- Security model (JWT auth, role-based access, encryption)
- Network architecture (Docker network, Cloud Run service mesh)

### 2. **[DESIGN.md](DESIGN.md)** — Solution & Application Design

For product owners, architects, UI/UX leads, and AI/ML engineers.

- Problem statement & solution vision (reduce investigation time from weeks to hours)
- Feature inventory (12 major features with purpose/data sources)
- UI architecture (component hierarchy, state ownership model)
- Investigation Workspace (6-tab design with 16 statutory tables)
- AI Analysis design (Gemini Pro integration for narratives + chat)
- Risk Score Analysis deep dive (7-factor formula, Three-Horizon pipeline, calibration)
- Referral Package workflow (4-stage progress bar with stage gates)
- Data visualization patterns (Recharts, USWDS design system)

### 3. **[DEPLOYMENT.md](DEPLOYMENT.md)** — Deployment Guide

For DevOps engineers and operators.

- Local development (Vite dev server + manual service startup)
- Local Docker production build (docker-compose with all 4 services)
- Cloud Run staging with SQLite (4 separate services, GCS bucket persistence)
- Cloud Run production with PostgreSQL + Cloud SQL (full-scale setup)
- Environment variables reference (all services, secrets vs. plain)
- CI/CD pipeline (GitHub Actions OIDC → Artifact Registry → Cloud Run)
- Rollback procedures (traffic splitting, SQLite backups)
- Monitoring, logs, and troubleshooting

---

## Getting Started

**For local development:**
```bash
# Clone and setup
git clone https://github.com/rahulvadera/cbp-sentry.git
cd cbp-sentry

# Option 1: Docker Compose (production build)
docker compose build --no-cache
docker compose up -d
# Open http://localhost:3001

# Option 2: Manual services (Vite dev server)
# See DEPLOYMENT.md § 2 for detailed instructions
cd services/data && uvicorn main:app --port 8005 --reload
# (in new terminal)
cd services/api && uvicorn main:app --port 8000 --reload
# (in new terminal)
cd services/cord-integration && uvicorn main:app --port 8004 --reload
# (in new terminal)
cd ui && npm run dev
# Open http://localhost:5173
```

**For Cloud Run staging:**
```bash
# One-time setup
bash scripts/setup_gcp_staging.sh

# Build and push images
export PROJECT_ID=$(gcloud config get-value project)
docker build -f services/api/Dockerfile \
  -t us-central1-docker.pkg.dev/${PROJECT_ID}/cbp-sentry/sentry-api:latest \
  services/api/ && docker push ...
# (See DEPLOYMENT.md § 4.3 for full commands)

# Deploy services
gcloud run deploy sentry-data --image ... # See DEPLOYMENT.md § 4.5+
```

---

## Document Quick Links

| Need | Document | Section |
|---|---|---|
| How services communicate | ARCHITECTURE.md | § 3, 9 |
| Risk scoring math | DESIGN.md | § 6 |
| Database schema | ARCHITECTURE.md | § 4 |
| UI component hierarchy | DESIGN.md | § 3 |
| Altana integration | DESIGN.md | § 6 |
| Local Docker setup | DEPLOYMENT.md | § 3 |
| Cloud Run setup | DEPLOYMENT.md | § 4 |
| Entity resolution | ARCHITECTURE.md | § 6 |
| Referral package workflow | DESIGN.md | § 7 |
| API key configuration | DEPLOYMENT.md | § 5 |
| Monitoring & logs | DEPLOYMENT.md | § 9 |

---

## Architecture at a Glance

```
Browser (React 19 + Vite)
  ↓
sentry-ui:3001 (nginx)
  ↓
sentry-api:8000 (FastAPI)
  ├─ sentry-data:8005 (SQLite CRUD)
  ├─ sentry-cord-integration:8004 (CORD 21M entities)
  └─ External APIs (Gemini, Altana, OFAC)

Deployment:
  • Local: Docker Compose
  • Staging: Cloud Run (SQLite on GCS FUSE)
  • Production: Cloud Run (PostgreSQL via Cloud SQL)
```

---

## Key Technologies

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | React + TypeScript + Vite | 19 + 5.6 + 5.4 |
| **Backend API** | FastAPI + uvicorn | 0.115 + 0.30 |
| **Backend Data** | SQLite (dev/staging) / PostgreSQL (prod) | 3.x / 15+ |
| **Entity Resolution** | CORD RAG + Senzing SDK | 21M records + 3.x |
| **AI** | Google Gemini Pro | Latest |
| **Containerization** | Docker + Docker Compose | 24+ / 2.20+ |
| **Cloud Platform** | Google Cloud Run | Latest |
| **CI/CD** | GitHub Actions + Cloud Build | Latest |

---

## Support & Contribution

For questions or issues:
1. Check the relevant document above (Architecture, Design, or Deployment)
2. Review [`ARCHITECTURE.md § 12`](ARCHITECTURE.md#12-health--observability) for health checks
3. File an issue on GitHub: https://github.com/rahulvadera/cbp-sentry/issues

For changes:
1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and test locally (see DEPLOYMENT.md § 2-3)
3. Submit PR against `main`

---

**Last Updated:** 2026-05-23 | **Maintained by:** CBP Sentry Team
