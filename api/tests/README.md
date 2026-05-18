# Sentry CBP API Tests

## Overview

This directory contains the **Test-Driven Development (TDD) skeleton** for the Sentry CBP Illegal Transshipment Detection API. All tests are written first (RED phase) before implementation.

## Philosophy

**Red → Green → Refactor**

1. **RED**: Write tests that *fail* (no implementation yet)
2. **GREEN**: Implement code to pass tests
3. **REFACTOR**: Improve code while keeping tests green

This repository begins in the **RED phase**. Tests serve as executable specifications.

## Test Structure

### Core Test Modules

| Module | Coverage |
|--------|----------|
| `test_referral_package.py` | Referral JSON generation (Tables 3-1 through 3-14) |
| `test_ingest.py` | Manifest parsing, normalization, HTS extraction |
| `test_entity_resolution.py` | Senzing integration, Neo4j graph construction |
| `test_scoring.py` | 4-tier ML scoring (Tier 1-4) |

### Fixtures

`conftest.py` provides:

- **Database**: In-memory SQLite for isolated tests
- **Async Client**: FastAPI test client
- **Greenfield Case Data**: Complete test data set
  - Manifest fixture
  - 7-node entity graph
  - 6-component score breakdown
  - Expected referral package

### Test Data Reference

The **Greenfield aluminum case** (from ARCHITECTURE.md) is the canonical test case:

```
Shipper: Greenfield Industrial Trading Co., Ltd. (Vietnam)
Consignee: SunPath Energy Distributors LLC (USA)
Commodity: Aluminum extrusions (HTS 7604.10.1000)
COO: Vietnam (declared)
Stuffing: Nansha Terminal, Guangzhou (China) — ISF Element 9
AIS Dwell: 11.2 days (5.3× baseline) — ANOMALY
Confidence Score: 91/100 (HIGH)
Recommended Action: EXAMINE_ON_ARRIVAL
Revenue Impact: ~$26.9k duties
```

## Running Tests

### Prerequisites

```bash
pip install pytest pytest-asyncio httpx pydantic-settings
```

### Run All Tests

```bash
pytest
```

### Run Specific Module

```bash
pytest api/tests/test_referral_package.py -v
```

### Run Specific Test

```bash
pytest api/tests/test_referral_package.py::TestConfidenceScoreCalculation::test_greenfield_confidence_score_is_91 -v
```

### Run with Coverage

```bash
pytest --cov=api --cov-report=html
```

### Run Only Unit Tests (skip integration)

```bash
pytest -m unit
```

### Run Only Async Tests

```bash
pytest -k "async"
```

## Test Organization

### By Concern

- **test_referral_package.py**: Referral package schema and confidence scoring
- **test_ingest.py**: Manifest ingestion pipeline
- **test_entity_resolution.py**: Senzing + Neo4j integration
- **test_scoring.py**: ML scoring tiers

### By Test Class (Arrange-Act-Assert pattern)

Each test module contains test classes organized by functionality:

```python
class TestReferralPackageStructure:
    """Test referral JSON schema"""

class TestConfidenceScoreCalculation:
    """Test score calculation (0-100)"""

class TestXAIAssertions:
    """Test explainable AI narratives"""
```

## Test Patterns

### Fixtures

Fixtures provide reusable test data. From `conftest.py`:

```python
def test_example(greenfield_manifest):
    # greenfield_manifest is automatically injected
    assert greenfield_manifest["bill_id"] == "SAMPLE-BOL-2026-001"
```

### Async Tests

Use `@pytest_asyncio.fixture` and `async def` for async tests:

```python
@pytest_asyncio.fixture
async def async_client():
    # Provides FastAPI test client
    ...

async def test_health(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
```

### Skipped Tests

Many tests are marked `pytest.skip()` for placeholder implementation:

```python
def test_parse_excel_manifest(self):
    """
    GIVEN: Valid Excel manifest file
    WHEN: File is uploaded and parsed
    THEN: Records are extracted without error
    """
    pytest.skip("Implementation pending: Excel parser service")
```

When implementation is ready, remove the `pytest.skip()` line.

### Mocks

Use `@pytest.fixture` + `patch()` for mocking external services:

```python
def test_example(mock_firestore):
    # mock_firestore is a MagicMock
    mock_firestore.collection().document().set.return_value = None
    # ... test code
```

## Greenfield Case Reference

The Greenfield test case maps to ARCHITECTURE.md:

| Item | Reference | Test Fixture |
|------|-----------|--------------|
| Manifest | H3 section | `greenfield_manifest` |
| Entity Graph | Neo4j model | `greenfield_entities` |
| Score Breakdown | Table 3-12 | `greenfield_score_breakdown` |
| Referral Package | Tables 3-1–3-14 | `greenfield_referral_package` |

### Score Breakdown (91/100)

| Tier | Component | Score | Max | Source |
|------|-----------|-------|-----|--------|
| 4 | origin_doc_gap | 23 | 25 | ISF contradiction |
| 1 | party_profile_risk | 15 | 15 | Senzing entity chain |
| 2 | routing_consistency | 14 | 15 | AIS anomaly |
| 3 | commodity_sensitivity | 14 | 15 | LightGBM |
| 3 | historical_pattern | 12 | 15 | LightGBM |
| 4 | time_sensitivity | 13 | 15 | BBN |
| **Total** | | **91** | **100** | |

## Common Assertions

### Referral Package

```python
# Structure
assert "package_id" in package
assert "score" in package
assert 0 <= package["score"] <= 100

# Score breakdown
components_sum = sum(c["score"] for c in package["sections"]["score_breakdown"]["components"])
assert components_sum == package["score"]

# XAI
for component in package["sections"]["score_breakdown"]["components"]:
    assert "description" in component  # Narrative, not just number
```

### Entity Graph

```python
# Entity validation
assert entity["type"] in ["TRADING_COMPANY", "MANUFACTURER", "HOLDING_COMPANY", ...]
assert entity["risk_score"] >= 0 and entity["risk_score"] <= 100

# Relationships
assert len(entities) >= 4  # Minimum: VN, CN, HK, US
```

### Scoring

```python
# Tier 1-4 are present
for component in breakdown["components"]:
    assert component["tier"] in [1, 2, 3, 4]

# No component exceeds max
assert component["score"] <= component["max"]
```

## Compliance & Standards

### WCAG 2.0 AA (API Responses)

API responses must be:
- **Serializable**: Valid JSON with no circular refs
- **Documented**: All fields have descriptions (XAI)
- **Accessible**: Text descriptions for non-text content (e.g., chart data)

Tests verify:
```python
import json
json_str = json.dumps(referral_package)  # Must not raise
```

### 19 CFR Compliance

Tests reference:
- **19 CFR 149.5**: ISF requirements (Element 9 stuffing location)
- **19 CFR 134.1**: Country of origin rules
- **EAPA enforcement cases**: ML training data

## Debugging Failed Tests

### View Full Output

```bash
pytest api/tests/test_referral_package.py -vv --tb=long
```

### Print Statements

```python
def test_example(greenfield_manifest):
    print(f"Manifest: {greenfield_manifest}")  # Visible with -s flag
    pytest -s api/tests/test_referral_package.py::TestExample::test_example
```

### Inspect Fixtures

```python
def test_inspect(greenfield_score_breakdown):
    import pprint
    pprint.pprint(greenfield_score_breakdown)
```

## Coverage Goals

- **api/services/**: 80%+ coverage
- **api/core/**: 75%+ coverage
- **api/main.py**: 90%+ coverage

Current coverage: **TBD** (skeleton phase)

## Next Steps (Implementation)

Once tests are written, follow this sequence:

1. **Week 1**: Implement `api/services/ingest/` (manifest parsing)
2. **Week 2**: Implement `api/services/entity_resolution/` (Senzing wrapper)
3. **Week 3**: Implement `api/services/scoring/` (ML tiers 1-4)
4. **Week 4**: Implement `api/services/referral/` (package generation)

Each module should have corresponding tests that move from RED → GREEN.

## References

- **ARCHITECTURE.md**: Three-horizon design, data models, scoring
- **19 CFR 149.5**: ISF Data Element 9 (stuffing location)
- **EAPA**: Enforcement database for model training
- **Senzing Documentation**: Entity resolution API
- **Neo4j**: Graph database query language (Cypher)
- **Pytest**: Framework documentation

## Questions?

Refer to:
- `conftest.py` — Fixture definitions
- `ARCHITECTURE.md` — System design
- Individual test file docstrings — Specific requirements
