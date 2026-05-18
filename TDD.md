# Test-Driven Development (TDD) Framework — Sentry CBP

## Overview

Sentry CBP is developed **test-first** following the Red → Green → Refactor cycle. This document describes the complete TDD framework covering backend (API) and frontend (UI).

## TDD Discipline

### The Cycle

```
RED          → WRITE FAILING TEST
  │
  ├─→ Test verifies requirement
  ├─→ No implementation yet
  ├─→ Test should fail
  │
GREEN        → IMPLEMENT CODE
  │
  ├─→ Write minimal code to pass test
  ├─→ Don't over-engineer
  ├─→ Test should pass
  │
REFACTOR     → IMPROVE CODE
  │
  ├─→ Keep tests green
  ├─→ Remove duplication
  ├─→ Simplify complexity
```

### Why TDD?

1. **Executable Specifications**: Tests document requirements in code
2. **Design First**: Writing tests forces you to think about interfaces before implementation
3. **Confidence**: Green tests = working code
4. **Refactoring Safety**: Tests prevent regressions
5. **Documentation**: New developers read tests to understand behavior

## Project Structure

```
cbp-sentry/
├── api/tests/                    # Backend tests (pytest)
│   ├── conftest.py              # Fixtures: database, async client, Greenfield data
│   ├── test_referral_package.py # Referral JSON (Tables 3-1–3-14)
│   ├── test_ingest.py           # Manifest parsing
│   ├── test_entity_resolution.py # Senzing + Neo4j
│   ├── test_scoring.py          # 4-tier scoring (Tier 1-4)
│   └── README.md                # Backend testing guide
│
├── ui/tests/                     # Frontend tests (Vitest)
│   ├── setup.ts                 # React Testing Library + jest-axe
│   ├── components/
│   │   ├── accessibility.spec.tsx      # WCAG 2.0 AA compliance
│   │   ├── ManifestTable.spec.tsx      # Table rendering
│   │   └── ScoreGauge.spec.tsx         # Gauge component
│   ├── pages/
│   │   ├── ReferralPackagePage.spec.tsx # Referral display
│   │   └── GraphPage.spec.tsx          # Graph explorer
│   └── README.md                # Frontend testing guide
│
├── pytest.ini                   # Pytest configuration
├── ui/vitest.config.ts          # Vitest configuration
└── TDD.md                       # This file
```

## Backend Tests

### Location
`api/tests/`

### Configuration
`pytest.ini` + `api/tests/conftest.py`

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=api --cov-report=html

# Specific module
pytest api/tests/test_referral_package.py -v

# Async tests only
pytest -k "async"
```

### Test Modules

#### `test_referral_package.py`
**Tests referral JSON generation and scoring**

Classes:
- `TestReferralPackageStructure` — All 14 tables (3-1 through 3-14) present
- `TestConfidenceScoreCalculation` — Score 0-100, Greenfield = 91
- `TestComponentBreakdown` — 6 components sum to total
- `TestXAIAssertions` — Plain-English descriptions for each score component
- `TestRevenueImpactCalculation` — Duty impact calculation
- `TestRecommendedActionField` — Action logic (EXAMINE_ON_ARRIVAL, etc.)

Example:
```python
def test_greenfield_confidence_score_is_91(self, greenfield_referral_package):
    """Greenfield case must score 91/100"""
    package = greenfield_referral_package
    assert package["score"] == 91
    assert package["confidence_level"] == "HIGH"
```

#### `test_ingest.py`
**Tests manifest parsing and ingestion**

Classes:
- `TestExcelUploadParsing` — Excel parsing, sheet selection
- `TestFieldNormalization` — Whitespace, special chars, country codes, units
- `TestHTSCodeExtraction` — HTS validation, commodity lookup, AD/CVD rates
- `TestShipperConsigneeResolution` — Entity parsing
- `TestManifestToShipmentRecord` — Firestore document creation
- `TestManifestIngestionEndToEnd` — Full pipeline E2E

Example:
```python
def test_extract_hts_code_from_manifest_field(self):
    """HTS code 7604.10.1000 must be extracted and validated"""
    pytest.skip("Implementation pending: HTS extraction")
```

#### `test_entity_resolution.py`
**Tests Senzing + Neo4j entity resolution**

Classes:
- `TestEntityLoading` — Load entities into Senzing
- `TestGreenfieldVNtoCNResolution` — VN shipper → CN parent chain
- `TestWhyExplanationAPI` — Senzing why-API
- `TestEntityGraphConstruction` — Neo4j graph building (7 nodes, relationships)
- `TestSenzingIntegration` — Health check, record format
- `TestEntityResolutionEndToEnd` — Full E2E

Example:
```python
def test_resolve_greenfield_vn_shipper_to_cn_parent(self, greenfield_entities, mock_senzing):
    """Greenfield VN shipper must match CN parent via Senzing"""
    shipper = greenfield_entities["shipper_vn"]
    parent = greenfield_entities["parent_cn"]
    assert shipper["senzing_confidence"] >= 0.85
    pytest.skip("Implementation pending: Senzing resolution")
```

#### `test_scoring.py`
**Tests 4-tier ML scoring pipeline**

Classes:
- `TestTier1SenzingEntityChain` — Party profile risk (0-15 pts)
- `TestTier2IsolationForest` — Routing consistency / AIS anomaly (0-15 pts)
- `TestTier3LightGBM` — Commodity sensitivity + historical pattern (0-30 pts)
- `TestTier4BayesianBeliefNetwork` — Origin doc gap + time sensitivity (0-40 pts)
- `TestScoringAggregation` — Final score (0-100)

Example:
```python
def test_tier1_party_profile_risk_for_greenfield(self, greenfield_entities):
    """VN shipper linked to CN parent = 15/15"""
    # VN → CN chain must score maximum
    pytest.skip("Implementation pending: Tier 1 scorer")
```

### Fixtures

All fixtures in `api/tests/conftest.py`:

| Fixture | Purpose |
|---------|---------|
| `in_memory_db` | SQLite database for tests |
| `async_client` | FastAPI test client |
| `greenfield_manifest` | Manifest fixture data |
| `greenfield_entities` | 7-node entity graph |
| `greenfield_score_breakdown` | 6-component scores (total 91) |
| `greenfield_referral_package` | Full referral JSON |
| `mock_firestore` | Mocked Firestore |
| `mock_neo4j` | Mocked Neo4j |
| `mock_senzing` | Mocked Senzing |
| `mock_gemini` | Mocked LLM |

### Test Data: Greenfield Case

The Greenfield aluminum case is the canonical test case:

```python
greenfield_manifest = {
    "bill_id": "SAMPLE-BOL-2026-001",
    "shipper": "Greenfield Industrial Trading Co., Ltd.",
    "hts_code": "7604.10.1000",
    "country_of_origin": "VN",
    "isf_stuffing_country": "CN",  # Contradiction!
    "ais_dwell_days": 11.2,  # 5.3× baseline
    "declared_value_usd": 72030,
}

greenfield_entities = {
    "shipper_vn": { risk_score: 65, jurisdiction: "VN", ... },
    "parent_cn": { risk_score: 72, jurisdiction: "CN", ... },
    "parent_hk": { risk_score: 58, jurisdiction: "HK", ... },
    # ... 4 more entities
}

greenfield_score_breakdown = {
    "total": 91,
    "components": [
        { "name": "origin_doc_gap", "score": 23, "max": 25 },
        { "name": "party_profile_risk", "score": 15, "max": 15 },
        { "name": "routing_consistency", "score": 14, "max": 15 },
        { "name": "commodity_sensitivity", "score": 14, "max": 15 },
        { "name": "historical_pattern", "score": 12, "max": 15 },
        { "name": "time_sensitivity", "score": 13, "max": 15 },
    ]
}
```

Reference: ARCHITECTURE.md

## Frontend Tests

### Location
`ui/tests/`

### Configuration
`ui/vitest.config.ts` + `ui/tests/setup.ts`

### Running Tests

```bash
# All tests
npm test

# With coverage
npm test -- --coverage

# Specific file
npm test components/ScoreGauge.spec.tsx

# Interactive UI dashboard
npm run test:ui

# Watch mode
npm test -- --watch
```

### Test Modules

#### `components/accessibility.spec.tsx`
**WCAG 2.0 AA compliance across all components**

Test classes:
- `jest-axe Automated Checks` — jest-axe scan for violations
- `Color Contrast` — 4.5:1 minimum for text
- `ARIA Labels and Roles` — aria-label, aria-expanded, etc.
- `Keyboard Navigation` — Tab, Escape, Enter, arrow keys
- `Focus Management` — Visible focus, focus trapping
- `Semantic HTML` — button vs. div[onclick], heading hierarchy
- `Screen Reader Support` — aria-live, role="alert"

Example:
```typescript
it("should have no automated accessibility violations in Button component", async () => {
  const { container } = render(<Button>Click me</Button>);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

#### `components/ManifestTable.spec.tsx`
**Manifest data table component**

Test classes:
- `Rendering` — All rows and columns rendered
- `Sorting/Filtering` — Column-based sorting
- `Keyboard Navigation` — Tab, arrow keys in table
- `Accessibility` — jest-axe, ARIA roles, column headers
- `Row Click Handler` — Row selection
- `Responsiveness` — Long names, large numbers
- `Data Validation` — Missing fields, null values

Example:
```typescript
it("should render table with manifest data", () => {
  render(<ManifestTable data={sampleData} />);
  expect(screen.getByRole("table")).toBeInTheDocument();
  expect(screen.getByText("SAMPLE-BOL-2026-001")).toBeInTheDocument();
});
```

#### `components/ScoreGauge.spec.tsx`
**Risk score gauge (0-100, color-coded)**

Test classes:
- `Rendering` — Score 0-100 displayed
- `Color Thresholds` — Green (<30), yellow (30-70), red (>70)
- `Animation` — Score animates from 0 to final value
- `Accessibility` — ARIA image role, aria-valuenow, jest-axe
- `Label Customization` — Custom labels
- `Responsive Design` — Mobile/tablet/desktop
- `Edge Cases` — Score 0, 100, non-integer, invalid

Example:
```typescript
it("should be red for high risk (> 70)", () => {
  render(<ScoreGauge score={91} />);
  expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
});
```

#### `pages/ReferralPackagePage.spec.tsx`
**Full referral package display page**

Test classes:
- `Rendering Full Package` — Score, confidence, action displayed
- `Tables 3-1 through 3-14` — All sections rendered
- `Expandable Sections` — Toggle visibility
- `PDF Export` — Export button and functionality
- `Score Breakdown` — Component scores sum to total
- `Data Sources` — ISF, AIS, Senzing with confidence
- `Accessibility` — jest-axe, heading hierarchy, semantic HTML
- `Responsive Design` — Mobile/tablet/desktop stacking
- `Data Validation` — Missing sections, malformed dates

Example:
```typescript
it("should display confidence score (91/100)", () => {
  render(<ReferralPackagePage package={greenfield_package} />);
  expect(screen.getByText(/Score: 91\/100/)).toBeInTheDocument();
});
```

#### `pages/GraphPage.spec.tsx`
**Entity graph explorer with sidebar**

Test classes:
- `Graph Loading` — Load 7-node Greenfield graph
- `Node Rendering` — All nodes with labels and colors
- `Edge Labels` — Relationship types and confidence
- `Node Interaction` — Click to select, highlight connected
- `Sidebar Details` — Show entity info, connected entities
- `Why Connected` — Explain connection reasons
- `Accessibility` — jest-axe, keyboard nav, screen reader
- `Responsive Design` — Mobile stacking, desktop side-by-side
- `Performance` — <1s for 7-node, handle 50+ nodes
- `Data Validation` — Missing properties, circular relationships

Example:
```typescript
it("should load 7-node Greenfield graph", () => {
  render(<GraphPage graph={greenfield_graph} />);
  expect(screen.getByText(/Greenfield Industrial Trading/)).toBeInTheDocument();
  expect(screen.getByText(/MV Pacific Horizon/)).toBeInTheDocument();
});
```

### Setup: `setup.ts`

Initializes:
- React Testing Library
- jest-axe for accessibility
- window.matchMedia mock
- Fetch API mock
- IntersectionObserver, ResizeObserver mocks

```typescript
import "@testing-library/jest-dom";
import { expect } from "vitest";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
```

## Running All Tests

### Backend Only
```bash
pytest
pytest --cov=api
```

### Frontend Only
```bash
npm test
npm test -- --coverage
```

### All Tests (Both Suites)
```bash
# Terminal 1
cd /home/rahulvadera/cbp-sentry
pytest

# Terminal 2
cd /home/rahulvadera/cbp-sentry/ui
npm test
```

## Coverage Goals

| Module | Target |
|--------|--------|
| api/services/ | 80%+ |
| api/core/ | 75%+ |
| api/main.py | 90%+ |
| ui/src/components/ | 80%+ |
| ui/src/pages/ | 75%+ |

Current: **TBD** (skeleton phase)

View coverage:
```bash
# Backend
pytest --cov=api --cov-report=html
open htmlcov/index.html

# Frontend
npm test -- --coverage
open ui/coverage/index.html
```

## Implementation Roadmap

### Phase 1: Skeleton (CURRENT)
- ✅ Write all test files (RED phase)
- ✅ Define fixtures and test data
- ✅ Document expected behavior
- Tests are failing

### Phase 2: Backend (Week 1-4)
- Implement `api/services/ingest/` (manifest parsing)
- Implement `api/services/entity_resolution/` (Senzing wrapper)
- Implement `api/services/scoring/` (4-tier ML)
- Implement `api/services/referral/` (JSON generation)
- All backend tests should pass (GREEN)

### Phase 3: Frontend (Week 5-8)
- Implement `ui/src/components/accessibility` compliance
- Implement `ui/src/components/ManifestTable`
- Implement `ui/src/components/ScoreGauge`
- Implement `ui/src/pages/ReferralPackagePage`
- Implement `ui/src/pages/GraphPage`
- All frontend tests should pass (GREEN)

### Phase 4: Refactoring (Week 9+)
- Simplify implementations
- Extract shared logic
- Optimize performance
- Keep all tests green

## Compliance Standards

### Backend API
- **19 CFR 149.5**: ISF requirements (manifest tests)
- **19 CFR 134.1**: Country of origin rules
- **FedRAMP High**: Vertex AI Gemini authorized service
- **WCAG 2.0 AA**: JSON response descriptions (XAI narratives)

### Frontend UI
- **WCAG 2.0 AA**: Keyboard navigation, contrast, ARIA
  - Tested via jest-axe
  - Keyboard: Tab, Escape, Enter, arrow keys
  - Contrast: 4.5:1 for normal text, 3:1 for large text
  - ARIA: Labels, roles, descriptions, live regions

### Data Models
- **Firestore**: Collections (corridors, shipments, referral_packages)
- **Neo4j**: Graph model (7-node Greenfield case)
- **Senzing**: Entity resolution + why-API

## References

### Backend
- ARCHITECTURE.md — System design
- pytest documentation
- Pydantic (data validation)
- Senzing Entity Resolution
- Neo4j Cypher Query Language

### Frontend
- Vitest documentation
- React Testing Library
- jest-axe (WCAG 2.0 AA)
- WCAG 2.0 Quick Reference
- MDN Web Accessibility

## Key Principles

1. **Test First**: Write test before implementation
2. **Clear Specs**: Tests document requirements
3. **Accessibility**: All components WCAG 2.0 AA compliant
4. **Minimal Code**: Implement only what's needed to pass tests
5. **Refactor Safely**: Tests prevent regressions
6. **Fixture Reuse**: Share test data via fixtures
7. **Mock External Services**: Senzing, Neo4j, Firestore, Gemini are mocked
8. **Green is Good**: All tests passing = working system

---

**Last Updated**: May 18, 2026  
**Framework Version**: 1.0  
**Status**: RED Phase (Tests written, no implementation yet)
