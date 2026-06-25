# Sentry CBP — Trade Enforcement Intelligence Platform

**Status**: 15% Model Maturity — Active Development  
**Last Updated**: June 24, 2026  
**Primary Corridor:** VN → US (aluminum extrusions HS 7604, solar panels HS 8541)

---

## Quick Summary

Sentry CBP automates **illegal transshipment detection** for CBP officers. Given a manifest of imports, the system:

1. **Parses Excel manifest** → extracts shipper, consignee, HS code, value, vessel
2. **Scores risk across 7 factors** → XGBoost (60%) + rule engine (40%) blend
3. **Generates referral package** → 14-section CBP EAPA dossier with Gemini narratives
4. **Displays Investigation Workspace** → 6-tab officer interface with entity graph + risk breakdown

**Total Risk Score**: 0-100 (HIGH ≥70, MEDIUM 50-69, LOW <50)

---

## Documentation

| Document | Purpose | For Whom |
|----------|---------|----------|
| **[CLAUDE.md](CLAUDE.md)** | Developer guide: ports, commands, architecture, data status | Developers (start here) |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | System design, scoring model, data pipelines, MLOps | Architects, Backend engineers |
| **[docs/DESIGN.md](docs/DESIGN.md)** | UI/UX design, scoring deep-dive, referral workflow | Product Owners, UI/UX, AI/ML |
| **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** | How to deploy locally, staging | DevOps, Operations |
| **[GATES_DEFINITION_AND_CURRENT_STATE.md](GATES_DEFINITION_AND_CURRENT_STATE.md)** | Gate definitions (15%→30%→50%→70%→90%) + current state | All |

> **Note:** Many other `.md` files in the root are historical session notes from prior development
> phases. Treat `CLAUDE.md`, `docs/ARCHITECTURE.md`, and `docs/DESIGN.md` as the canonical references.

---

## Running Locally (5 minutes)

### Prerequisites
```bash
# Check Docker is installed
docker --version  # v24+
docker compose --version  # v2.27+
```

### Start Services
```bash
cd /home/rahulvadera/cbp-sentry
bash deploy.sh
```

**Expected output**:
```
✅ DEPLOYMENT COMPLETE!
   🌐 UI: http://localhost:3000
   🛢️  API: http://localhost:8000
   💾 Data: http://localhost:8005
```

### Test API
```bash
# List shipments (should show 10 demo shipments)
curl http://localhost:8000/api/shipments | python3 -m json.tool

# Score a shipment
SHIPMENT_ID=$(curl -s http://localhost:8000/api/shipments | python3 -c "import sys, json; print(json.load(sys.stdin)['shipments'][0]['id'])")
curl -X POST http://localhost:8000/api/score/$SHIPMENT_ID | python3 -m json.tool
```

### Stop Services
```bash
docker compose down
```

---

## Project Structure

```
cbp-sentry/
├── README.md                          ← You are here
├── PROJECT_STATUS.md                  ← What's complete/blocked
├── ARCHITECTURE.md                    ← System design
├── DEPLOYMENT.md                      ← Deployment guide
│
├── services/
│   ├── api/                           ← FastAPI server (scoring + ingest)
│   │   ├── main.py
│   │   ├── ingest_parser.py           ← Excel parsing + vessel_name extraction
│   │   ├── h3_scorer.py               ← NEW: 25-pt intelligence scorer
│   │   ├── ml_scorers.py              ← H1 corridor + H2 anomaly scoring
│   │   ├── external_apis/             ← Adapters (Comtrade, OpenCorporates, AIS)
│   │   │   ├── h1_adapters.py
│   │   │   ├── h2_adapters.py
│   │   │   └── config.py
│   │   └── Dockerfile
│   │
│   ├── data/                          ← FastAPI data service (SQLite)
│   │   ├── main.py
│   │   ├── db.py
│   │   └── Dockerfile
│   │
│   └── [monitoring, ingest, risk, er]  ← Future microservices (not yet)
│
├── ui/                                ← React frontend (Vite build)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── CaseViewerPage.tsx      ← Main page (6 tabs)
│   │   │   └── UploadPage.tsx          ← Upload modal
│   │   ├── components/
│   │   │   ├── CaseQueue.tsx
│   │   │   ├── RiskGauge.tsx
│   │   │   └── [entity, H1, H2, H3, referral tabs]
│   │   └── services/api.ts
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml                 ← Local orchestration
├── deploy.sh                          ← Deploy + seed data script
├── scripts/
│   ├── build_models.py                ← Train ML models (future)
│   └── demo_reset.sh                  ← Quick reset
│
└── docs/
    ├── REFERRAL_PACKAGE.md            ← 14-table CBP spec
    └── CBP_RESEARCH.md                ← Domain knowledge
```

---

## Current Status (Phase 1: Backend Scoring)

### ✅ Complete
- [x] Ingest parser with vessel_name extraction
- [x] H3 Intelligence Scorer (25-point max)
- [x] Score endpoint rewrite (/api/score/{id})
- [x] Shipments list endpoint (real scores, not hardcoded 58)
- [x] Referral package endpoint (14-table CBP dossier, per-shipment)
- [x] Seed data with varied shipments
- [x] H1 adapter fixture data fixes

### 🚨 Blocked
- ❌ Scoring fails with `UnboundLocalError: pricing_score` error
  - Root cause: ml_scorers.py import path confusion (2 duplicate files)
  - Impact: Can't verify H1/H2/H3 scoring logic
  - Impact: Can't verify DB write-back (PATCH /shipments/{id})
  - Status: Needs consolidation + fresh rebuild

### 📋 Open
- [ ] ml_scorers.py import resolution
- [ ] End-to-end integration test (ingest → score → referral)
- [ ] Case Viewer UI build (6 tabs)
- [ ] Entity resolution (Senzing integration)
- [ ] ML model training

---

## Next Steps (After Documentation Pause)

### Immediate Fix (Hour 1)
1. Delete duplicate `/services/api/external_apis/ml_scorers.py`
2. Consolidate to `/services/api/ml_scorers.py` only
3. Rebuild Docker image
4. Test that `/api/score/{id}` succeeds (no UnboundLocalError)

### MVP Verification (Hour 2-3)
1. Hardcode simple scores (H1=15, H2=12, H3=8 for all shipments)
2. Verify `/api/shipments` shows varied scores (not all 58)
3. Verify `/api/referral/{id}` returns per-shipment data
4. Verify scores persist to DB

### Phase 2: UI Build (Week 2)
1. Case Viewer main page with 6 tabs
2. Upload pipeline modal with progress
3. Entity chain visualization (SVG diagram)
4. H1/H2/H3 intelligence panels
5. Referral package viewer (14 tables, print-friendly)

---

## API Endpoints (v1)

| Method | Path | Purpose | Status |
|--------|------|---------|--------|
| POST | `/api/ingest/manifest` | Upload + parse Excel | ✅ Works |
| POST | `/api/score/{shipment_id}` | Compute H1/H2/H3 | ❌ Blocked (pricing_score error) |
| GET | `/api/shipments` | List all (varied scores) | ⚠️ Partial (shows 58 until scored) |
| GET | `/api/shipments/{id}` | Detail view | ✅ Works |
| GET | `/api/referral/{shipment_id}` | 14-table package | ✅ Works (returns per-shipment) |
| GET | `/api/graph/shipment/{id}` | Entity ownership chain | ✅ Placeholder |

---

## Scoring Model (Three Horizons)

### H1: Corridor Risk (40 pts)
Assesses trade route for inherent evasion incentive.

- High-risk country pair (CN→US, VN→US): 12 pts
- Extreme duty rate (>200% AD/CVD): 10 pts
- Young shipper (<2 years): 8 pts
- Price well below market (<60%): 10 pts

### H2: Anomaly Detection (35 pts)
Detects unusual shipping patterns.

- Extreme AIS dwell (5x baseline): 12 pts
- ISF Element 9 mismatch (declared ≠ stuffing): 12 pts
- AIS signal gaps (>3): 6 pts
- Unusual routing: 5 pts

### H3: Intelligence (25 pts)
External intelligence on risk factors.

- OFAC/SDN hit: 15 pts
- Watch list (3+ EAPA filings): 10 pts
- New importer high volume (<1yr, >$50k): 8 pts
- Volume surge (3x+): 5 pts

**Total**: H1 + H2 + H3 (max 100, capped)

---

## Database Schema

### shipments table
```sql
id (TEXT) — primary key
manifest_id (TEXT) — links to manifest upload
shipper_name, consignee_name, origin_country, destination_country (TEXT)
hs_code, declared_value_usd, declared_weight_kg, vessel_name (TEXT/REAL)
risk_score (INT) — 0-100, NULL until scored
h1_score, h2_score (INT) — 0-40, 0-35
status, created_at (TEXT/TIMESTAMP)
```

---

## Dependencies

### Runtime
- Python 3.12
- FastAPI 0.115
- pandas (Excel parsing)
- httpx (async HTTP)
- aiosqlite (SQLite async)

### Development
- Docker / Docker Compose
- Git
- Node 20 (React build)

### Future (For Advanced Features)
- Senzing v4 (entity resolution)
- scikit-learn (ML models)
- LightGBM (classifier)
- pgmpy (Bayesian networks)

---

## Troubleshooting

### Services won't start
```bash
# Check logs
docker logs sentry-api
docker logs sentry-data

# Clean and rebuild
docker system prune -af --volumes
bash deploy.sh
```

### Scoring fails with pricing_score error
**Root cause**: ml_scorers.py import path issue  
**Workaround**: Delete `/services/api/external_apis/ml_scorers.py`, rebuild

### Shipments show risk_score = 58
**Cause**: Shipments not yet scored  
**Solution**: Call `POST /api/score/{shipment_id}` to compute scores

### Upload hangs
**Cause**: Ingest parser error on malformed Excel  
**Solution**: Check Excel schema: shipper, consignee, origin_country, destination_country, hs_code, value, weight, [optional] vessel_name

---

## Contributing

### Code Style
- Type hints on all functions
- Docstrings on public methods
- Single quotes for strings
- 100-character line limit
- No f-strings in logs (use % formatting)

### Git Workflow
```bash
git checkout -b feature/my-feature
# ... make changes ...
git commit -m "feat: add X feature"
git push origin feature/my-feature
# Create PR
```

### Testing (Future)
```bash
# Run tests
pytest tests/

# Coverage
pytest --cov=services/api tests/

# Smoke tests
bash scripts/smoke_tests.sh
```

---

## Contact & Support

**Lead Engineer**: Rahul Vadera (ravjdpr@gmail.com)  
**Project Deadline**: Apr 24, 2026 (CBP CSOP-BP-GS-26-0001)

---

## References

- [CBP Intelligent Cargo Screening](https://www.cbp.gov/about/accomplishments-and-metrics)
- [EAPA — Enforce and Protect Act](https://www.cbp.gov/trade/eapa)
- [HTS — Harmonized Tariff Schedule](https://usitc.gov/research_and_analysis/harmonized_tariff_schedule_hts)
- [ISF Element 9 — Importer Security Filing](https://www.cbp.gov/border-security/automated-commercial-environment/importer-security-filing-isf)
- [AD/CVD — Anti-Dumping & Countervailing Duty](https://www.usitc.gov/trade_remedy_investigations/antidumping_countervailing_duty)

---

**README Version**: 1.0  
**Status**: Paused for documentation + fresh restart  
**Next Milestone**: May 20, 2026 — Resume with ml_scorers fix
