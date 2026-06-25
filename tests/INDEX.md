# CBP Sentry Test Suite - Complete Index

**Status**: Complete and validated
**Date**: June 13, 2026
**Coverage**: 14 fixtures, 8 test markers, 1000+ lines of documentation

## Quick Navigation

### For First-Time Users
1. Start here: [README.md](README.md) — 5-minute overview
2. Then: [EXAMPLES.md](EXAMPLES.md) — Copy-paste test patterns
3. Reference: [FIXTURE_REFERENCE.md](FIXTURE_REFERENCE.md) — Detailed fixture info

### For Running Tests
```bash
# All tests
pytest tests/ -v

# Specific category
pytest tests/ -m integration -v

# With coverage
pytest tests/ --cov=services --cov=api --cov-report=html
```

### For Writing Tests
1. Choose test type: unit, integration, or api
2. Find example: [EXAMPLES.md](EXAMPLES.md)
3. Copy pattern
4. Add assertions
5. Run: `pytest tests/test_mytest.py -v`

## File Structure

```
tests/
├── INDEX.md                       ← You are here
├── README.md                      ← Complete guide (435 lines)
├── EXAMPLES.md                    ← 20+ code examples (496 lines)
├── FIXTURE_REFERENCE.md           ← Detailed reference (454 lines)
├── conftest.py                    ← Fixture definitions (482 lines)
│
├── fixtures/                      ← Test data directory
│   ├── __init__.py               ← Fixture utilities
│   ├── shipments.json            ← 20 realistic shipments (11 KB)
│   └── shap_responses.json       ← 5 SHAP examples (11 KB)
│
├── integration/                   ← Integration tests
│   ├── __init__.py
│   └── test_risk_model_management.py
│
└── test_phase2_integration.py     ← Phase 2 tests
```

## 14 Pytest Fixtures

### Database (2 fixtures)
| Fixture | Scope | Type | Use Case |
|---------|-------|------|----------|
| `db_session` | function | async | Integration tests with real SQLite DB |
| `mock_db_session` | function | sync | Unit tests without database I/O |

**Example:**
```python
@pytest.mark.asyncio
async def test_with_db(db_session):
    shipments = db_session.query(Shipment).all()
    assert len(shipments) == 100
```

### Services (2 fixtures)
| Fixture | Scope | Type | Returns |
|---------|-------|------|---------|
| `data_service` | function | async | RiskModelDataService instance |
| `api_client` | function | sync | FastAPI TestClient |

**Example:**
```python
def test_health_endpoint(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
```

### Mocks (3 fixtures)
| Fixture | Scope | Type | Mocks |
|---------|-------|------|-------|
| `mock_risk_engine` | function | sync | precise-risk-engine API |
| `mock_senzing` | function | sync | Senzing entity resolution |
| `mock_vessel_api` | function | sync | VesselAPI ship tracking |

**Example:**
```python
@pytest.mark.asyncio
async def test_risk_prediction(mock_risk_engine):
    result = await mock_risk_engine.predict(shipment, "v3.0")
    assert result['score'] == 0.76
```

### Test Data (4 fixtures)
| Fixture | Scope | Type | Returns |
|---------|-------|------|---------|
| `sample_shipment` | function | async | Single shipment dict |
| `sample_shipments` | function | async | List of 20 shipments |
| `sample_shap_responses` | function | sync | List of 5 SHAP responses |
| `sample_risk_breakdown` | function | sync | 3-level scoring dict |

**Example:**
```python
def test_shipment_scoring(api_client, sample_shipment):
    response = api_client.post("/api/score", json=sample_shipment)
    assert response.status_code == 200
```

### Setup (3 fixtures)
| Fixture | Scope | Purpose |
|---------|-------|---------|
| `event_loop_policy` | session | Asyncio event loop policy |
| `event_loop` | session | Session-level event loop |
| `setup_test_environment` | session | Test environment variables |

## 8 Test Markers

```python
@pytest.mark.unit              # Fast tests (no services)
@pytest.mark.integration       # Tests requiring services
@pytest.mark.smoke             # Health checks
@pytest.mark.slow              # Tests > 1 second
@pytest.mark.database          # Tests using database
@pytest.mark.api               # Tests using FastAPI
@pytest.mark.risk_engine       # Tests using risk engine
@pytest.mark.senzing           # Tests using entity resolution
```

**Run by marker:**
```bash
pytest tests/ -m integration -v     # Integration only
pytest tests/ -m "not slow" -v      # Exclude slow tests
pytest tests/ -m "api and not slow" -v  # API tests that are fast
```

## Test Data Coverage

### 20 Shipments (fixtures/shipments.json)
**Origins**: CN (5), VN (2), IN (2), MX (1), HK (1), PA (1), TH (1), MY (1), ID (1), BR (1), PH (1)

**Commodities**:
- Electronics: Circuit boards, network equipment, laptops
- Textiles: Clothing, cotton, fabric
- Chemicals: Organic compounds, resins, oils
- Pharmaceuticals: Drug preparations
- Auto Parts: Brake systems
- Agriculture: Coal, soybeans
- Seafood: Shrimp, salmon
- Machinery: Lifting equipment
- Steel: Hot rolled coils
- Semiconductors: Integrated circuits
- Furniture: Wooden office furniture
- Footwear: Leather boots

**Risk Profiles**:
- Low (0.31-0.42): USMCA, established routes
- Medium (0.48-0.58): Documentation gaps, new suppliers
- High (0.64-0.76): Pharma, electronics, restricted items
- Critical (0.82+): Semiconductors with export controls

### 5 SHAP Responses (fixtures/shap_responses.json)
- SHP-000001: Medium risk (0.58) — Electronics documentation gaps
- SHP-000003: High risk (0.71) — Pharmaceutical regulatory issues
- SHP-000004: Low risk (0.31) — Compliant auto parts
- SHP-000010: High risk (0.76) — Price anomalies, AD/CVD
- SHP-000017: Critical risk (0.82) — Semiconductors, export control

## Documentation Overview

### README.md (435 lines)
- Quick start commands
- Fixture descriptions (with all 14 documented)
- Environment variables
- Test patterns
- Troubleshooting guide

**Read this if**: You want to understand how to use fixtures

### EXAMPLES.md (496 lines)
- 20+ ready-to-use test examples
- Unit tests (5 examples)
- Integration tests (4 examples)
- API tests (3 examples)
- End-to-end tests (1 example)
- Async patterns (1 example)
- Parameterization examples (3 examples)

**Read this if**: You want to write a test quickly

### FIXTURE_REFERENCE.md (454 lines)
- Complete dependency tree
- Fixture scope explanation
- All methods and attributes
- 6 usage patterns documented
- Combining fixtures (3 patterns)
- Parameterized fixtures
- Troubleshooting

**Read this if**: You need deep fixture details

## Environment Setup (Automatic)

When you run pytest, these are auto-configured:

```
ENVIRONMENT=test           # Test mode enabled
DEBUG=true                 # Detailed logging
DEMO_MODE=true             # Demo data mode
USE_MOCK_SENZING=true      # Mock Senzing service
CBP_API_URL=http://localhost:8000
RISK_ENGINE_URL=http://localhost:8004
DATABASE_URL=sqlite:////tmp/test_cbp_sentry.db
```

## Common Test Patterns

### Pattern 1: Unit Test
```python
@pytest.mark.unit
def test_business_logic(mock_db_session):
    # No external services needed
    pass
```

### Pattern 2: Database Test
```python
@pytest.mark.database
@pytest.mark.asyncio
async def test_with_database(db_session):
    # Real SQLite database with seeded data
    pass
```

### Pattern 3: API Test
```python
@pytest.mark.api
def test_endpoint(api_client):
    response = api_client.get("/endpoint")
    assert response.status_code == 200
```

### Pattern 4: Service Integration
```python
@pytest.mark.asyncio
async def test_with_service(data_service, db_session):
    # Service + database together
    pass
```

### Pattern 5: Mock External Service
```python
@pytest.mark.asyncio
async def test_with_risk_engine(mock_risk_engine):
    result = await mock_risk_engine.predict(...)
    assert result['score'] > 0
```

## Running Tests

### Basic
```bash
pytest tests/ -v
```

### By Category
```bash
pytest tests/ -m unit -v          # Unit tests only
pytest tests/ -m integration -v   # Integration only
pytest tests/ -m api -v           # API tests only
```

### Exclude Slow Tests
```bash
pytest tests/ -m "not slow" -v
```

### With Coverage
```bash
pytest tests/ --cov=services --cov=api --cov-report=html
open htmlcov/index.html
```

### Specific Test
```bash
pytest tests/test_phase2_integration.py -v
pytest tests/test_phase2_integration.py::test_both_services_healthy -v
```

### Watch Mode (auto-rerun)
```bash
pip install pytest-watch
ptw tests/ -- -v
```

## Pytest Configuration (pytest.ini)

Key settings:
- **Test paths**: tests/, services/api/tests, api/tests
- **Async mode**: auto (FastAPI support)
- **Markers**: 8 custom markers configured
- **Timeout**: 30 seconds per test
- **Coverage**: 70% minimum required
- **Logging**: test-results/pytest.log

## Fixture Scopes Explained

**Session scope** (shared across all tests):
- event_loop_policy
- event_loop
- setup_test_environment

**Function scope** (fresh for each test):
- db_session (auto-cleanup)
- mock_db_session
- data_service
- api_client
- mock_risk_engine
- mock_senzing
- mock_vessel_api
- sample_shipment
- sample_shipments
- sample_shap_responses
- sample_risk_breakdown

## Database Seeding

When db_session is used, a fresh SQLite database is created with:

- **100 shipments** — Diverse origins, commodities, values
- **100 risk scores** — v3.0 model predictions
- **3 model versions** — v3.0 (active), v3.1 (candidate), v2.1 (deprecated)

Auto-cleaned up after test completes.

## Files Changed/Created

| File | Lines | Status |
|------|-------|--------|
| pytest.ini | 64 | Updated |
| tests/conftest.py | 482 | Rewritten |
| tests/fixtures/__init__.py | 46 | Created |
| tests/fixtures/shipments.json | 381 | Created |
| tests/fixtures/shap_responses.json | 203 | Created |
| tests/README.md | 435 | Created |
| tests/EXAMPLES.md | 496 | Created |
| tests/FIXTURE_REFERENCE.md | 454 | Created |
| tests/INDEX.md | 400+ | Created (this file) |
| **Total** | **2,747** | **8 files** |

## Next Steps

1. **Understand fixtures**: Read [README.md](README.md)
2. **See examples**: Review [EXAMPLES.md](EXAMPLES.md)
3. **Write test**: Copy pattern from examples
4. **Run tests**: `pytest tests/test_mytest.py -v`
5. **Add more**: Update conftest.py with custom fixtures
6. **Coverage**: Generate report with `--cov`

## Getting Help

### Error Messages
See **Troubleshooting** in [README.md](README.md)

### Fixture Details
See **Fixture Usage Patterns** in [FIXTURE_REFERENCE.md](FIXTURE_REFERENCE.md)

### Code Examples
See [EXAMPLES.md](EXAMPLES.md) for 20+ patterns

### Python/Pytest Docs
- pytest: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- FastAPI testing: https://fastapi.tiangolo.com/advanced/testing/

## Validation Summary

- ✓ All files created and syntax validated
- ✓ All JSON fixtures properly formatted
- ✓ All Python files compile without errors
- ✓ 14 fixtures covering all test needs
- ✓ 8 custom test markers configured
- ✓ 1,000+ lines of documentation
- ✓ 20+ real-world examples provided
- ✓ Auto-cleanup of all test resources
- ✓ Async support fully configured
- ✓ Ready for immediate use

---

**Test infrastructure complete and validated.**
All fixtures, configuration, and documentation ready for CBP Sentry development.
