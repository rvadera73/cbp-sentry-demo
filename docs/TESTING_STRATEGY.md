# Testing Strategy — TDD Approach

## Philosophy

**Test-first discipline** (RED → GREEN → REFACTOR):

1. **RED**: Write failing test first (before implementation)
2. **GREEN**: Implement minimal code to pass test
3. **REFACTOR**: Improve code quality, duplication, clarity

**Never commit untested code.** Before every push:
```bash
npm run test              # Unit + integration tests
npm run test:a11y        # Accessibility tests (jest-axe)
npm run test:e2e         # End-to-end tests (if modified critical paths)
```

---

## Test Coverage Targets

| Category | Target | Notes |
|----------|--------|-------|
| **Unit (models, services)** | 90%+ | Fast, isolated, no I/O |
| **Integration (API routes)** | 80%+ | Database fixtures, mocked external APIs |
| **Accessibility (jest-axe)** | 0 violations | Every component must pass |
| **E2E (full pipeline)** | Greenfield case + 2 control cases | 3 scenarios total |

---

## Test Structure

### Backend Tests (Python, pytest)

```
api/tests/
├── conftest.py                          # Shared fixtures
├── test_h1_corridor.py                  # H1 corridor analysis
├── test_h2_isf_ais.py                   # H2 pre-intelligence
├── test_h3_manifest.py                  # H3 manifest parsing
├── test_senzing_entity_resolution.py    # Entity matching
├── test_scoring_tiers.py                # 4-tier ML scoring
├── test_referral_package.py             # Output format (Tables 3-1 to 3-14)
└── integration/
    ├── test_pipeline_greenfield.py      # Full H1→H2→H3 (Greenfield case)
    ├── test_pipeline_control_cases.py   # Control shipments (low-risk)
    └── test_database_sync.py            # PostgreSQL ↔ Neo4j sync
```

### Frontend Tests (TypeScript, Vitest + jest-axe)

```
ui/src/
├── views/**/__tests__/
│   ├── ManifestTable.spec.tsx           # + accessibility.spec.tsx
│   ├── ScoreGauge.spec.tsx
│   ├── RiskFactors.spec.tsx
│   ├── EntityGraph.spec.tsx
│   └── ReferralDocument.spec.tsx
├── pages/__tests__/
│   ├── IngestPage.spec.tsx
│   ├── ScoringPage.spec.tsx
│   └── ReferralPackagePage.spec.tsx
└── integration/__tests__/
    ├── full_pipeline.spec.tsx           # Upload → Score → Referral
    └── accessibility.spec.tsx           # Page-level a11y
```

---

## Backend Test Patterns

### Pattern 1: Fixture-Based Unit Tests

**File**: `api/tests/test_referral_package.py`

```python
import pytest
from api.services.referral import generate_referral_package
from api.seed_data import greenfield_aluminum

@pytest.fixture
def greenfield_shipment():
    """Load Greenfield test case"""
    return greenfield_aluminum

@pytest.mark.asyncio
async def test_referral_package_greenfield_format(greenfield_shipment):
    """Test referral package structure matches Tables 3-1 to 3-14"""
    
    package = await generate_referral_package(greenfield_shipment)
    
    # Assert structure
    assert 'package_id' in package
    assert 'sections' in package
    assert package['sections'].keys() >= {
        'shipment_identification',      # Table 3-1
        'line_items',                   # Table 3-2
        'routing_history',              # Table 3-3
        'parties_and_roles',            # Table 3-4
        'entity_ownership_chain_senzing', # Table 3-5
        'historical_import_pattern_analysis', # Table 3-6
        'trade_flow_intelligence',      # Table 3-7
        'document_review',              # Table 3-8
        'document_consistency_analysis', # Table 3-9
        'supplier_manufacturing_verification', # Table 3-10
        'risk_indicator_summary',       # Table 3-11
        'risk_score_breakdown',         # Table 3-12
        'what_if_scenarios',            # Table 3-13
        'data_sources_and_uses',        # Table 3-14
    }
    
    # Assert score
    assert package['total_score'] == 91
    assert package['confidence_level'] == 'HIGH'
    
    # Assert evidence completeness
    assert len(package['sections']['risk_indicator_summary']) == 6
    
    # Assert each risk factor is ranked and scored
    for factor in package['sections']['risk_indicator_summary']:
        assert 'indicator' in factor
        assert 'evidence' in factor
        assert 'risk_level' in factor
        assert factor['impact_on_score'] > 0

@pytest.mark.asyncio
async def test_referral_package_score_breakdown(greenfield_shipment):
    """Test 4-tier scoring sums correctly"""
    
    package = await generate_referral_package(greenfield_shipment)
    breakdown = package['sections']['risk_score_breakdown']
    
    # Calculate composite score
    total = sum(c['score'] for c in breakdown['components'])
    assert total == breakdown['total_score']
    
    # Verify weights sum to 100
    total_weight = sum(c['weight_pct'] for c in breakdown['components'])
    assert total_weight == 100


@pytest.mark.asyncio
async def test_referral_package_isf_contradiction(greenfield_shipment):
    """Test ISF Element 9 contradiction is flagged"""
    
    package = await generate_referral_package(greenfield_shipment)
    
    # Find routing history
    routing = package['sections']['routing_history']
    guangzhou_call = next((r for r in routing if 'Guangzhou' in r['location']), None)
    
    assert guangzhou_call is not None
    assert guangzhou_call['dwell_days'] == 11.2
    assert 'DISCREPANCY' in guangzhou_call['notes']
    assert 'ISF' in guangzhou_call['notes']
```

### Pattern 2: Senzing Entity Resolution Tests

**File**: `api/tests/test_senzing_entity_resolution.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from api.services.entity_resolution import resolve_entities_senzing

@pytest.fixture
def mock_senzing_client():
    """Mock Senzing SDK responses"""
    client = AsyncMock()
    
    # Setup shipper resolution (Vietnam entity → Chinese parent)
    client.resolve_entity.side_effect = lambda **kwargs: {
        'shipper_name': {
            'entity_id': 1001,
            'confidence': 0.91,
            'match_keys': ['NAME_ORG', 'REGISTERED_ADDRESS']
        },
        'Greenfield Industrial Trading Co., Ltd.': {
            'entity_id': 1001,
            'confidence': 0.91,
        },
        'Guangdong Greenfield Aluminum Mfg. Co., Ltd.': {
            'entity_id': 1003,
            'confidence': 0.98,
            'prior_cbp_filings': 18,
        }
    }
    return client

@pytest.mark.asyncio
async def test_senzing_shipper_to_parent_linkage(mock_senzing_client):
    """Test Senzing resolves Vietnamese shipper to Chinese parent"""
    
    shipment_data = {
        'shipper_name': 'Greenfield Industrial Trading Co., Ltd.',
        'shipper_address': 'Tran Hung Dao St, HCMC, Vietnam',
        'hts_code': '7604.10.1000',
    }
    
    with patch('api.services.entity_resolution.senzing_client', mock_senzing_client):
        entities = await resolve_entities_senzing(shipment_data)
    
    # Verify entity chain
    assert len(entities) >= 2
    
    shipper = next(e for e in entities if e['entity_id'] == 1001)
    assert shipper['entity_type'] == 'SHIPPER'
    assert shipper['jurisdiction'] == 'Vietnam'
    assert shipper['senzing_confidence'] == 0.91
    
    manufacturer = next(e for e in entities if e['entity_id'] == 1003)
    assert manufacturer['entity_type'] == 'MANUFACTURER'
    assert manufacturer['jurisdiction'] == 'China'
    assert manufacturer['senzing_confidence'] == 0.98
    assert manufacturer['prior_cbp_filings'] == 18


@pytest.mark.asyncio
async def test_senzing_confidence_threshold():
    """Test low-confidence matches are flagged"""
    
    # Mock low-confidence match
    entities = await resolve_entities_senzing({
        'shipper_name': 'Random Company Name',  # Unlikely match
        'shipper_address': 'Unknown Address',
    })
    
    for entity in entities:
        if entity['senzing_confidence'] < 0.70:
            assert 'LOW_CONFIDENCE_FLAG' in entity.get('risk_flags', [])
```

### Pattern 3: 4-Tier Scoring Tests

**File**: `api/tests/test_scoring_tiers.py`

```python
import pytest
from api.services.scoring import (
    score_tier_1_entity_resolution,
    score_tier_2_anomaly_detection,
    score_tier_3_classification,
    score_tier_4_bayesian,
)

@pytest.mark.asyncio
async def test_tier_1_senzing_confidence_to_score():
    """Test Tier 1: Senzing confidence maps to Party Profile Risk score"""
    
    # High confidence (0.91) should yield high score
    score_data = {
        'senzing_confidence': 0.91,
        'component': 'Party Profile Risk',
        'max_points': 15,
    }
    
    result = await score_tier_1_entity_resolution(score_data)
    
    assert result['score'] == 15
    assert result['max'] == 15
    assert result['component'] == 'Party Profile Risk'
    
    # Medium confidence (0.65) should yield medium score
    score_data['senzing_confidence'] = 0.65
    result = await score_tier_1_entity_resolution(score_data)
    
    assert 7 <= result['score'] <= 10  # ~65% of 15
    assert result['basis'].startswith('Senzing confidence')


@pytest.mark.asyncio
async def test_tier_2_ais_dwell_anomaly():
    """Test Tier 2: AIS dwell time anomaly detection"""
    
    shipment_data = {
        'ais_dwell_days': 11.2,
        'ais_dwell_baseline': 2.1,
        'port_code': 'CNGGZ',
        'commodity': 'Aluminum extrusions (HTS 7604.10)',
    }
    
    result = await score_tier_2_anomaly_detection(shipment_data)
    
    assert result['component'] == 'Routing Consistency'
    assert result['score'] >= 13  # 11.2 / 2.1 = 5.3× is highly anomalous
    assert result['anomaly_ratio'] == pytest.approx(5.33, rel=0.01)
    assert result['percentile'] == 99


@pytest.mark.asyncio
async def test_tier_3_lightgbm_classification():
    """Test Tier 3: Supervised classification predicts fraud probability"""
    
    shipment_data = {
        'hts_code': '7604.10.1000',
        'declared_origin': 'VN',
        'shipper_age_days': 104,
        'price_below_market_pct': 15,
        'origin_shift_detected': True,
        'prior_cbp_filings': 0,
    }
    
    result = await score_tier_3_classification(shipment_data)
    
    # Should return two component scores
    assert len(result['components']) == 2
    
    commodity_score = next(c for c in result['components'] if c['component'] == 'Commodity Sensitivity')
    assert commodity_score['score'] >= 13  # HTS 7604.10 is high-risk
    
    pattern_score = next(c for c in result['components'] if c['component'] == 'Historical Pattern Anomaly')
    assert pattern_score['score'] >= 10  # Origin shift detected


@pytest.mark.asyncio
async def test_tier_4_bayesian_network():
    """Test Tier 4: Bayesian network integrates all evidence"""
    
    all_evidence = {
        'h1_corridor_critical': True,
        'h2_isf_contradiction': True,
        'h2_ais_anomaly': True,
        'senzing_linked_to_china': True,
        'price_below_market': True,
    }
    
    result = await score_tier_4_bayesian(all_evidence)
    
    # With all evidence pointing to fraud, probability should be high
    assert result['bayesian_fraud_probability'] >= 0.85
    
    # Score components
    assert len(result['components']) == 2
    
    origin_doc = next(c for c in result['components'] if c['component'] == 'Origin Documentation Gap')
    assert origin_doc['score'] >= 22  # High fraud probability
    
    time_sens = next(c for c in result['components'] if c['component'] == 'Time Sensitivity')
    assert time_sens['score'] >= 12


@pytest.mark.asyncio
async def test_scoring_composite_greenfield():
    """Test full 4-tier scoring produces Greenfield's 91/100"""
    
    from api.seed_data import greenfield_aluminum
    
    result = await score_tier_1_entity_resolution(greenfield_aluminum)
    tier1_score = result['score']  # 15
    
    result = await score_tier_2_anomaly_detection(greenfield_aluminum)
    tier2_score = result['score']  # 14
    
    result = await score_tier_3_classification(greenfield_aluminum)
    tier3_score = sum(c['score'] for c in result['components'])  # 14 + 12 = 26
    
    result = await score_tier_4_bayesian(greenfield_aluminum)
    tier4_score = sum(c['score'] for c in result['components'])  # 23 + 13 = 36
    
    total = tier1_score + tier2_score + tier3_score + tier4_score
    assert total == 91
```

### Pattern 4: End-to-End Pipeline Tests

**File**: `api/tests/integration/test_pipeline_greenfield.py`

```python
import pytest
from api.horizons import h1_corridor, h2_isf_ais, h3_manifest
from api.services.referral import generate_referral_package
from api.seed_data import greenfield_aluminum

@pytest.mark.asyncio
async def test_full_pipeline_greenfield():
    """Test H1 → H2 → H3 pipeline with Greenfield case"""
    
    # H1: Corridor analysis
    corridor_risk = await h1_corridor.analyze_corridor(
        hts_6='760410',
        origin='CN',
        destination='US',
        intermediate='VN',
    )
    
    assert corridor_risk['risk_level'] == 'CRITICAL_STRUCTURAL_RISK'
    assert corridor_risk['evasion_incentive_pct'] >= 300
    
    # H2: ISF + AIS intelligence
    h2_data = await h2_isf_ais.process_isf_ais(
        bill_id='SAMPLE-BOL-2026-001',
        isf_element_9_location='Guangzhou, China',
        declared_origin='Vietnam',
        vessel_ais_data={
            'dwell_days': 11.2,
            'port': 'CNGGZ',
        }
    )
    
    assert h2_data['isf_contradiction'] == True
    assert h2_data['ais_anomaly_ratio'] == pytest.approx(5.33, rel=0.01)
    
    # H3: Full assessment
    shipment = await h3_manifest.parse_and_score(greenfield_aluminum)
    
    assert shipment['h3_total_score'] == 91
    assert shipment['h3_confidence_level'] == 'HIGH'
    assert shipment['recommended_action'] == 'EXAMINE_ON_ARRIVAL'
    
    # Referral package generation
    package = await generate_referral_package(shipment)
    
    assert package['total_score'] == 91
    assert package['confidence_level'] == 'HIGH'
    assert len(package['sections']) == 14  # Tables 3-1 to 3-14
```

---

## Frontend Test Patterns

### Pattern 1: Component Unit Tests

**File**: `ui/src/views/manifest/__tests__/ManifestTable.spec.tsx`

```typescript
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import ManifestTable from '../ManifestTable';

expect.extend(toHaveNoViolations);

describe('ManifestTable', () => {
  const manifests = [
    {
      bill_of_lading: 'SAMPLE-BOL-2026-001',
      shipper_name: 'Greenfield Industrial Trading Co., Ltd.',
      hts_code: '7604.10.1000',
      weight_kg: 26200,
      value_usd: 72030,
      status: 'IN_TRANSIT',
    },
  ];

  it('renders table with headers', () => {
    render(<ManifestTable manifests={manifests} />);

    expect(screen.getByRole('columnheader', { name: /Bill of Lading/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Shipper/i })).toBeInTheDocument();
  });

  it('displays manifest data in rows', () => {
    render(<ManifestTable manifests={manifests} />);

    expect(screen.getByText('SAMPLE-BOL-2026-001')).toBeInTheDocument();
    expect(screen.getByText('Greenfield Industrial Trading Co., Ltd.')).toBeInTheDocument();
  });

  it('allows sorting by column', async () => {
    const user = userEvent.setup();
    render(<ManifestTable manifests={manifests} />);

    const shipper_header = screen.getByRole('button', { name: /Shipper/i });
    await user.click(shipper_header);

    expect(shipper_header).toHaveAttribute('aria-sort', 'ascending');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ManifestTable manifests={manifests} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('is keyboard navigable', async () => {
    const user = userEvent.setup();
    render(<ManifestTable manifests={manifests} />);

    // Tab to first header
    await user.tab();
    const firstHeader = screen.getByRole('columnheader', { name: /Bill of Lading/i });
    expect(firstHeader).toHaveFocus();

    // Tab to next header
    await user.tab();
    const nextHeader = screen.getByRole('columnheader', { name: /Shipper/i });
    expect(nextHeader).toHaveFocus();
  });
});
```

### Pattern 2: Page Integration Tests

**File**: `ui/src/pages/__tests__/ScoringPage.spec.tsx`

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import ScoringPage from '../ScoringPage';
import * as api from '../../services/api';

expect.extend(toHaveNoViolations);

jest.mock('../../services/api');

describe('ScoringPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.getShipment as jest.Mock).mockResolvedValue({
      shipment_id: 'SHP-001',
      bill_of_lading: 'SAMPLE-BOL-2026-001',
      status: 'RECEIVED',
    });
  });

  it('displays score gauge with confidence level', async () => {
    (api.score as jest.Mock).mockResolvedValue({
      shipment_id: 'SHP-001',
      h3_total_score: 91,
      h3_confidence_level: 'HIGH',
    });

    render(<ScoringPage shipment_id="SHP-001" />);

    await waitFor(() => {
      expect(screen.getByText('91')).toBeInTheDocument();
      expect(screen.getByText(/HIGH/i)).toBeInTheDocument();
    });
  });

  it('displays 6 risk factors', async () => {
    (api.score as jest.Mock).mockResolvedValue({
      shipment_id: 'SHP-001',
      h3_total_score: 91,
      risk_indicators: [
        { indicator: 'Origin Documentation Gap', risk_level: 'HIGH' },
        { indicator: 'Commodity Sensitivity', risk_level: 'HIGH' },
        { indicator: 'Routing Consistency', risk_level: 'MEDIUM-HIGH' },
        { indicator: 'Party Profile Risk', risk_level: 'CRITICAL' },
        { indicator: 'Historical Pattern', risk_level: 'MEDIUM-HIGH' },
        { indicator: 'Time Sensitivity', risk_level: 'MEDIUM' },
      ],
    });

    render(<ScoringPage shipment_id="SHP-001" />);

    await waitFor(() => {
      expect(screen.getByText(/Origin Documentation Gap/)).toBeInTheDocument();
      expect(screen.getByText(/Commodity Sensitivity/)).toBeInTheDocument();
    });
  });

  it('has no accessibility violations', async () => {
    (api.score as jest.Mock).mockResolvedValue({
      shipment_id: 'SHP-001',
      h3_total_score: 91,
    });

    const { container } = render(<ScoringPage shipment_id="SHP-001" />);

    await waitFor(() => {
      expect(screen.getByText('91')).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('is fully keyboard navigable', async () => {
    const user = userEvent.setup();
    (api.score as jest.Mock).mockResolvedValue({
      shipment_id: 'SHP-001',
      h3_total_score: 91,
    });

    render(<ScoringPage shipment_id="SHP-001" />);

    // Start at top
    expect(document.body).toHaveFocus();

    // Tab through page
    for (let i = 0; i < 20; i++) {
      await user.tab();
      expect(document.activeElement).not.toBe(document.body);
    }
  });
});
```

---

## Running Tests

### Before Committing

```bash
# 1. Run all tests (fail fast on first error)
npm run test

# 2. Run accessibility tests
npm run test:a11y

# 3. Check coverage
npm run test:coverage
# Fail if below 90% (unit), 80% (integration)
```

### Full Test Suite

```bash
# Backend
cd api && pytest --cov=api --cov-fail-under=90 tests/

# Frontend
npm run test:ui -- --coverage --coverageThreshold='{"global":{"branches":80,"functions":80,"lines":80,"statements":80}}'

# E2E (staging only)
npm run test:e2e -- --baseURL=https://staging.sentry.cbp.dev
```

### Watch Mode (Development)

```bash
# Backend (auto-rerun on change)
pytest -x --lf tests/

# Frontend
npm run test:ui -- --watch
```

---

## GitHub Actions CI/CD

**File**: `.github/workflows/test.yml`

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: sentry_test
          POSTGRES_PASSWORD: test
      neo4j:
        image: neo4j:5-enterprise
        env:
          NEO4J_AUTH: neo4j/test

    steps:
      - uses: actions/checkout@v3
      
      - name: Backend tests
        run: |
          cd api
          pip install -r requirements.txt
          pytest --cov=api --cov-fail-under=90 tests/
      
      - name: Frontend tests
        run: |
          npm ci
          npm run test:ui -- --coverage
      
      - name: Accessibility tests
        run: npm run test:a11y -- --force-exit
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage.xml
```

---

## Pre-Commit Checklist

Before `git commit`:

- [ ] `npm run test` passes (RED → GREEN → REFACTOR)
- [ ] `npm run test:a11y` passes (0 violations)
- [ ] Coverage ≥ 90% (unit), ≥ 80% (integration)
- [ ] New tests added for new features
- [ ] Greenfield case still scores 91/100
- [ ] Control cases score < 50/100
- [ ] No flaky tests (run 3×)
- [ ] Accessibility tested manually (2 min NVDA check)

---

## Common Test Patterns

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### Testing Database Operations

```python
@pytest.mark.asyncio
async def test_shipment_creation(db_session):
    """Fixture provides transaction that rolls back after test"""
    
    shipment = Shipment(bill_of_lading='TEST-001', h3_score=91)
    db_session.add(shipment)
    await db_session.commit()
    
    # Query to verify
    result = await db_session.get(Shipment, shipment.id)
    assert result.h3_score == 91
```

### Testing with Fixtures

```python
@pytest.fixture
def greenfield_shipment():
    """Reusable test data"""
    return greenfield_aluminum

def test_with_greenfield(greenfield_shipment):
    assert greenfield_shipment['expected_score'] == 91
```

### Testing Error Handling

```python
def test_invalid_hts_code():
    with pytest.raises(ValueError, match="Invalid HTS code"):
        parse_hts('INVALID')
```

---

## Continuous Integration

All tests run automatically on:
- **PR push**: Full test suite
- **PR merge to main**: Full test suite + E2E on staging
- **Nightly**: Load testing, security scanning

**Status badge**: [![Tests](https://github.com/rvadera73/cbp-sentry-demo/workflows/Test/badge.svg)](https://github.com/rvadera73/cbp-sentry-demo/actions)
