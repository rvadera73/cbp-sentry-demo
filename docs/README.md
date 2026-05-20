# CBP Sentry Documentation

## Quick Start
- **Deployment:** See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for Cloud Run setup
- **Architecture:** See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for system design
- **API Reference:** See [`API_CONTRACT.md`](./API_CONTRACT.md) for all endpoints
- **Database:** See [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) for schema details

## Implementation Guides

### Scoring System
- [`THREE_HORIZONS.md`](./THREE_HORIZONS.md) — Three-horizon (H1/H2/H3) scoring architecture
- [`REFERRAL_PACKAGE.md`](./REFERRAL_PACKAGE.md) — 14-table CBP referral package specification

### Data Integration
- [`CORD_INTEGRATION.md`](./CORD_INTEGRATION.md) — CORD RAG (entity resolution) integration
- [`ISF_VESSEL_ARCHIVAL.md`](./ISF_VESSEL_ARCHIVAL.md) — ISF Element 9 vessel tracking integration
- [`SENZING_LICENSING.md`](./SENZING_LICENSING.md) — Senzing entity resolution setup

### Testing & Accessibility
- [`TESTING_STRATEGY.md`](./TESTING_STRATEGY.md) — Unit, integration, and smoke test approach
- [`WCAG_ACCESSIBILITY.md`](./WCAG_ACCESSIBILITY.md) — Federal WCAG 2.1 AA compliance
- [`USWDS_PATTERNS.md`](./USWDS_PATTERNS.md) — U.S. Web Design System patterns

### Demo & Case Studies
- [`GREENFIELD_SEED_DATA.md`](./GREENFIELD_SEED_DATA.md) — Greenfield case study (HIGH risk, 91/100)

## Current Status

**Last Updated:** 2026-05-19

| Component | Status |
|---|---|
| Three-horizon scoring (H1/H2/H3) | ✓ Complete |
| CORD RAG integration | ✓ Complete (244K entities) |
| ISF Element 9 detection | ✓ Complete |
| Case Viewer UI (6 tabs) | ✓ Complete |
| Referral package (14 tables) | ✓ Complete |
| GitHub Actions CI/CD | ✓ Ready (3 bug fixes needed) |
| Cloud Run staging deploy | → In progress |
| Senzing live integration | → Next sprint |

## For Implementation

**See the active plan:** `.claude/plans/cosmic-swinging-allen.md` — Five-phase execution plan for Cloud Run deployment, data consolidation, and bug fixes.

**Key Files:**
- Backend: `services/api/main.py` (deployed), `services/data/main.py` (CRUD layer)
- Frontend: `ui/src/pages/CaseViewerPage.tsx` (investigation dossier)
- Pipeline: `.github/workflows/deploy.yml` (GitHub Actions → Cloud Run)
- Tests: `services/api/tests/` (unit + integration test suite)
- Seed Data: `services/data/seed_data/` (manifest records with ISF fields)
