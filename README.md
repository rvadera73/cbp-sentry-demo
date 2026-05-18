# Sentry CBP — Customs and Border Protection Intelligence Engine

A machine learning-powered pipeline for CBP manifest processing, entity resolution, risk scoring, and knowledge graph construction. Designed to support customs enforcement, illegal transshipment detection, and border security operations.

## Architecture

```
Manifest Ingest → Entity Resolution → Risk Scoring → Knowledge Graph
    ↓                  ↓                   ↓               ↓
  Excel/CSV      Deduplication &     ML Risk Models    Neo4j Network
  FastAPI         Consolidation        (LightGBM)      Visualization
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local dev)
- Node 20+ (for UI)

### Development

```bash
# Start all services
docker-compose up

# API will be available at http://localhost:8000
# UI will be available at http://localhost:3000
# Postgres will be available at localhost:5432
# Neo4j will be available at http://localhost:7474
```

### Local Development (without Docker)

**API:**
```bash
cd api
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python main.py
```

**UI:**
```bash
cd ui
npm install
npm run dev
```

## Project Structure

```
cbp-sentry/
├── api/
│   ├── core/              # Config, database, utilities
│   ├── services/          # Business logic modules
│   │   ├── ingest/        # Manifest ingestion
│   │   ├── entity_resolution/
│   │   ├── scoring/       # Risk scoring models
│   │   ├── referral/      # Output formatting
│   │   └── graph/         # Neo4j knowledge graph
│   ├── models/            # Pydantic schemas
│   ├── tests/             # Unit/integration tests
│   ├── fixtures/          # Test data
│   ├── seed_data/         # Database initialization
│   ├── main.py            # FastAPI entry point
│   ├── requirements.txt
│   └── Dockerfile
├── ui/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API client
│   │   ├── types/         # TypeScript types
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── deploy/
│   ├── gcp/               # GCP Cloud Run / GKE
│   └── aws/               # AWS ECS / CodeBuild
├── scripts/               # Utility scripts
├── docker-compose.yml     # Multi-service orchestration
├── .env.example
└── .gitignore
```

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Key variables:
- `DATABASE_URL` — PostgreSQL connection (Neon schema)
- `NEO4J_URI` — Neo4j database URI
- `CORS_ORIGINS` — Allowed frontend origins
- `API_KEY` — Demo API key
- `DEMO_MODE` — Enable demo data loading

## API Endpoints (TBD)

### Manifest Ingest
- `POST /api/ingest/manifest` — Upload manifest file
- `GET /api/ingest/status/{manifest_id}` — Check ingest status

### Entity Resolution
- `POST /api/entity-resolution/load` — Run ER pipeline
- `GET /api/entity-resolution/results/{manifest_id}` — Get results

### Risk Scoring
- `POST /api/scoring/score` — Score entities
- `GET /api/scoring/why/{entity_id}` — Explain score factors
- `POST /api/referral/package` — Generate referral package

### Knowledge Graph
- `POST /api/graph/build` — Build relationship network
- `GET /api/graph/query` — Query graph

### Health
- `GET /health` — Service health check

## Development Workflow

### Testing
```bash
# Run API tests
cd api
pytest

# Run UI tests
cd ui
npm test
```

### Building for Production

```bash
# Build images
docker-compose build

# Run production compose (adjust as needed)
docker-compose -f docker-compose.prod.yml up
```

## Deployment

### GCP Cloud Run
```bash
gcloud builds submit --config=deploy/gcp/cloudbuild.yaml
```

### AWS ECS
```bash
aws codebuild start-build-batch --project-name sentry-build
```

## Configuration

- **Python dependencies** — `api/requirements.txt`
- **Node dependencies** — `ui/package.json`
- **Tailwind CSS** — `ui/tailwind.config.ts` (USWDS color palette)
- **Database schema** — `api/core/db.py` (auto-initializes)

## Key Technologies

| Layer | Tech Stack |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, Python 3.12, Uvicorn |
| Data | PostgreSQL (Neon), Neo4j, pandas, SQLite (dev) |
| ML/AI | scikit-learn, LightGBM, pgmpy (Bayesian networks) |
| Orchestration | Docker, Docker Compose, GCP Cloud Build / AWS CodeBuild |

## Future Enhancements

- [ ] Advanced entity resolution with Senzing integration
- [ ] Probabilistic graphical models (pgmpy)
- [ ] Real-time streaming with Kafka
- [ ] Multi-factor risk scoring with explainability
- [ ] GraphQL API for knowledge graph queries
- [ ] WebSocket support for live scoring updates

## License

Internal Precise Software tool.

## Support

Contact: [TBD]
