# Sentry CBP Development Guide

## Project Overview

**Sentry CBP** is a machine learning pipeline for Customs and Border Protection (CBP) manifest processing. It ingests CBP declarations, resolves entities, assigns risk scores, and builds knowledge graphs for downstream enforcement operations.

**Demo Workflow:** Manifest Ingest → Entity Resolution → Risk Scoring → Knowledge Graph Visualization

## Stack

- **Frontend:** React 19 + TypeScript + Tailwind CSS + Vite
- **Backend:** FastAPI + Python 3.12 + Uvicorn
- **Data Stores:** PostgreSQL (Neon) + Neo4j (Aura)
- **ML/AI:** scikit-learn, LightGBM, pgmpy, networkx
- **Deployment:** Docker Compose (local), GCP Cloud Run, AWS ECS

## Getting Started

```bash
# Start all services
docker-compose up

# API: http://localhost:8000
# UI: http://localhost:3000
# Postgres: localhost:5432 (sentry_user / sentry_password)
# Neo4j: http://localhost:7474 (neo4j / password)
```

## Architecture

### API Layer (`api/`)
- **Core:** Config (pydantic), database (aiosqlite/PostgreSQL), utilities
- **Services:** Ingest, Entity Resolution, Scoring, Referral, Graph
- **Models:** Pydantic request/response schemas
- **Tests:** Unit and integration tests using pytest

### UI Layer (`ui/`)
- **Components:** Layout (header, stepper), feature pages (ingest, ER, scoring, graph)
- **Types:** TypeScript interfaces for all API responses
- **Services:** Axios-based API client (TBD)
- **Styling:** Tailwind CSS with USWDS color palette (navy #013060, teal #4AC4D3, orange #E6800C)

### Deployment
- **GCP:** Cloud Build pipeline, Cloud Run, GKE
- **AWS:** CodeBuild pipeline, ECS, CodeDeploy

## Development Workflow

### Adding a Feature

1. **Define schemas** in `api/models/schemas.py`
2. **Create routes** in `api/services/{service}/routes.py`
3. **Implement business logic** in `api/services/{service}/logic.py` (TBD)
4. **Add tests** in `api/tests/test_{service}.py`
5. **Update UI** with corresponding page/component in `ui/src/pages/` or `ui/src/components/`
6. **Add TypeScript types** in `ui/src/types/sentry.ts`

### Running Tests

```bash
cd api && pytest --asyncio-mode=auto
cd ui && npm test
```

### Database

- **SQLite** (dev): Auto-initializes from `api/core/db.py`
- **PostgreSQL** (production): Via docker-compose service
- **Schema:** Tables auto-created on startup (manifest_ingests, records, entity_resolutions, scores)

### Configuration

Environment variables in `.env` (copy from `.env.example`):
- `DATABASE_URL` — PostgreSQL connection
- `NEO4J_URI` — Neo4j endpoint
- `CORS_ORIGINS` — Frontend origins
- `DEMO_MODE` — Load sample data on startup

## Code Style

- **Python:** Black formatting, type hints required
- **TypeScript/React:** ESLint + Prettier (TBD)
- **Imports:** Absolute imports preferred (use `@/` alias in UI)
- **API responses:** Always include `success` boolean + `data` or `error`

## Key Files

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI app entry point |
| `api/core/config.py` | Environment configuration |
| `api/core/db.py` | Database initialization & connection pool |
| `api/models/schemas.py` | Request/response schemas |
| `ui/src/App.tsx` | React Router setup |
| `ui/tailwind.config.ts` | Tailwind theme (colors, fonts) |
| `docker-compose.yml` | Local development orchestration |
| `.env.example` | Environment template |

## TODO

- [ ] Implement service routers (ingest, ER, scoring, referral, graph)
- [ ] Add entity resolution business logic (deduplication, matching)
- [ ] Implement risk scoring models (LightGBM pipelines)
- [ ] Build Neo4j graph construction logic
- [ ] Add Senzing integration (optional)
- [ ] Implement UI pages with API calls
- [ ] Add comprehensive test suite
- [ ] Configure GCP / AWS deployments
- [ ] Add CI/CD pipelines (GitHub Actions, GitLab CI)
- [ ] Performance optimization (caching, async processing)

## Useful Commands

```bash
# Development
docker-compose up                    # Start all services
docker-compose logs -f api           # Watch API logs
docker-compose exec api bash         # Shell into API container

# API
curl http://localhost:8000/health    # Health check
pytest api/tests/                    # Run tests
python api/main.py                   # Run locally

# UI
npm run dev                           # Dev server
npm run build                         # Production build
npm test                              # Run tests

# Database
docker-compose exec postgres psql -U sentry_user -d sentry_cbp  # Connect to DB
```

## References

- FastAPI: https://fastapi.tiangolo.com
- React 19: https://react.dev
- Tailwind CSS: https://tailwindcss.com
- Pydantic: https://docs.pydantic.dev
- Docker Compose: https://docs.docker.com/compose
