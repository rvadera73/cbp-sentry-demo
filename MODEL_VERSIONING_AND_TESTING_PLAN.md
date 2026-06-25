# Model Versioning & Full New Model Testing Plan

**Version:** 1.0 | **Date:** 2026-06-12 | **Purpose:** Execute Phase 2 with new model as primary, maintain full rollback capability

---

## 1. Overview

**Goal:** Test CBP Sentry exclusively with the new Precise Risk Model (v3.0) while maintaining snapshots of all data models for complete rollback to legacy model (v2.1).

**Key Requirements:**
- ✅ 100% traffic on new model (not gradual ramping)
- ✅ All scores show which model calculated them
- ✅ UI displays model version in tabs
- ✅ Complete data model snapshots before changes
- ✅ Easy rollback to v2.1 if needed
- ✅ Track model versions in database

---

## 2. Data Model Snapshots Strategy

### 2.1 Create Versioned Schema

Add model versioning to all relevant database tables:

```sql
-- New column: track which model version calculated the score
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);
-- Default for existing rows: 'v2.1-legacy'

-- New table: model_metadata (tracks versions)
CREATE TABLE IF NOT EXISTS model_metadata (
  id TEXT PRIMARY KEY,
  version TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  type TEXT NOT NULL,  -- 'legacy' or 'precise'
  features_count INT,
  gates_count INT,
  rules_count INT,
  weight_sum FLOAT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  description TEXT
);

-- New table: score_history (complete audit trail)
CREATE TABLE IF NOT EXISTS score_history (
  id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL,
  model_version TEXT NOT NULL,
  legacy_score FLOAT,
  legacy_factors JSON,
  precise_score FLOAT,
  precise_factors JSON,
  precise_confidence FLOAT,
  scored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (shipment_id) REFERENCES shipments(id)
);
```

### 2.2 Snapshot All Data Models Before v3.0

**Before deploying new model, create snapshots:**

```bash
# 1. Export current database schema (v2.1)
sqlite3 /app/data/cbp_sentry.db ".schema" > /app/backups/cbp_sentry_v2.1_schema.sql

# 2. Export all data
sqlite3 /app/data/cbp_sentry.db ".dump" > /app/backups/cbp_sentry_v2.1_dump.sql

# 3. Create git commit with schema snapshot
git add services/data/schemas/v2.1_schema.sql
git add services/data/schemas/v2.1_dump.sql
git commit -m "snapshot: Data model v2.1 (legacy) before v3.0 deployment"

# 4. Tag the commit
git tag -a v2.1-snapshot -m "Legacy model data snapshot before v3.0 deployment"
```

### 2.3 Document Model Metadata

Create schema documentation file:

**File:** `services/data/schemas/MODEL_VERSIONS.md`

```markdown
# Model Versions & Schemas

## v2.1 (Legacy)

**Status:** Frozen (snapshot only)
**Type:** Rule-based, 7-factor
**Weights:** 110% (over-weighted, see documentation)
**Features:** 72 CBP fields
**Gates:** 3 (H1, H2, H3 horizons)
**Rules:** 8 implicit rules
**Score Range:** 0-100
**Latency:** ~50ms
**Creation Date:** 2026-05-23
**Snapshot Date:** 2026-06-12

**Schema:** `cbp_sentry.db` (v2.1)
- shipments.h1_score, h2_score, h1_h2_score
- shipments.risk_score
- shipments.risk_breakdown
- No model_version field (assumed 'v2.1')

**Rollback:** Restore from `cbp_sentry_v2.1_dump.sql`

---

## v3.0 (Precise Risk Model)

**Status:** Active (testing)
**Type:** ML-based, XGBoost classifier
**Weights:** 100% (normalized, correct)
**Features:** 72 CBP fields → 7 weighted factors
**Gates:** 3 (Deterministic → ML → Uncertainty)
**Rules:** 8 explicit rules + XGBoost
**Score Range:** 0-100 (integer)
**Confidence Range:** 0-1.0
**Latency:** <100ms
**Creation Date:** 2026-06-12
**Deployment Date:** 2026-06-12

**Schema Extensions:** `cbp_sentry.db` (v3.0)
- shipments.model_version = 'v3.0' (new field)
- shipments.precise_score (new field, replaces risk_score calculation)
- shipments.model_confidence (new field)
- shipments.model_factors (new field, JSON)
- score_history table (new, tracks both models)
- model_metadata table (new, versioning)

**Score Calculation:**
- Input: 72 CBP features
- Feature Engineering: 7 weighted factors (100% total)
- Gate 1: Deterministic rules (OFAC, commodity, corridor)
- Gate 2: XGBoost classifier (probability → score)
- Gate 3: Uncertainty quantification (confidence interval)
- Output: {risk_score, confidence, factors, explanations}

**Rollback:** 
- Option A: Revert feature flag to v2.1, use legacy calculation
- Option B: Restore from snapshot, drop v3.0 fields
```

---

## 3. Feature Flag Configuration for v3.0 Full Testing

### 3.1 Update Configuration

**File:** `services/api/.env.local` (local testing)

```bash
# DISABLE legacy model, ENABLE new model with 100% traffic
USE_PRECISE_RISK_MODEL=true
PRECISE_RISK_ENGINE_URL=http://precise-risk-engine:8004
PRECISE_RISK_ENGINE_TIMEOUT=5
TRAFFIC_PERCENTAGE=100          # ← 100%, not 10% or 0%
MODEL_VERSION_ACTIVE=v3.0       # ← New field: which model is active
LEGACY_MODEL_AVAILABLE=true     # ← Can switch back if needed
```

**File:** `docker-compose.yml` (local deployment)

```yaml
sentry-api:
  environment:
    USE_PRECISE_RISK_MODEL: "true"
    TRAFFIC_PERCENTAGE: "100"
    MODEL_VERSION_ACTIVE: "v3.0"
    LEGACY_MODEL_AVAILABLE: "true"  # For quick fallback
```

### 3.2 Update phase2_integration.py

Modify the feature flag and routing logic to support model versioning:

**New FeatureFlagManager class method:**

```python
class FeatureFlagManager:
    def get_model_version(self) -> str:
        """Get currently active model version"""
        return os.getenv('MODEL_VERSION_ACTIVE', 'v2.1')
    
    def set_model_version(self, version: str):
        """Switch between model versions"""
        valid_versions = ['v2.1', 'v3.0']
        if version not in valid_versions:
            raise ValueError(f"Invalid model version: {version}")
        os.environ['MODEL_VERSION_ACTIVE'] = version
        logger.info(f"Model switched to {version}")
    
    def record_score_history(self, shipment_id: str, legacy_score: float, 
                           precise_score: float, confidence: float):
        """Log both model scores for comparison"""
        # Save to score_history table
        ...
```

**Updated score_shipment_phase2() function:**

```python
async def score_shipment_phase2(shipment_id: str, shipment_data: dict) -> dict:
    """Score using active model version (v2.1 or v3.0)"""
    
    model_version = flag_manager.get_model_version()
    
    if model_version == 'v3.0':
        # Use only Precise Risk Model
        try:
            precise_score = await client.score(shipment_data)
            return {
                'shipment_id': shipment_id,
                'risk_score': precise_score['risk_score'],
                'model_version': 'v3.0',
                'model_used': 'precise-risk-engine',
                'confidence': precise_score.get('confidence', 0.0),
                'factors': precise_score.get('factors', {}),
                'scored_at': datetime.now()
            }
        except Exception as e:
            logger.error(f"v3.0 scoring failed: {e}")
            # FALLBACK to v2.1 if v3.0 fails
            return score_shipment_legacy(shipment_data)
    
    elif model_version == 'v2.1':
        # Use legacy model
        return score_shipment_legacy(shipment_data)
```

---

## 4. UI Changes — Show Model Version in Tabs

### 4.1 Update Shipment Response

Modify `sentry-api/routes/shipments.py` to include model version:

```python
@router.get("/api/shipments/{shipment_id}")
async def get_shipment(shipment_id: str):
    shipment = await db.get_shipment(shipment_id)
    
    return {
        "id": shipment.id,
        "shipper_name": shipment.shipper_name,
        # ... existing fields ...
        
        # NEW: Model version info
        "model_version": shipment.model_version or "v2.1",
        "risk_score": shipment.precise_score or shipment.risk_score,
        "model_used": "precise-risk-engine" if shipment.model_version == "v3.0" else "legacy",
        "confidence": shipment.model_confidence or None,
        "factors": shipment.model_factors or shipment.risk_breakdown,
        
        # For debugging/comparison
        "legacy_score": shipment.h1_h2_score,  # For side-by-side comparison
    }
```

### 4.2 Update React Components

**File:** `ui/src/components/V2Header.tsx` (or relevant component)

Add model version badge:

```tsx
// Show which model is active
<div className="model-version-badge">
  <span className="badge badge-primary">
    {shipment?.model_version || 'v2.1'}
  </span>
  <span className="badge-label">
    {shipment?.model_used === 'precise-risk-engine' ? '🤖 ML Model' : '📋 Legacy'}
  </span>
</div>

// Show confidence (new model feature)
{shipment?.confidence && (
  <div className="confidence-indicator">
    Confidence: {(shipment.confidence * 100).toFixed(1)}%
  </div>
)}

// Show factors breakdown (for new model)
{shipment?.factors && (
  <div className="factors-breakdown">
    <h4>Risk Factors (v3.0)</h4>
    {shipment.factors.map(factor => (
      <div key={factor.name} className="factor-row">
        <span>{factor.name}</span>
        <span className="weight">{factor.weight}%</span>
        <span className="score">{factor.score}</span>
      </div>
    ))}
  </div>
)}
```

### 4.3 Add Model Version Tab (Optional)

Create new UI tab showing model information:

**File:** `ui/src/pages/V2InvestigationsPage.tsx`

Add tab: "Model Details" showing:
- Active model version (v2.1 vs v3.0)
- Model type (Legacy vs ML)
- Confidence level
- Feature importance
- Score explanation
- Comparison to legacy score (if available)

---

## 5. Scoring Recalculation Strategy

### 5.1 Rescore All Existing Shipments with v3.0

Create migration script:

**File:** `services/data/migrate_scores_v2_to_v3.py`

```python
import asyncio
from datetime import datetime
from sqlalchemy import update

async def migrate_all_scores_to_v3():
    """
    Rescore all existing shipments with v3.0 model
    Preserves old scores in legacy_score field
    """
    
    async with AsyncSession(engine) as session:
        # Get all shipments
        shipments = await session.execute(
            select(Shipment).where(Shipment.model_version.is_(None))
        )
        
        for shipment in shipments.scalars():
            # Score with v3.0
            new_score = await score_with_precise_model(shipment)
            
            # Update shipment
            await session.execute(
                update(Shipment)
                .where(Shipment.id == shipment.id)
                .values(
                    model_version='v3.0',
                    precise_score=new_score['risk_score'],
                    model_confidence=new_score['confidence'],
                    model_factors=new_score['factors'],
                    legacy_score=shipment.h1_h2_score,  # Preserve old score
                    h1_h2_score=new_score['risk_score']  # Update for UI
                )
            )
            
            # Log to score_history
            await session.execute(
                insert(ScoreHistory).values(
                    shipment_id=shipment.id,
                    model_version='v3.0',
                    precise_score=new_score['risk_score'],
                    precise_confidence=new_score['confidence'],
                    precise_factors=new_score['factors'],
                    legacy_score=shipment.h1_h2_score,
                    scored_at=datetime.now()
                )
            )
        
        await session.commit()
        print(f"✅ Migrated {len(shipments)} shipments to v3.0")

# Run during deployment
if __name__ == '__main__':
    asyncio.run(migrate_all_scores_to_v3())
```

**Execution:**

```bash
cd services/data
python migrate_scores_v2_to_v3.py
# Output: ✅ Migrated 30 shipments to v3.0
```

---

## 6. Rollback Strategy

### 6.1 Quick Rollback (Feature Flag)

Switch back to v2.1 without redeployment:

```bash
# Via API (instant)
curl -X POST http://localhost:8000/api/model-version \
  -H "Content-Type: application/json" \
  -d '{"active_version": "v2.1", "fallback_model": "legacy"}'

# Or environment variable (requires restart)
export MODEL_VERSION_ACTIVE=v2.1
docker-compose restart sentry-api
```

### 6.2 Full Rollback (Database)

Restore from snapshot if needed:

```bash
# Stop services
docker-compose down

# Restore v2.1 database
rm /app/data/cbp_sentry.db
sqlite3 /app/data/cbp_sentry.db < /app/backups/cbp_sentry_v2.1_dump.sql

# Restart with legacy model
export MODEL_VERSION_ACTIVE=v2.1
docker-compose up -d

# Verify
curl http://localhost:8000/api/model-version
# Response: {"active_version": "v2.1", "model_used": "legacy"}
```

### 6.3 Partial Rollback (Keep v3.0, Revert Scores)

Keep v3.0 infrastructure but revert to legacy scores:

```sql
-- Swap back to legacy scores
UPDATE shipments 
SET h1_h2_score = legacy_score 
WHERE model_version = 'v3.0';

-- Mark as rolled back
UPDATE shipments 
SET model_version = 'v2.1-reverted' 
WHERE model_version = 'v3.0';
```

---

## 7. Testing Checklist

### Phase 0: Pre-Deployment (Data Snapshots)

- [ ] Export v2.1 schema: `sqlite3 ... ".schema" > v2.1_schema.sql`
- [ ] Export v2.1 data: `sqlite3 ... ".dump" > v2.1_dump.sql`
- [ ] Commit snapshots to git with tag `v2.1-snapshot`
- [ ] Verify snapshots can be restored: `sqlite3 < v2.1_dump.sql`
- [ ] Document rollback procedure in this file

### Phase 1: Local Deployment

- [ ] Update `.env.local`: `USE_PRECISE_RISK_MODEL=true, TRAFFIC_PERCENTAGE=100`
- [ ] Start with `./scripts/local_startup.sh`
- [ ] Verify precise-risk-engine healthy: `curl http://localhost:8007/health`
- [ ] Verify API uses v3.0: `curl http://localhost:8000/api/model-version`
- [ ] Check logs: `docker-compose logs sentry-api | grep model_version`

### Phase 2: Rescore All Data

- [ ] Run migration: `python migrate_scores_v2_to_v3.py`
- [ ] Verify all scores updated: `SELECT COUNT(*) WHERE model_version='v3.0'`
- [ ] Check score_history table populated: `SELECT COUNT(*) FROM score_history`
- [ ] Compare legacy vs v3.0 scores: `SELECT * FROM score_history LIMIT 10`

### Phase 3: UI Testing

- [ ] Load dashboard: http://localhost:3001
- [ ] Verify model version badge shows "v3.0" in Investigations tab
- [ ] Check confidence scores displayed (new feature)
- [ ] Verify risk factors breakdown shows v3.0 factors (not H1/H2/H3)
- [ ] Test model comparison: side-by-side legacy vs v3.0 scores
- [ ] Check all 6 tabs load with new model data

### Phase 4: Full Application Testing

- [ ] Create new shipment → scored with v3.0 → shows v3.0 in UI
- [ ] Edit shipment → rescore with v3.0
- [ ] Generate synopsis (Gemini) → uses v3.0 score
- [ ] Entity resolution → returns with v3.0 risk context
- [ ] Risk corridors → aggregated from v3.0 scores
- [ ] Export referral package → includes v3.0 factors

### Phase 5: Validation

- [ ] Score distribution: histogram of v3.0 scores vs v2.1
- [ ] Classification rates: % HOLD, EXAMINE, CLEAR (v3.0 vs v2.1)
- [ ] Latency: average time to score shipment (<100ms for v3.0)
- [ ] Confidence levels: mean/median/std of confidence scores
- [ ] Error rate: % fallback to legacy (should be ~0% if system healthy)
- [ ] Coverage: % shipments with v3.0 score (should be 100%)

### Phase 6: Rollback Test (Optional)

- [ ] Switch model version: `curl -X POST ... MODEL_VERSION_ACTIVE=v2.1`
- [ ] Verify API uses v2.1: `curl http://localhost:8000/api/model-version`
- [ ] Check scores revert to legacy calculation
- [ ] Stop containers, restore snapshot, verify data integrity
- [ ] Document any issues found during rollback

---

## 8. Deployment Commands

### Local Testing (v3.0 Full)

```bash
# Update environment
cat > services/api/.env.local << 'EOF'
USE_PRECISE_RISK_MODEL=true
TRAFFIC_PERCENTAGE=100
MODEL_VERSION_ACTIVE=v3.0
LEGACY_MODEL_AVAILABLE=true
EOF

# Deploy with new config
./scripts/local_startup.sh clean

# Rescore all data
cd services/data
python migrate_scores_v2_to_v3.py

# Verify
curl http://localhost:8000/api/model-version
# Response: {"active_version": "v3.0", "model_used": "precise-risk-engine"}

# Open UI
open http://localhost:3001
```

### Staging Deployment (v3.0 Full)

```bash
# Push with v3.0 config
git checkout -b test/v3.0-full-testing
git add services/api/.env.staging
git commit -m "config: Switch to v3.0 model (100% traffic) for full testing"
git push origin test/v3.0-full-testing

# GitHub Actions will automatically:
# 1. Detect changes
# 2. Build services
# 3. Deploy to Cloud Run
# 4. Run smoke tests
# 5. Execute migration script
```

---

## 9. Model Version API Endpoints

New endpoints to add to `sentry-api/routes/`:

```python
@router.get("/api/model-version")
async def get_active_model():
    """Get currently active model version"""
    return {
        "active_version": os.getenv('MODEL_VERSION_ACTIVE', 'v2.1'),
        "model_used": "precise-risk-engine" if os.getenv('MODEL_VERSION_ACTIVE') == 'v3.0' else "legacy",
        "traffic_percentage": int(os.getenv('TRAFFIC_PERCENTAGE', 0)),
        "feature_flag_enabled": os.getenv('USE_PRECISE_RISK_MODEL') == 'true',
        "legacy_available": os.getenv('LEGACY_MODEL_AVAILABLE') == 'true'
    }

@router.post("/api/model-version")
async def switch_model_version(request: dict):
    """Switch between model versions (requires auth)"""
    new_version = request.get('active_version')
    if new_version not in ['v2.1', 'v3.0']:
        raise ValueError(f"Invalid version: {new_version}")
    os.environ['MODEL_VERSION_ACTIVE'] = new_version
    return {"switched_to": new_version}

@router.get("/api/shipments/{shipment_id}/score-history")
async def get_score_history(shipment_id: str):
    """Get all scores for this shipment across model versions"""
    history = await db.get_score_history(shipment_id)
    return {
        "shipment_id": shipment_id,
        "v2.1_legacy_score": history.legacy_score,
        "v3.0_precise_score": history.precise_score,
        "v3.0_confidence": history.precise_confidence,
        "differences": history.precise_score - history.legacy_score,
        "percent_change": ((history.precise_score - history.legacy_score) / history.legacy_score * 100) if history.legacy_score else 0
    }
```

---

## 10. Success Criteria

✅ **Testing Complete When:**

1. All shipments scored with v3.0 (model_version = 'v3.0' for all records)
2. UI displays "v3.0" badge in Investigation tabs
3. Confidence scores visible in risk scoring details
4. Risk factors breakdown shows 7 factors (not H1/H2/H3)
5. Score comparison available (legacy vs v3.0)
6. Rollback tested and confirmed working
7. No fallback events (error rate ~0%)
8. All 6 tabs load and display v3.0 data correctly
9. Score distribution documented (mean, median, std)
10. Classification rates documented (% HOLD, EXAMINE, CLEAR)

---

## 11. Next Steps

1. **Review & Approve:** Share this plan with stakeholders
2. **Create Snapshots:** Execute Phase 0 (data backup)
3. **Deploy Locally:** Test with v3.0 full (Phase 1-3)
4. **Validate:** Complete all testing checklist (Phase 4-5)
5. **Optional Rollback Test:** Confirm rollback works (Phase 6)
6. **Document Results:** Save score distributions, timings, accuracy metrics
7. **Decide:** Proceed to production or iterate on v3.0
