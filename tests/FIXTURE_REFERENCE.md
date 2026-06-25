# Pytest Fixture Reference

Complete fixture dependency graph and usage guide.

## Fixture Dependency Tree

```
session (setup)
├── event_loop_policy
│   └── event_loop
└── setup_test_environment

function (per test)
├── db_session (depends on nothing)
│   ├── data_service (depends on db_session)
│   └── tests using real database
│
├── mock_db_session (depends on nothing)
│   └── tests mocking database
│
├── api_client (depends on mock_db_session)
│   └── FastAPI endpoint tests
│
├── mock_risk_engine (depends on nothing)
│   └── tests mocking risk engine
│
├── mock_senzing (depends on nothing)
│   └── tests mocking entity resolution
│
├── mock_vessel_api (depends on nothing)
│   └── tests mocking vessel API
│
└── Test data fixtures (depend on nothing)
    ├── sample_shipment
    ├── sample_shipments
    ├── sample_shap_responses
    └── sample_risk_breakdown
```

## Fixture Quick Lookup

### By Category

#### Database Fixtures
| Fixture | Scope | Type | Returns | Purpose |
|---------|-------|------|---------|---------|
| `db_session` | function | async | SQLAlchemy Session | Real SQLite DB with seeded data |
| `mock_db_session` | function | sync | MagicMock | Mocked database for unit tests |

#### Service Fixtures
| Fixture | Scope | Type | Returns | Purpose |
|---------|-------|------|---------|---------|
| `data_service` | function | async | RiskModelDataService | Initialized service with test DB |
| `api_client` | function | sync | TestClient | FastAPI test client |

#### Mock Service Fixtures
| Fixture | Scope | Type | Returns | Purpose |
|---------|-------|------|---------|---------|
| `mock_risk_engine` | function | sync | MagicMock | Mocks risk engine API |
| `mock_senzing` | function | sync | MagicMock | Mocks entity resolution |
| `mock_vessel_api` | function | sync | MagicMock | Mocks ship tracking |

#### Test Data Fixtures
| Fixture | Scope | Type | Returns | Purpose |
|---------|-------|------|---------|---------|
| `sample_shipment` | function | async | dict | Single test shipment |
| `sample_shipments` | function | async | list | 20 test shipments |
| `sample_shap_responses` | function | sync | list | SHAP explanations |
| `sample_risk_breakdown` | function | sync | dict | 3-level score structure |

## Fixture Usage Patterns

### Pattern 1: Database Test (Integration)

```python
@pytest.mark.integration
@pytest.mark.database
async def test_database_operation(db_session):
    """Test with real SQLite database"""
    # db_session is a SQLAlchemy session
    # Auto-cleaned up after test
    pass
```

### Pattern 2: Unit Test (No Database)

```python
@pytest.mark.unit
def test_business_logic(mock_db_session):
    """Test logic without database I/O"""
    # mock_db_session is a MagicMock
    # No actual database needed
    pass
```

### Pattern 3: API Test (HTTP)

```python
@pytest.mark.api
def test_endpoint(api_client):
    """Test FastAPI endpoint"""
    response = api_client.get("/health")
    # api_client is TestClient
    # Already includes mock dependencies
    pass
```

### Pattern 4: Risk Engine Mock

```python
@pytest.mark.asyncio
async def test_risk_prediction(mock_risk_engine):
    """Test with mocked risk engine"""
    result = await mock_risk_engine.predict(
        {"id": "SHP-000001"},
        "v3.0"
    )
    # mock_risk_engine returns realistic responses
    pass
```

### Pattern 5: Service Integration

```python
@pytest.mark.asyncio
async def test_service(data_service, db_session):
    """Test service with real database"""
    # data_service is initialized and ready
    # db_session provides database access
    pass
```

### Pattern 6: Async Data Test

```python
@pytest.mark.asyncio
async def test_with_test_data(sample_shipments):
    """Test using fixture test data"""
    # sample_shipments loaded from JSON
    assert len(sample_shipments) == 20
    # Each shipment is a complete dict
    pass
```

## Fixture Methods & Attributes

### db_session Methods

```python
async def test_db_methods(db_session):
    # Query operations
    result = db_session.execute(select(Shipment))
    shipments = result.scalars().all()
    
    # Add/update operations
    db_session.add(new_shipment)
    db_session.commit()
    
    # Rollback on error
    db_session.rollback()
    
    # Close session
    db_session.close()  # Auto-called after test
```

### mock_risk_engine Methods

```python
@pytest.mark.asyncio
async def test_engine_methods(mock_risk_engine):
    # Prediction
    score = await mock_risk_engine.predict(
        shipment={"id": "SHP-001"},
        model_version="v3.0"
    )
    # Returns: {score, confidence, latency_ms, components, shap}
    
    # Explanation
    explain = await mock_risk_engine.explain(
        shipment_id="SHP-001",
        model_version="v3.0"
    )
    # Returns: {shipment_id, model_version, explanation}
```

### mock_senzing Methods

```python
@pytest.mark.asyncio
async def test_senzing_methods(mock_senzing):
    # Entity search
    result = await mock_senzing.search_by_attributes({
        "shipper_name": "Test Co.",
        "origin_country": "CN"
    })
    # Returns: {resolved_entities, possible_matches}
```

### api_client Methods

```python
def test_api_methods(api_client):
    # GET request
    response = api_client.get("/health")
    
    # POST request
    response = api_client.post(
        "/api/score",
        json={"shipment": {...}}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    
    # Headers
    response = api_client.get(
        "/endpoint",
        headers={"Authorization": "Bearer token"}
    )
```

## Fixture Scope Explanation

### Session Scope
- Created once per test session
- Shared across all tests
- Not cleaned up between tests
- Used for: event loop, environment setup

### Function Scope
- Created fresh for each test
- Isolated from other tests
- Cleaned up after test completes
- Used for: database, services, mocks, test data

## Combining Fixtures

### Multi-Fixture Pattern 1: Database + API

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_with_database(
    api_client,
    db_session,
    sample_shipment
):
    """Test API endpoint with real database"""
    # api_client: TestClient
    # db_session: SQLAlchemy session
    # sample_shipment: Test data
    
    # Create shipment via API
    response = api_client.post(
        "/api/ingest",
        json=sample_shipment
    )
    
    # Verify stored in database
    assert db_session.query(Shipment).count() > 0
```

### Multi-Fixture Pattern 2: Service + Mocks

```python
@pytest.mark.asyncio
async def test_service_with_mocks(
    data_service,
    mock_risk_engine,
    mock_senzing
):
    """Test service with all dependencies mocked"""
    # data_service: Initialized service
    # mock_risk_engine: Risk scoring mock
    # mock_senzing: Entity resolution mock
    
    # Service can use both mocks
    pass
```

### Multi-Fixture Pattern 3: All Fixtures

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_integration(
    db_session,
    data_service,
    api_client,
    mock_risk_engine,
    sample_shipments
):
    """Full integration test with all components"""
    # Database with seeded data
    # Service initialized and ready
    # API client for HTTP testing
    # Risk engine mocked for predictions
    # Sample data for test cases
    pass
```

## Parameterized Fixtures

### Test Multiple Shipments

```python
@pytest.mark.parametrize("shipment_id", [
    "SHP-000001",
    "SHP-000002",
    "SHP-000003"
])
@pytest.mark.asyncio
async def test_shipment_scoring(
    api_client,
    shipment_id
):
    """Test scoring for multiple shipments"""
    from tests.fixtures import get_sample_shipment
    
    shipment = get_sample_shipment(shipment_id)
    response = api_client.post("/api/score", json=shipment)
    assert response.status_code == 200
```

### Test Multiple Risk Levels

```python
@pytest.mark.parametrize("shap_id", [
    "SHP-000001",  # MEDIUM
    "SHP-000003",  # HIGH
    "SHP-000004",  # LOW
    "SHP-000017"   # CRITICAL
])
def test_risk_level_validation(
    sample_shap_responses,
    shap_id
):
    """Test SHAP for all risk levels"""
    from tests.fixtures import get_sample_shap_response
    
    response = get_sample_shap_response(shap_id)
    assert response is not None
    assert response['risk_level'] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
```

## Environment Setup (Auto-applied)

Fixtures automatically configure these environment variables:

```
ENVIRONMENT=test
DEBUG=true
DEMO_MODE=true
USE_MOCK_SENZING=true
CBP_API_URL=http://localhost:8000
RISK_ENGINE_URL=http://localhost:8004
DATABASE_URL=sqlite:////tmp/test_cbp_sentry.db
```

Access in test:

```python
import os

def test_env_vars():
    assert os.getenv("ENVIRONMENT") == "test"
    assert os.getenv("DEBUG") == "true"
```

## Fixture Cleanup

All fixtures are automatically cleaned up:

- **db_session**: Database file deleted after test
- **api_client**: Dependency overrides cleared
- **mock_***: Garbage collected

No manual cleanup needed in tests.

## Troubleshooting Fixtures

### "fixture not found" error

Ensure fixture is imported or in conftest.py:

```python
# Good - fixture in conftest.py or imported
async def test_something(db_session):
    pass

# Bad - fixture not available
async def test_something(nonexistent_fixture):
    pass
```

### "object is not awaitable"

Async fixtures must be awaited in async tests:

```python
# Good - async fixture in async test
@pytest.mark.asyncio
async def test_something(db_session):
    # db_session is ready to use
    pass

# Good - async fixture in sync test (auto-awaited)
def test_something(sample_shipment):
    # sample_shipment is already a dict
    pass
```

### Database not seeding

Verify database file permissions:

```bash
# If /tmp/test_cbp_sentry.db is locked
rm -f /tmp/test_cbp_sentry.db
pytest tests/ -v
```

### Mocks not working

Verify mock fixture is passed to test:

```python
# Good
async def test_risk_engine(mock_risk_engine):
    result = await mock_risk_engine.predict(...)

# Missing mock parameter
async def test_risk_engine():
    # mock_risk_engine not available
    pass
```

## Best Practices

1. **Use most specific fixture needed**: Don't use `db_session` if `mock_db_session` is sufficient
2. **Keep fixtures focused**: Each fixture should do one thing well
3. **Document fixture purpose**: Add docstring explaining what it does
4. **Test isolation**: Use function scope to ensure test isolation
5. **Mock external services**: Don't call real APIs in tests
6. **Seed diverse data**: Test data covers edge cases (low/high risk)
7. **Clean up resources**: Fixtures auto-cleanup, but verify manually if needed

## See Also

- [tests/README.md](README.md) — Complete fixture documentation
- [tests/EXAMPLES.md](EXAMPLES.md) — Ready-to-use test patterns
- [pytest.ini](../pytest.ini) — Test configuration
- [conftest.py](conftest.py) — Fixture implementation
