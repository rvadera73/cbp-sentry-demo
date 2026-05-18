# Sentry CBP — Complete Testing Framework

## Quick Start

### Backend Tests (pytest)

```bash
# Install dependencies
pip install pytest pytest-asyncio httpx pydantic-settings

# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test
pytest api/tests/test_referral_package.py::TestConfidenceScoreCalculation::test_greenfield_confidence_score_is_91 -v
```

### Frontend Tests (Vitest)

```bash
# Install dependencies
npm install

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Interactive UI dashboard
npm run test:ui
```

## Documentation Structure

| Document | Purpose |
|----------|---------|
| **TDD.md** | Master TDD framework overview (400+ tests, all phases) |
| **TESTING.md** | This file — quick reference and running tests |
| **api/tests/README.md** | Backend testing guide (pytest, fixtures, patterns) |
| **ui/tests/README.md** | Frontend testing guide (Vitest, RTL, jest-axe) |

## Test Organization

### Backend (api/tests/)

```
api/tests/
├── conftest.py                   # Pytest configuration & fixtures
├── test_referral_package.py      # Referral JSON (Tables 3-1–3-14)
├── test_ingest.py               # Manifest parsing & ingestion
├── test_entity_resolution.py     # Senzing + Neo4j graph
├── test_scoring.py              # 4-tier ML scoring
└── README.md                     # Backend guide
```

**Test Counts**
- 140+ test methods
- 50.7 KB test code
- 6 test classes per module (avg)
- All fixtures in conftest.py

**Key Fixtures**
- `greenfield_manifest` — Sample manifest with ISF/AIS data
- `greenfield_entities` — 7-node Neo4j graph
- `greenfield_score_breakdown` — 6-component scores (total 91)
- `greenfield_referral_package` — Full referral JSON
- `in_memory_db` — SQLite for tests
- `async_client` — FastAPI test client
- Service mocks — Firestore, Neo4j, Senzing, Gemini

### Frontend (ui/tests/)

```
ui/tests/
├── setup.ts                      # Vitest + RTL + jest-axe init
├── components/
│   ├── accessibility.spec.tsx    # WCAG 2.0 AA compliance
│   ├── ManifestTable.spec.tsx    # Table rendering & interaction
│   └── ScoreGauge.spec.tsx       # Risk score gauge (0-100)
├── pages/
│   ├── ReferralPackagePage.spec.tsx # Referral display
│   └── GraphPage.spec.tsx           # Entity graph explorer
├── vitest.config.ts              # Vitest configuration
└── README.md                     # Frontend guide
```

**Test Counts**
- 260+ test methods
- 48 KB test code
- 7-10 test classes per file
- Jest-axe accessibility integration

**Component Coverage**
- Accessibility (all components)
- ManifestTable (data, sorting, keyboard)
- ScoreGauge (animation, color thresholds)
- ReferralPackagePage (expandable sections, PDF export)
- GraphPage (node interaction, why-connected)

## Test Data: Greenfield Case

The Greenfield aluminum case is the canonical test scenario (ARCHITECTURE.md):

```
Bill ID:              SAMPLE-BOL-2026-001
Shipper:              Greenfield Industrial Trading Co., Ltd. (Vietnam)
Consignee:            SunPath Energy Distributors LLC (USA)
Commodity:            Aluminum extrusions (HTS 7604.10.1000)
Declared COO:         Vietnam
ISF Stuffing Country: China ← CONTRADICTION (19 CFR 149.5)
AIS Dwell Time:       11.2 days (5.3× baseline) ← ANOMALY
Confidence Score:     91/100 ← HIGH RISK
Recommended Action:   EXAMINE_ON_ARRIVAL
Entity Chain:         VN shipper → HK holding → CN manufacturer
```

All tests use this case as reference data.

## Compliance Standards

### Backend API

- **19 CFR 149.5** — ISF Data Element 9 (stuffing location contradiction)
- **19 CFR 134.1** — Country of origin determination
- **FedRAMP High** — Vertex AI Gemini authorized
- **Senzing** — Entity resolution and why-API

### Frontend UI

- **WCAG 2.0 AA** — Keyboard navigation, color contrast, ARIA labels
- **jest-axe** — Automated accessibility testing
- **Color Contrast** — 4.5:1 minimum for text
- **Keyboard** — Tab, Escape, Enter, arrow keys all functional

## Test Execution

### Pytest Commands

```bash
# All tests with verbose output
pytest -v

# All tests with short tracebacks
pytest --tb=short

# Tests matching pattern
pytest -k "greenfield"

# Specific test class
pytest api/tests/test_scoring.py::TestTier1SenzingEntityChain -v

# Specific test method
pytest api/tests/test_scoring.py::TestTier1SenzingEntityChain::test_tier1_party_profile_risk_for_greenfield -v

# Coverage only
pytest --cov=api --cov-report=term-missing

# With HTML coverage report
pytest --cov=api --cov-report=html
open htmlcov/index.html

# Slow tests (>1s)
pytest --durations=10

# Only async tests
pytest -m asyncio

# With logging
pytest --log-cli-level=DEBUG
```

### Vitest Commands

```bash
# All tests
npm test

# Specific file
npm test ManifestTable.spec.tsx

# Matching pattern
npm test -- --grep "render"

# Coverage report
npm test -- --coverage

# Interactive dashboard
npm run test:ui

# Watch mode
npm test -- --watch

# Single run (CI mode)
npm test -- --run

# Debug mode (opens browser)
npm test -- --inspect-brk
```

## Test Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| api/services | TBD | 80%+ |
| api/core | TBD | 75%+ |
| api/main.py | TBD | 90%+ |
| ui/src/components | TBD | 80%+ |
| ui/src/pages | TBD | 75%+ |
| **Overall** | **TBD** | **80%+** |

## Implementation Roadmap

### Phase 1: RED (CURRENT)
- ✅ All 400+ tests written
- ✅ Greenfield case defined
- ✅ Fixtures and mocks in place
- Tests are failing (expected)

### Phase 2: Backend Implementation (Week 1-4)
- Implement `api/services/ingest/` (manifest parsing)
- Implement `api/services/entity_resolution/` (Senzing wrapper)
- Implement `api/services/scoring/` (4-tier ML)
- Implement `api/services/referral/` (JSON generation)
- All backend tests pass (GREEN)

### Phase 3: Frontend Implementation (Week 5-8)
- Implement `ui/src/components/accessibility` (WCAG)
- Implement `ui/src/components/ManifestTable`
- Implement `ui/src/components/ScoreGauge`
- Implement `ui/src/pages/ReferralPackagePage`
- Implement `ui/src/pages/GraphPage`
- All frontend tests pass (GREEN)

### Phase 4: Refactoring (Week 9+)
- Simplify implementations
- Extract shared logic
- Optimize performance
- Keep all tests green

## Common Test Patterns

### Pytest Fixtures

```python
# Use fixture in test
def test_example(greenfield_manifest):
    assert greenfield_manifest["bill_id"] == "SAMPLE-BOL-2026-001"

# Parametrized fixture
@pytest.mark.parametrize("score,tier", [
    (25, "LOW"),
    (50, "MEDIUM"),
    (91, "HIGH"),
])
def test_confidence_tiers(score, tier):
    # Test with multiple parameters
    pass
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
```

### React Testing Library Patterns

```typescript
// Render and query
render(<Component />);
expect(screen.getByText("Hello")).toBeInTheDocument();

// User interaction
await user.click(screen.getByRole("button"));

// jest-axe
const { container } = render(<Component />);
const results = await axe(container);
expect(results).toHaveNoViolations();
```

## Debugging Tests

### Backend

```bash
# Print debug info
pytest -s -v api/tests/test_referral_package.py

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Open debugger on failure
pytest --pdb
```

### Frontend

```bash
# Print DOM tree
screen.debug();

# Interactive browser
npm run test:ui

# Console output
npm test -- --reporter=verbose

# Single test
npm test -- --grep "should render"
```

## File Locations

### Backend

| File | Lines | Purpose |
|------|-------|---------|
| pytest.ini | 30 | Test discovery, coverage config |
| conftest.py | 300 | Fixtures, test data, mocks |
| test_referral_package.py | 400 | 50+ tests for referral generation |
| test_ingest.py | 300 | 25+ tests for manifest ingestion |
| test_entity_resolution.py | 280 | 20+ tests for entity resolution |
| test_scoring.py | 350 | 45+ tests for ML scoring |

### Frontend

| File | Lines | Purpose |
|------|-------|---------|
| vitest.config.ts | 50 | Vitest setup (jsdom, coverage) |
| setup.ts | 60 | RTL, jest-axe, mocks |
| accessibility.spec.tsx | 300 | 40+ WCAG 2.0 AA tests |
| ManifestTable.spec.tsx | 350 | 45+ table tests |
| ScoreGauge.spec.tsx | 300 | 50+ gauge tests |
| ReferralPackagePage.spec.tsx | 450 | 60+ page tests |
| GraphPage.spec.tsx | 500 | 70+ graph tests |

## Troubleshooting

### "Test not found"
- Check file naming: `test_*.py` (backend), `*.spec.ts` (frontend)
- Verify function naming: `test_*` (backend), `it("...", () => {})` (frontend)

### "Import error"
- Backend: Install dependencies `pip install pytest pytest-asyncio httpx`
- Frontend: Install dependencies `npm install`

### "Async test timeout"
- Increase timeout in config (pytest.ini, vitest.config.ts)
- Use `waitFor()` with timeout option for async operations

### "Element not found"
- Frontend: Use `screen.debug()` to see DOM
- Check for typos in query text
- Use `getByRole()` instead of `getByTestId()`

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Backend tests
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install pytest pytest-asyncio httpx
      - run: pytest --cov=api
      
      # Frontend tests
      - uses: actions/setup-node@v3
        with:
          node-version: "18"
      - run: npm install
      - run: npm test -- --coverage
```

## Resources

### Testing Frameworks

- **pytest** — https://docs.pytest.org/
- **Vitest** — https://vitest.dev/
- **React Testing Library** — https://testing-library.com/docs/react-testing-library/intro/
- **jest-axe** — https://github.com/nickcolley/jest-axe

### Standards & Compliance

- **WCAG 2.0** — https://www.w3.org/WAI/WCAG21/quickref/
- **19 CFR 149** — https://www.ecfr.gov/current/title-19/section-149.5
- **Senzing** — https://docs.senzing.com/

### Architecture

- **ARCHITECTURE.md** — System design (3-horizon, scoring, data models)
- **CLAUDE.md** — Project-specific instructions
- **README.md** — Project overview

## Key Takeaways

✅ **400+ tests** covering all major components  
✅ **RED phase** — Tests written first, implementations follow  
✅ **Greenfield case** — Canonical test scenario  
✅ **Fixtures** — Reusable test data  
✅ **Mocks** — External services isolated  
✅ **WCAG 2.0 AA** — Full accessibility testing  
✅ **19 CFR compliance** — All tests reference regulations  
✅ **Documentation** — Every test class has clear purpose  

**Status**: Tests complete, implementation ready to begin

---

**Last Updated**: May 18, 2026  
**Phase**: RED (Tests written, failing)  
**Next**: GREEN (Implementation)
