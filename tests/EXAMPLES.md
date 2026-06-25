# CBP Sentry Test Examples

Ready-to-use test patterns for unit, integration, and end-to-end testing.

## Unit Tests (No External Dependencies)

### Test Service Initialization

```python
"""Test service initialization with mocked database"""
import pytest
from unittest.mock import MagicMock

@pytest.mark.unit
def test_risk_model_data_service_init(mock_db_session):
    """Verify service initializes with correct configuration"""
    from services.data.db import RiskModelDataService
    
    service = RiskModelDataService(
        db_session=mock_db_session,
        risk_engine_url="http://localhost:8004",
        db_path="/tmp/test.db"
    )
    
    assert service.db_session == mock_db_session
    assert service.risk_engine_url == "http://localhost:8004"
    assert service.db_path == "/tmp/test.db"
```

### Test Risk Score Calculation

```python
"""Test risk scoring logic without database"""
import pytest
from services.api.risk_scoring_engine import RiskScoringEngine

@pytest.mark.unit
def test_three_level_score_calculation():
    """Verify 3-level scoring formula"""
    engine = RiskScoringEngine()
    
    corridor_score = 0.65
    vessel_score = 0.72
    manifest_score = 0.81
    
    weights = {"corridor": 0.3, "vessel": 0.3, "manifest": 0.4}
    
    total_score = (
        corridor_score * weights["corridor"] +
        vessel_score * weights["vessel"] +
        manifest_score * weights["manifest"]
    )
    
    assert 0.70 < total_score < 0.75
    assert total_score == pytest.approx(0.730, rel=0.01)
```

### Test SHAP Value Parsing

```python
"""Test SHAP explanation extraction"""
import pytest

@pytest.mark.unit
def test_shap_response_parsing(sample_shap_responses):
    """Verify SHAP response structure and content"""
    response = sample_shap_responses[0]
    
    # Validate top-level structure
    assert 'shipment_id' in response
    assert 'model_version' in response
    assert 'score' in response
    assert 'features' in response
    assert 'positive_factors' in response
    assert 'negative_factors' in response
    
    # Verify feature contributions sum correctly
    base_value = response['base_value']
    contributions = sum(
        f['contribution'] for f in response['positive_factors']
    ) + sum(
        f['contribution'] for f in response['negative_factors']
    )
    
    reconstructed_score = base_value + contributions
    assert reconstructed_score == pytest.approx(response['score'], rel=0.01)
```

### Test Input Validation

```python
"""Test shipment data validation"""
import pytest
from pydantic import ValidationError
from services.data.models import Shipment, ShipmentCreate

@pytest.mark.unit
def test_shipment_validation():
    """Verify required shipment fields"""
    # Valid shipment
    valid_data = {
        'manifest_id': 'MAN-00001',
        'shipper_name': 'Test Shipper',
        'consignee_name': 'Test Consignee',
        'origin_country': 'CN',
        'destination_country': 'US',
        'hs_code': '8517.62.00',
        'declared_value_usd': 100000,
        'declared_weight_kg': 1000,
        'status': 'received'
    }
    
    shipment = ShipmentCreate(**valid_data)
    assert shipment.manifest_id == 'MAN-00001'
    assert shipment.origin_country == 'CN'
    
    # Invalid shipment (missing required field)
    invalid_data = {
        'manifest_id': 'MAN-00002',
        'shipper_name': 'Test Shipper',
        # Missing consignee_name
    }
    
    with pytest.raises(ValidationError):
        ShipmentCreate(**invalid_data)
```

## Integration Tests (Database Required)

### Test Shipment Storage and Retrieval

```python
"""Test shipment persistence"""
import pytest
from sqlalchemy import select
from services.data.models import Shipment

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_shipment_storage_and_retrieval(db_session):
    """Verify shipments can be stored and retrieved"""
    # Verify seeded data exists
    result = db_session.execute(select(Shipment).limit(10))
    shipments = result.scalars().all()
    
    assert len(shipments) == 10
    assert shipments[0].id.startswith("SHP-")
    assert shipments[0].origin_country in ['CN', 'MX', 'IN', 'VN', 'HK']
    
    # Verify all shipments have required fields
    for shipment in shipments:
        assert shipment.manifest_id is not None
        assert shipment.declared_value_usd > 0
        assert shipment.declared_weight_kg > 0
```

### Test Risk Score Caching

```python
"""Test risk score persistence and retrieval"""
import pytest
from sqlalchemy import select
from services.data.models import RiskScore

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_risk_score_cache(db_session):
    """Verify risk scores are cached properly"""
    # Retrieve cached scores
    result = db_session.execute(
        select(RiskScore)
        .where(RiskScore.current_model_version == 'v3.0')
        .limit(5)
    )
    scores = result.scalars().all()
    
    assert len(scores) > 0
    
    # Verify score structure
    for score in scores:
        assert 0.0 <= score.final_score <= 1.0
        assert score.shipment_id is not None
        assert score.created_at is not None
```

### Test Model Version Tracking

```python
"""Test model version management"""
import pytest
from sqlalchemy import select
from services.data.models import ModelVersion

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_active_model_version(db_session):
    """Verify correct active model is tracked"""
    result = db_session.execute(
        select(ModelVersion)
        .where(ModelVersion.is_active == True)
    )
    active_models = result.scalars().all()
    
    # Should have exactly one active model
    assert len(active_models) == 1
    assert active_models[0].version_number == 'v3.0'
    
    # Verify deprecation tracking
    result = db_session.execute(
        select(ModelVersion)
        .where(ModelVersion.version_number == 'v2.1')
    )
    deprecated = result.scalar_one()
    
    assert deprecated.is_active == False
    assert deprecated.deprecated_at is not None
```

## API Tests (HTTP Endpoints)

### Test Health Endpoint

```python
"""Test API health check"""
import pytest

@pytest.mark.api
@pytest.mark.smoke
def test_health_check(api_client):
    """Verify /health endpoint responds correctly"""
    response = api_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "debug" in data
```

### Test Scoring Endpoint

```python
"""Test shipment scoring endpoint"""
import pytest

@pytest.mark.api
@pytest.mark.asyncio
async def test_score_endpoint(api_client, sample_shipment):
    """Verify /api/score endpoint returns valid score"""
    response = api_client.post(
        "/api/score",
        json=sample_shipment
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert 'shipment_id' in data
    assert 'score' in data
    assert 'confidence' in data
    assert 'shap' in data
    
    # Verify score range
    assert 0.0 <= data['score'] <= 1.0
    assert 0.0 <= data['confidence'] <= 1.0
    
    # Verify SHAP structure
    shap_data = data['shap']
    assert 'base_score' in shap_data
    assert 'positive' in shap_data
    assert 'negative' in shap_data
```

### Test Batch Scoring

```python
"""Test batch scoring endpoint"""
import pytest

@pytest.mark.api
@pytest.mark.asyncio
async def test_batch_score_endpoint(api_client, sample_shipments):
    """Verify batch scoring API"""
    response = api_client.post(
        "/api/score/batch",
        json={"shipments": sample_shipments[:5]}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'results' in data
    assert len(data['results']) == 5
    
    # Verify each result has score
    for result in data['results']:
        assert 'shipment_id' in result
        assert 'score' in result
        assert 0.0 <= result['score'] <= 1.0
```

## End-to-End Tests (Full Pipeline)

### Test Complete Scoring Pipeline

```python
"""Test full shipment-to-score pipeline"""
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_scoring_pipeline(
    api_client,
    db_session,
    mock_risk_engine,
    sample_shipment
):
    """Verify complete shipment processing flow"""
    # Step 1: Create/ingest shipment
    response = api_client.post(
        "/api/ingest",
        json=sample_shipment
    )
    assert response.status_code == 201
    ingested = response.json()
    shipment_id = ingested['id']
    
    # Step 2: Score shipment
    response = api_client.post(
        "/api/score",
        json={"shipment_id": shipment_id}
    )
    assert response.status_code == 200
    scored = response.json()
    
    # Step 3: Verify score cached
    from sqlalchemy import select
    from services.data.models import RiskScore
    
    result = db_session.execute(
        select(RiskScore).where(RiskScore.shipment_id == shipment_id)
    )
    cached = result.scalar_one_or_none()
    
    assert cached is not None
    assert cached.final_score == scored['score']
    
    # Step 4: Retrieve and verify SHAP
    response = api_client.get(f"/api/score/{shipment_id}/explain")
    assert response.status_code == 200
    explanation = response.json()
    
    assert 'shap' in explanation
    assert 'features' in explanation['shap']
```

## Async Test Pattern

### Test Async Risk Engine Integration

```python
"""Test async risk engine integration"""
import pytest
from tests.fixtures import get_sample_shipment

@pytest.mark.asyncio
@pytest.mark.risk_engine
async def test_risk_engine_prediction(mock_risk_engine):
    """Verify risk engine prediction flow"""
    shipment = get_sample_shipment("SHP-000001")
    
    # Call async predict method
    result = await mock_risk_engine.predict(shipment, "v3.0")
    
    # Verify response structure
    assert result['shipment_id'] == "SHP-000001"
    assert result['model_version'] == "v3.0"
    assert result['score'] == 0.76
    assert result['confidence'] == 0.91
    
    # Verify SHAP data
    shap = result['shap']
    assert shap['base_score'] == 0.35
    assert len(shap['positive']) == 3
    assert len(shap['negative']) == 2
    
    # Call async explain method
    explanation = await mock_risk_engine.explain("SHP-000001", "v3.0")
    
    assert explanation['shipment_id'] == "SHP-000001"
    assert 'explanation' in explanation
    assert 'features' in explanation['explanation']
```

## Test with Fixtures

### Test Using Sample Shipments

```python
"""Test against diverse shipment types"""
import pytest

@pytest.mark.parametrize("commodity_type", [
    "ELEC",    # Electronics
    "TEXTL",   # Textiles
    "PHARMA",  # Pharmaceuticals
    "MACH",    # Machinery
    "CHEM"     # Chemicals
])
@pytest.mark.asyncio
async def test_scoring_by_commodity(api_client, commodity_type):
    """Test scoring works for all commodity types"""
    # Use appropriate sample shipment
    from tests.fixtures import load_shipments
    
    shipments = load_shipments()
    # Filter by commodity type
    test_shipments = [
        s for s in shipments
        if commodity_type.lower() in s.get('commodity_name', '').lower()
    ]
    
    if test_shipments:
        response = api_client.post(
            "/api/score",
            json=test_shipments[0]
        )
        assert response.status_code == 200
```

### Test Against SHAP Samples

```python
"""Test SHAP interpretation"""
import pytest

@pytest.mark.parametrize("risk_level", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_risk_level_shap_consistency(sample_shap_responses, risk_level):
    """Verify SHAP explanations match risk level"""
    responses = {r['shipment_id']: r for r in sample_shap_responses}
    
    # Map risk levels to shipment IDs from fixtures
    risk_map = {
        "LOW": "SHP-000004",
        "MEDIUM": "SHP-000001",
        "HIGH": "SHP-000003",
        "CRITICAL": "SHP-000017"
    }
    
    shipment_id = risk_map.get(risk_level)
    if shipment_id in responses:
        response = responses[shipment_id]
        assert response['risk_level'] == risk_level
```

## Running the Examples

Execute specific test:
```bash
pytest tests/EXAMPLES.md::test_health_check -v
```

Run all examples:
```bash
pytest tests/ -k "example" -v
```

Run by test type:
```bash
# Only unit tests
pytest tests/ -m unit -v

# Only integration tests
pytest tests/ -m integration -v

# Only API tests
pytest tests/ -m api -v

# Exclude slow tests
pytest tests/ -m "not slow" -v
```

With coverage:
```bash
pytest tests/ --cov=services --cov-report=html -v
```

Watch mode (auto-rerun on file change):
```bash
pytest-watch tests/ -- -v
```
