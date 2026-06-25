# CBP Sentry Test Configuration

Comprehensive pytest fixtures and test configuration for risk model management, API integration, and entity resolution testing.

## Quick Start

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/ -m unit -v

# Integration tests only
pytest tests/ -m integration -v

# API tests
pytest tests/ -m api -v

# Fast tests (< 1 second)
pytest tests/ -m "not slow" -v

# With coverage
pytest tests/ --cov=services --cov=api --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_phase2_integration.py -v
```

## Test Configuration

### pytest.ini
Central configuration for all pytest behavior:

- **Test discovery**: `testpaths = tests services/api/tests api/tests`
- **Asyncio mode**: `auto` (FastAPI async support)
- **Coverage**: Minimum 70% across services and api
- **Markers**: Custom categorization (unit, integration, smoke, slow, database, api, risk_engine, senzing)
- **Logging**: Outputs to `test-results/pytest.log`
- **Timeout**: 30 seconds per test

### conftest.py
Global fixture configuration with async setup:

**Session-scoped fixtures:**
- `event_loop_policy` — Asyncio event loop policy
- `event_loop` — Session-level event loop
- `setup_test_environment` — Environment variable initialization

**Function-scoped fixtures:**
- `db_session` — Temporary SQLite database with seeded test data
- `mock_db_session` — Mocked SQLAlchemy session for unit tests
- `data_service` — RiskModelDataService with test DB
- `api_client` — FastAPI TestClient with mocked dependencies
- `mock_risk_engine` — Mock precise-risk-engine responses
- `mock_senzing` — Mock Senzing entity resolution service
- `mock_vessel_api` — Mock VesselAPI for ship tracking
- `sample_shipment` — Single realistic shipment
- `sample_shipments` — List of 20 test shipments
- `sample_shap_responses` — Sample SHAP explainability responses
- `sample_risk_breakdown` — Sample 3-level risk score breakdown

## Fixtures

### Database Fixtures

#### db_session
Creates a temporary SQLite database for integration tests:

```python
@pytest.mark.asyncio
async def test_shipment_storage(db_session):
    # db_session is a SQLAlchemy session with pre-seeded data
    shipments = db_session.query(Shipment).all()
    assert len(shipments) == 100
```

**Includes:**
- 100 shipments across 5 origins (CN, MX, IN, VN, HK)
- 100 risk score predictions with SHAP breakdowns
- 3 model versions (v3.0 active, v3.1 candidate, v2.1 deprecated)

#### mock_db_session
Mock session for unit tests (no database I/O):

```python
def test_service_initialization(mock_db_session):
    service = DataService(db_session=mock_db_session)
    assert service is not None
```

### Service Fixtures

#### data_service
Initialized RiskModelDataService:

```python
@pytest.mark.asyncio
async def test_model_version_fetch(data_service):
    models = await data_service.get_active_models()
    assert len(models) > 0
    assert models[0].version_number == "v3.0"
```

#### api_client
FastAPI TestClient with test configuration:

```python
def test_health_endpoint(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### Mock Service Fixtures

#### mock_risk_engine
Simulates precise-risk-engine v3.0 API:

```python
@pytest.mark.asyncio
async def test_risk_prediction(mock_risk_engine):
    result = await mock_risk_engine.predict(
        {"id": "SHP-000001", "origin_country": "CN"},
        "v3.0"
    )
    assert result['score'] == 0.76
    assert result['shap']['base_score'] == 0.35
```

**Returns:**
```json
{
  "shipment_id": "SHP-000000",
  "model_version": "v3.0",
  "score": 0.76,
  "confidence": 0.91,
  "components": {
    "corridor_score": 0.65,
    "vessel_score": 0.72,
    "manifest_score": 0.81
  },
  "shap": {
    "base_score": 0.35,
    "positive": [
      {"feature": "documentation_risk", "contribution": 0.16},
      {"feature": "routing_risk", "contribution": 0.14}
    ],
    "negative": [
      {"feature": "party_trust_score", "contribution": -0.04}
    ]
  }
}
```

#### mock_senzing
Simulates Senzing entity resolution:

```python
@pytest.mark.asyncio
async def test_entity_resolution(mock_senzing):
    result = await mock_senzing.search_by_attributes({
        "shipper_name": "Shanghai Electronics",
        "origin_country": "CN"
    })
    assert result['resolved_entities'][0]['entity_id'] == '1001'
    assert result['resolved_entities'][0]['match_score'] == 85
```

#### mock_vessel_api
Simulates VesselAPI ship tracking:

```python
@pytest.mark.asyncio
async def test_vessel_lookup(mock_vessel_api):
    vessel = await mock_vessel_api.get_vessel_info("9811000")
    assert vessel['vessel_name'] == "EVER GIVEN"
    assert vessel['flag'] == "PK"
```

### Test Data Fixtures

#### sample_shipment
Single realistic shipment for minimal test scenarios:

```python
async def test_shipment_creation(sample_shipment):
    assert sample_shipment['id'] == 'SHP-00142857'
    assert sample_shipment['origin_country'] == 'CN'
    assert sample_shipment['declared_value_usd'] == 45200
```

#### sample_shipments
List of 20 diverse shipments (fixtures/shipments.json):

```python
async def test_shipment_batch_processing(sample_shipments):
    assert len(sample_shipments) == 20
    
    # Origins: CN, VN, IN, MX, HK, PA, TH, MY, ID, BR, PH
    origins = {s['origin_country'] for s in sample_shipments}
    assert 'CN' in origins
    assert 'VN' in origins
```

**Covers:**
- Electronics (CN, HK)
- Textiles (CN, VN, IN, PK)
- Chemicals (TH, BR)
- Pharmaceuticals (IN)
- Auto parts (MX)
- Agricultural (PA, MY)
- Semiconductors (PH)

#### sample_shap_responses
SHAP explainability for 5 shipments (fixtures/shap_responses.json):

```python
def test_shap_interpretation(sample_shap_responses):
    response = sample_shap_responses[0]  # SHP-000001
    assert response['score'] == 0.58
    assert 'documentation_risk' in response['features']
    assert response['risk_level'] == 'MEDIUM'
```

**Includes:**
- Low risk (SHP-000004): USMCA auto parts
- Medium risk (SHP-000001): Electronics with doc gaps
- High risk (SHP-000003): Pharmaceuticals, new supplier
- Critical risk (SHP-000017): Semiconductors w/ export controls

#### sample_risk_breakdown
3-level scoring components:

```python
def test_risk_breakdown_structure(sample_risk_breakdown):
    assert 'corridor_score' in sample_risk_breakdown
    assert 'vessel_score' in sample_risk_breakdown
    assert 'manifest_score' in sample_risk_breakdown
```

## Test Markers

Use markers to categorize and run specific test types:

```python
@pytest.mark.unit
def test_model_parsing():
    """Fast unit test"""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_integration():
    """Full integration test"""
    pass

@pytest.mark.slow
def test_full_pipeline():
    """Tests taking > 1 second"""
    pass

@pytest.mark.smoke
def test_service_health():
    """Basic health checks"""
    pass

@pytest.mark.database
async def test_with_db(db_session):
    """Tests requiring database"""
    pass

@pytest.mark.risk_engine
async def test_engine_integration(mock_risk_engine):
    """Tests requiring risk engine"""
    pass

@pytest.mark.senzing
async def test_entity_resolution(mock_senzing):
    """Tests requiring Senzing"""
    pass
```

## Test Fixtures Directory

```
tests/
├── conftest.py                  # Global pytest configuration
├── README.md                    # This file
├── fixtures/
│   ├── __init__.py             # Fixture utilities
│   ├── shipments.json          # 20 realistic shipments
│   └── shap_responses.json     # SHAP explanations for 5 shipments
├── integration/
│   ├── __init__.py
│   └── test_risk_model_management.py
└── test_phase2_integration.py
```

## Environment Variables

Test environment configured automatically:

```python
ENVIRONMENT=test
DEBUG=true
DEMO_MODE=true
USE_MOCK_SENZING=true
CBP_API_URL=http://localhost:8000
RISK_ENGINE_URL=http://localhost:8004
DATABASE_URL=sqlite:////tmp/test_cbp_sentry.db
```

## Writing Tests

### Async Test Example

```python
import pytest
from tests.fixtures import get_sample_shipment

@pytest.mark.asyncio
@pytest.mark.integration
async def test_shipment_scoring(api_client, mock_risk_engine):
    """Test complete scoring pipeline"""
    shipment = get_sample_shipment("SHP-000001")
    
    # Call scoring endpoint
    response = api_client.post("/api/score", json=shipment)
    
    assert response.status_code == 200
    data = response.json()
    assert 'score' in data
    assert 'shap' in data
```

### Unit Test Example

```python
from unittest.mock import MagicMock
from services.data.risk_model_data_service import RiskModelDataService

@pytest.mark.unit
def test_model_initialization(mock_db_session):
    """Test service initialization"""
    service = RiskModelDataService(
        db_session=mock_db_session,
        risk_engine_url="http://localhost:8004",
        db_path="/tmp/test.db"
    )
    
    assert service.db_session == mock_db_session
    assert service.risk_engine_url == "http://localhost:8004"
```

### Database Test Example

```python
@pytest.mark.database
async def test_shipment_retrieval(db_session):
    """Test shipment from database"""
    from sqlalchemy import select
    from services.data.models import Shipment
    
    result = db_session.execute(
        select(Shipment).limit(1)
    )
    shipment = result.scalar_one()
    
    assert shipment is not None
    assert shipment.id.startswith("SHP-")
```

## Coverage Report

Generate detailed coverage report:

```bash
pytest tests/ --cov=services --cov=api --cov-report=html
open htmlcov/index.html
```

Target: **70% minimum coverage** across services and api modules.

## Troubleshooting

### Async Test Failures

Ensure `@pytest.mark.asyncio` is applied:
```python
@pytest.mark.asyncio
async def test_something():
    pass
```

### Database Locking

Tests use `/tmp/test_cbp_sentry.db` which is cleaned up automatically. If you see lock errors:
```bash
rm -f /tmp/test_cbp_sentry.db
```

### Import Errors

Ensure working directory is project root:
```bash
cd /home/rahulvadera/cbp-sentry
pytest tests/
```

### Mock Service Issues

Verify mock fixture is correctly passed to test:
```python
# Good
async def test_something(mock_risk_engine):
    result = await mock_risk_engine.predict(...)

# Wrong - missing mock parameter
async def test_something():
    # mock_risk_engine not available
    pass
```

## References

- **pytest documentation**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **FastAPI testing**: https://fastapi.tiangolo.com/advanced/testing/
- **SQLAlchemy testing**: https://docs.sqlalchemy.org/orm/session_basics.html
