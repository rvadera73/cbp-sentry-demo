# 7-Factor Risk Scoring System — Verification Checklist

## Phase 2 Implementation Status: COMPLETE ✓

### Backend Components

#### Database Layer ✓
- **File**: `services/data/db.py`
- **Status**: All 4 migration columns added (idempotent pattern)
  - `calculated_risk_score REAL`
  - `risk_score_calculated_at TIMESTAMP`
  - `risk_score_breakdown TEXT`
  - `confidence_interval TEXT`
- **Migrations**: Lines 467-470
- **Pattern**: Duplicate column check prevents errors on repeated runs

#### Data Models ✓
- **File**: `services/data/models.py`
- **Status**: Both ShipmentUpdate and Shipment classes updated
  - `ShipmentUpdate`: Lines 32-35
  - `Shipment`: Lines 72-75
- **Types**: Float, datetime, and Dict[str, Any] for breakdown JSON storage

#### Risk Scoring Engine ✓
- **File**: `services/api/risk_scoring_engine.py`
- **Import Fix**: Changed to absolute import `from services.api.risk_models import...`
- **Status**: Loads ML models (Isolation Forest, LightGBM) on initialization

#### API Routes ✓
- **File**: `api/services/risk_scoring/routes.py`
- **Endpoints**:
  - `POST /api/score/full-breakdown/{shipment_id}` — Main scoring endpoint
  - `POST /api/score/health-check` — Engine health verification
- **Features**:
  - Accepts shipment_data dict with all relevant fields
  - Returns RiskScoreBreakdown with 18 components in 7 factors
  - Database persistence: Automatically saves breakdown after calculation
  - Non-blocking: Request succeeds even if DB save fails

#### Route Registration ✓
- **File**: `api/main.py`
- **Status**: Lines 77, 82
  - Import: `from api.services.risk_scoring.routes import router as risk_scoring_router`
  - Registration: `app.include_router(risk_scoring_router, prefix="/api/score", tags=["risk-scoring"])`

### Frontend Components

#### TypeScript Types ✓
- **File**: `ui/src/components/risk-scoring/types.ts`
- **Defines**: RiskComponent, RiskScoreBreakdown, CalculationTable, Adjustment interfaces
- **Status**: All 18 component fields + calculation transparency + adjustment tracking

#### Utilities ✓
- **File**: `ui/src/components/risk-scoring/utils.ts`
- **Functions**:
  - `getRiskLevel(score)` — Classification (CRITICAL|HIGH|MEDIUM|LOW)
  - `getRiskColor(score)` — Color mapping (#dc2626|#ea580c|#eab308|#22c55e)
  - `groupComponentsByFactor()` — Organize 18 components by 7 factors
  - `calculateFactorSubtotal()` — Sum weighted results per factor
  - `isValidRiskBreakdown()` — Type guard validation
  - `generateMockRiskBreakdown()` — Test data with all 18 components
  - `exportBreakdownAsJSON()`, `exportBreakdownAsCSV()` — Export functions
  - `formatScore()` — Number formatting
- **Status**: Pure utility functions, no side effects, fully testable

#### Components (5 Created) ✓

**RiskScoreHeader.tsx** — Score Display
- Large risk score number (56px font-weight 900)
- Color-coded risk badge (CRITICAL|HIGH|MEDIUM|LOW)
- Confidence interval display
- Score range indicator bar (0-100 fill)
- Risk classification text (auto-generated based on level)
- No API calls, props-only

**RiskComponentTable.tsx** — 7-Factor Breakdown
- Displays all 18 components organized by 7 factors in predefined order
- Table columns: Component, Score/10, Weight %, Calculation, Weighted Result
- Shows evidence and rationale for each component
- Responsive design (single column on mobile)
- Pure presentational component

**RiskScoreBreakdown.tsx** (Main Container) — Orchestration
- Root component combining all sections:
  - RiskScoreHeader (score display)
  - RiskComponentTable (18 components in 7 factors)
  - CollapsibleSection: "Component Details" (expanded by default)
  - CollapsibleSection: "Calculation Breakdown" (collapsed, shows step-by-step)
  - CollapsibleSection: "Adjustments & Modifiers" (corridor multipliers, penalties)
  - Export Section (JSON/CSV format + download button)
- State: exportFormat, showExport
- Handles loading, error, and empty states
- Database persistence happens via API (non-blocking)
- Full calculation transparency with evidence per component

#### Stylesheets (3 Created) ✓

**RiskScoreBreakdown.css** (270 lines)
- Main container layout and spacing
- Collapsible section styling (header, toggle, content)
- Calculation table styling
- Adjustments section card layout
- Export panel styling with radio buttons and download button
- Loading spinner animation
- Error and empty state styling
- Responsive breakpoints (tablet, mobile)

**RiskScoreHeader.css** (140 lines)
- Score card with left border color
- Score display (large number + label + badge)
- Confidence display
- Score range bar with 0-50-100 labels
- Risk classification box
- Color-specific variants (red, orange, yellow, green)
- Responsive design

**RiskComponentTable.css** (310 lines)
- Table layout with proper column widths
- Factor section headers and organization
- Component info display (name, rationale, evidence badges)
- Score value styling (blue score, green calculation)
- Responsive table scrolling on mobile
- Hover effects on rows
- Print styles for referral generation

#### Investigation Page Integration ✓
- **File**: `ui/src/pages/ModernCaseInvestigationPage.tsx`
- **Changes**:
  - Removed import of old ThreeLevelScoreData
  - Added import of RiskScoreBreakdown component
  - Added import of RiskScoreBreakdown type from types.ts
  - Removed threeLevelScore state, added riskBreakdown, riskLoading, riskError
  - Updated expandedSections to remove altana/factors sections
  - Created new `fetchRiskBreakdown()` function calling POST /api/score/full-breakdown/{id}
  - Updated header to display riskBreakdown?.final_score
  - Replaced old 3-level section with new 7-factor RiskScoreBreakdown component
  - Updated feedback interface to use riskBreakdown?.final_score
  - Removed old three-level, XAI factors, and Altana sections

## Testing Checklist

### Unit Tests (Pre-Deployment)
- [ ] RiskScoreBreakdown component renders without API
- [ ] Mock data loads correctly (generateMockRiskBreakdown)
- [ ] Export functions generate valid JSON and CSV
- [ ] Color and level classification functions work correctly
- [ ] Component grouping logic maintains factor order

### Integration Tests (Local Deployment)
- [ ] Database migrations run successfully
- [ ] POST /api/score/full-breakdown/{id} returns valid RiskScoreBreakdown
- [ ] API response persists to database (calculated_risk_score, risk_score_breakdown)
- [ ] Investigation page loads and displays RiskScoreBreakdown
- [ ] Export buttons generate downloadable files
- [ ] Collapsible sections toggle correctly
- [ ] Mobile responsive layout works correctly

### End-to-End Flow
- [ ] Shipment data → API call → RiskScoreBreakdown component → UI display
- [ ] Database persistence (non-blocking)
- [ ] Confidence interval displays correctly
- [ ] All 18 components visible and organized by factor
- [ ] Calculation table shows step-by-step breakdown
- [ ] Adjustments section shows corridor multipliers

## Deployment Instructions

### 1. Database Setup
```bash
cd /home/rahulvadera/cbp-sentry
python3 services/data/db.py
# Or via local deployment script if configured
```

### 2. API Server
```bash
# Start from api/ directory
python3 -m uvicorn main:app --reload --port 8000
```

### 3. Frontend Build
```bash
cd ui/
npm install  # If dependencies updated
npm run dev  # For development
# or
npm run build  # For production
```

### 4. Verify Routes
```bash
# Check API routes are registered
curl http://localhost:8000/openapi.json | grep risk-scoring
```

### 5. Test Endpoint
```bash
curl -X POST http://localhost:8000/api/score/full-breakdown/test-123 \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "test-123",
    "shipper_name": "Test Shipper",
    "shipper_country": "VN",
    "consignee_name": "Test Consignee",
    "consignee_country": "US",
    "hs_code": "6204.62.8015",
    "declared_value_usd": 45000,
    "declared_weight_kg": 500,
    "vessel_name": "Test Vessel"
  }'
```

## File Structure Summary

```
cbp-sentry/
├── api/
│   ├── main.py (routes registered here)
│   └── services/
│       └── risk_scoring/
│           ├── __init__.py
│           └── routes.py (main scoring endpoint)
├── services/
│   ├── data/
│   │   ├── db.py (migrations + CRUD)
│   │   └── models.py (Pydantic models)
│   └── api/
│       ├── risk_scoring_engine.py (7-factor model)
│       └── risk_models.py (RiskScoreBreakdown)
└── ui/
    └── src/
        ├── components/
        │   └── risk-scoring/
        │       ├── types.ts
        │       ├── utils.ts
        │       ├── RiskScoreHeader.tsx
        │       ├── RiskComponentTable.tsx
        │       ├── RiskScoreBreakdown.tsx
        │       ├── RiskScoreBreakdown.css
        │       ├── RiskScoreHeader.css
        │       └── RiskComponentTable.css
        └── pages/
            └── ModernCaseInvestigationPage.tsx
```

## Known Status

- **ML Models**: Isolation Forest (AIS anomalies), LightGBM (transshipment) — loaded on engine init
- **Database Persistence**: Non-blocking (request completes even if DB save fails)
- **Frontend Independence**: Zero API calls within components, all data via props
- **Type Safety**: Full TypeScript with RiskScoreBreakdown interface
- **Mock Data**: Realistic 18-component breakdown for testing without server

## Next Phase: Historical Data Migration

Once deployment verified:
1. Run `scripts/migrate_scores.py` to backfill calculated_risk_score for existing shipments
2. Monitor database size (risk_score_breakdown stored as JSON TEXT)
3. Archive old three-level scoring data if desired
