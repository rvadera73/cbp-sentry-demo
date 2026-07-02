# Phase 1: Activate the 7-Factor Risk Scoring Model
**Estimated Duration:** 4-6 hours  
**Goal:** Make risk_scoring_engine.py the active system (fix 91 vs 39 mismatch)

---

## Step-by-Step Implementation

### STEP 1: Create Risk Scoring API Routes (1.5 hours)

**File:** `/api/services/risk_scoring/routes.py` (NEW)

```python
"""
Risk Scoring API endpoints - activate 7-factor model
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from services.api.risk_scoring_engine import RiskScoringEngine
from models.schemas import RiskScoreBreakdownResponse
from core.shipments_db import update_shipment_risk_score

router = APIRouter(prefix="/api", tags=["scoring"])
logger = logging.getLogger(__name__)

# Initialize engine (loads ML models on startup)
engine = RiskScoringEngine()


@router.post(
    "/score/full-breakdown/{shipment_id}",
    response_model=RiskScoreBreakdownResponse,
    summary="Calculate Full Risk Score Breakdown",
    description="Use 7-factor ML model to calculate comprehensive risk score"
)
async def calculate_full_risk_breakdown(
    shipment_id: str,
    shipment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate risk score using 7-factor model:
    1. Documentation Risk (25%)
    2. Commodity Sensitivity (15%)
    3. Routing Risk (15%)
    4. Party Profile Risk (15%)
    5. Corridor Risk (20%)
    6. Pattern Anomaly (10%)
    7. Time Sensitivity (10%)
    
    Returns full breakdown with:
    - Component scores + weights
    - Calculation table (for transparency)
    - Final score (0-100)
    - Confidence interval
    
    Args:
        shipment_id: Shipment identifier
        shipment_data: Dict with all shipment fields
        
    Returns:
        RiskScoreBreakdown with detailed component breakdown
    """
    try:
        # Validate input
        if not shipment_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shipment data is required"
            )
        
        logger.info(f"Calculating risk score for shipment {shipment_id}")
        
        # Calculate using 7-factor model
        breakdown = engine.score_shipment(shipment_data)
        
        # Convert to dict for response
        response_data = breakdown.to_dict()
        
        # Persist to database
        try:
            update_shipment_risk_score(
                shipment_id=shipment_id,
                calculated_risk_score=breakdown.final_score,
                risk_score_calculated_at=datetime.utcnow(),
                risk_score_breakdown=response_data,
                confidence_interval=breakdown.confidence_interval
            )
            logger.info(f"Persisted score {breakdown.final_score} for {shipment_id}")
        except Exception as e:
            logger.error(f"Failed to persist score: {e}")
            # Don't fail the API call if DB write fails
        
        logger.info(
            f"Shipment {shipment_id} scored: {breakdown.final_score}/100 "
            f"({breakdown.confidence_interval})"
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error calculating risk score for {shipment_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate risk score: {str(e)}"
        )


@router.get(
    "/score/{shipment_id}",
    response_model=Dict[str, Any],
    summary="Get Cached Risk Score",
    description="Return cached risk score if available, otherwise calculate"
)
async def get_risk_score(
    shipment_id: str,
    recalculate: bool = False
) -> Dict[str, Any]:
    """
    Get risk score for a shipment.
    
    Args:
        shipment_id: Shipment identifier
        recalculate: Force recalculation (ignores cache)
        
    Returns:
        Risk score with timestamp
    """
    try:
        from core.shipments_db import get_shipment_by_id
        
        shipment = get_shipment_by_id(shipment_id)
        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shipment {shipment_id} not found"
            )
        
        # Return calculated score if available and not forcing recalculation
        if shipment.get("calculated_risk_score") and not recalculate:
            return {
                "shipment_id": shipment_id,
                "risk_score": shipment["calculated_risk_score"],
                "source": "calculated",
                "calculated_at": shipment.get("risk_score_calculated_at"),
                "confidence_interval": shipment.get("confidence_interval"),
                "cached": True
            }
        
        # Otherwise calculate fresh
        breakdown = engine.score_shipment(shipment)
        return {
            "shipment_id": shipment_id,
            "risk_score": breakdown.final_score,
            "source": "calculated",
            "calculated_at": datetime.utcnow().isoformat(),
            "confidence_interval": breakdown.confidence_interval,
            "cached": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching risk score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch risk score: {str(e)}"
        )
```

**File:** `/api/main.py` (MODIFY)

Add to FastAPI app:
```python
# Add this import at top
from services.risk_scoring import routes as risk_scoring_routes

# Add this in app creation section
app.include_router(risk_scoring_routes.router)
```

---

### STEP 2: Update Database Schema (1 hour)

**File:** `/api/core/shipments_db.py` (MODIFY)

Add function to persist calculated scores:
```python
def update_shipment_risk_score(
    shipment_id: int,
    calculated_risk_score: float,
    risk_score_calculated_at: datetime,
    risk_score_breakdown: Dict,
    confidence_interval: str
):
    """Update shipment with calculated risk score"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get current shipment to preserve other fields
        cursor.execute(
            "SELECT * FROM shipments WHERE id = ?",
            (shipment_id,)
        )
        shipment = cursor.fetchone()
        
        if not shipment:
            logger.warning(f"Shipment {shipment_id} not found, skipping update")
            return
        
        # Update with calculated values
        cursor.execute("""
            UPDATE shipments 
            SET 
                calculated_risk_score = ?,
                risk_score_calculated_at = ?,
                risk_score_breakdown = ?,
                confidence_interval = ?
            WHERE id = ?
        """, (
            calculated_risk_score,
            risk_score_calculated_at,
            json.dumps(risk_score_breakdown),
            confidence_interval,
            shipment_id
        ))
        
        conn.commit()
        logger.info(f"Updated risk score for shipment {shipment_id}")
        
    except Exception as e:
        logger.error(f"Failed to update shipment {shipment_id}: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
```

Add import at top:
```python
import json
from datetime import datetime
```

**File:** `/api/core/db.py` (MODIFY)

Update schema creation to add new columns:
```python
async def create_schema():
    """Create database schema"""
    if not _db_connection:
        return

    try:
        # ... existing tables ...
        
        # Scores table - UPDATE with new columns
        await _db_connection.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                risk_score REAL,
                calculated_risk_score REAL,  -- NEW: calculated by 7-factor model
                confidence_interval TEXT,     -- NEW: e.g., "85±2.5"
                risk_score_calculated_at TIMESTAMP,  -- NEW: when calculated
                risk_score_breakdown TEXT,    -- NEW: JSON breakdown
                threat_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entity_resolutions(id)
            )
        """)
        
        # Also add to shipments table for direct access
        # (Note: SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS,
        #  so we'll handle this in a migration script)
        
        await _db_connection.commit()
        logger.info("Database schema initialized")
    
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        raise
```

**Migration Script:** `/scripts/add_risk_score_columns.py` (NEW)

```python
"""
Database migration: Add calculated risk score columns to shipments table
Run once to add new columns for storing calculated scores
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "api" / "cbp_sentry.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(shipments)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # Add missing columns
        if "calculated_risk_score" not in columns:
            cursor.execute("""
                ALTER TABLE shipments 
                ADD COLUMN calculated_risk_score REAL
            """)
            print("✓ Added calculated_risk_score column")
        
        if "risk_score_calculated_at" not in columns:
            cursor.execute("""
                ALTER TABLE shipments 
                ADD COLUMN risk_score_calculated_at TIMESTAMP
            """)
            print("✓ Added risk_score_calculated_at column")
        
        if "risk_score_breakdown" not in columns:
            cursor.execute("""
                ALTER TABLE shipments 
                ADD COLUMN risk_score_breakdown TEXT
            """)
            print("✓ Added risk_score_breakdown column")
        
        if "confidence_interval" not in columns:
            cursor.execute("""
                ALTER TABLE shipments 
                ADD COLUMN confidence_interval TEXT
            """)
            print("✓ Added confidence_interval column")
        
        # Create index on calculated_risk_score
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_calculated_risk_score 
            ON shipments(calculated_risk_score DESC)
        """)
        print("✓ Created index on calculated_risk_score")
        
        conn.commit()
        print("\n✅ Migration complete!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
```

Run migration:
```bash
cd /home/rahulvadera/cbp-sentry
python scripts/add_risk_score_columns.py
```

---

### STEP 3: Update Investigation Page (1.5 hours)

**File:** `/ui/src/pages/ModernCaseInvestigationPage.tsx` (MODIFY)

Replace the `fetchCase` function and add new state:

```typescript
interface RiskBreakdown {
  shipment_id: string;
  components: RiskComponent[];
  subtotal: number;
  final_score: number;
  confidence_interval: string;
  calculation_table?: any;
  corridor_risk_adjustment?: any;
  additional_adjustments?: any[];
}

interface RiskComponent {
  component: string;
  factor: string;
  score: number;
  weight: number;
  weighted_result: number;
  rationale: string;
  evidence: string[];
}

export default function ModernCaseInvestigationPage() {
  const { role } = useRole();
  const { shipmentId } = useParams<{ shipmentId?: string }>();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [riskBreakdown, setRiskBreakdown] = useState<RiskBreakdown | null>(null); // NEW
  const [threeLevelScore, setThreeLevelScore] = useState<ThreeLevelScoreData | null>(null); // Keep for now (deprecate later)
  const [loading, setLoading] = useState(true);
  const [loadingScore, setLoadingScore] = useState(false); // NEW
  const [showFeedback, setShowFeedback] = useState(false);
  const [showAltanaPanel, setShowAltanaPanel] = useState(false);

  // ... expandedSections state ...

  useEffect(() => {
    fetchCase();
  }, [shipmentId]);

  const fetchCase = async () => {
    try {
      let shipment: Case | null = null;

      if (shipmentId) {
        const response = await fetch(`${API_BASE_URL}/shipments`);
        const data = await response.json();
        if (data.shipments) {
          shipment = data.shipments.find((s: Case) => s.id === shipmentId) || null;
          if (shipment) {
            setCaseData(shipment);
          }
        }
      } else {
        const response = await fetch(`${API_BASE_URL}/shipments?limit=1`);
        const data = await response.json();
        if (data.shipments && data.shipments.length > 0) {
          shipment = data.shipments[0];
          setCaseData(shipment);
        }
      }

      // NEW: Calculate risk breakdown using 7-factor model
      if (shipment) {
        fetchRiskBreakdown(shipment);
      }
    } catch (error) {
      console.error('Failed to fetch case:', error);
    } finally {
      setLoading(false);
    }
  };

  // NEW: Fetch full risk breakdown from API
  const fetchRiskBreakdown = async (shipment: Case) => {
    setLoadingScore(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/score/full-breakdown/${shipment.id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(shipment)
        }
      );

      if (response.ok) {
        const breakdown = await response.json();
        setRiskBreakdown(breakdown);
        console.log('✓ Risk breakdown calculated:', breakdown.final_score);
      } else {
        console.warn('Failed to fetch risk breakdown:', response.status);
      }
    } catch (error) {
      console.error('Error fetching risk breakdown:', error);
    } finally {
      setLoadingScore(false);
    }
  };

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  if (loading || !caseData) {
    return <USWDSLayout title="Case Investigation"><div className="loading">Loading...</div></USWDSLayout>;
  }

  const getRiskColor = (score: number) => {
    if (score >= 90) return '#dc2626';
    if (score >= 70) return '#ea580c';
    if (score >= 50) return '#eab308';
    return '#22c55e';
  };

  const getRiskLevel = (score: number) => {
    if (score >= 90) return 'CRITICAL';
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'MEDIUM';
    return 'LOW';
  };

  // NEW: Use calculated score, fallback to DB
  const displayScore = riskBreakdown?.final_score ?? caseData.risk_score;

  return (
    <USWDSLayout title="Case Investigation">
      <div className="compact-dashboard">
        {/* HEADER ROW */}
        <div className="dashboard-header">
          <div className="header-left">
            <h2>{caseData.id}</h2>
            <p className="header-subtitle">
              {caseData.shipper_name} → {caseData.consignee_name}
            </p>
          </div>
          <div className="header-right">
            {/* CHANGED: Use calculated score instead of DB score */}
            <div className="score-display" style={{ borderColor: getRiskColor(displayScore) }}>
              <div className="score-number" style={{ color: getRiskColor(displayScore) }}>
                {Math.round(displayScore)}
              </div>
              <div className="score-label">RISK</div>
              <div className="risk-badge" style={{ backgroundColor: getRiskColor(displayScore) }}>
                {getRiskLevel(displayScore)}
              </div>
              {/* NEW: Show confidence interval */}
              {riskBreakdown?.confidence_interval && (
                <div className="confidence-note" style={{ fontSize: '11px', marginTop: '4px' }}>
                  {riskBreakdown.confidence_interval}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ... existing Overview section ... */}

        {/* NEW: RISK BREAKDOWN SECTION (7-Factor Model) */}
        {riskBreakdown && (
          <CollapsibleSection
            title="📊 7-Factor Risk Breakdown"
            expanded={expandedSections.scoring}
            onToggle={() => toggleSection('scoring')}
          >
            <div className="risk-breakdown">
              {/* Factor Summary */}
              <div className="factor-summary">
                <table>
                  <thead>
                    <tr>
                      <th>Factor</th>
                      <th align="right">Components</th>
                      <th align="right">Subtotal</th>
                      <th align="right">% of Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {riskBreakdown.calculation_table?.factor_summary?.map((factor, idx) => (
                      <tr key={idx}>
                        <td>{factor.factor}</td>
                        <td align="right">{factor.components}</td>
                        <td align="right">{factor.subtotal.toFixed(1)}</td>
                        <td align="right">{factor.percentage}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Component Details */}
              {riskBreakdown.components && (
                <div className="component-details">
                  <h4>Component Details</h4>
                  {Object.entries(
                    riskBreakdown.components.reduce((acc, comp) => {
                      if (!acc[comp.factor]) acc[comp.factor] = [];
                      acc[comp.factor].push(comp);
                      return acc;
                    }, {} as Record<string, RiskComponent[]>)
                  ).map(([factor, components]) => (
                    <div key={factor} className="factor-group">
                      <h5>{factor}</h5>
                      <table>
                        <tbody>
                          {components.map((comp, idx) => (
                            <tr key={idx}>
                              <td className="component-name">{comp.component}</td>
                              <td align="right" className="component-score">{comp.score.toFixed(1)}/10</td>
                              <td align="right" className="component-weight">×{comp.weight.toFixed(2)}</td>
                              <td align="right" className="component-result">=<strong>{comp.weighted_result.toFixed(1)}</strong></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              )}

              {/* Adjustments */}
              {(riskBreakdown.corridor_risk_adjustment || riskBreakdown.additional_adjustments) && (
                <div className="adjustments">
                  <h4>Adjustments</h4>
                  {riskBreakdown.corridor_risk_adjustment && (
                    <div className="adjustment-item">
                      <strong>Corridor Risk Adjustment</strong>
                      <p>{riskBreakdown.corridor_risk_adjustment.reason}</p>
                      <p>
                        {riskBreakdown.corridor_risk_adjustment.baseline.toFixed(1)} ×{' '}
                        {riskBreakdown.corridor_risk_adjustment.multiplier.toFixed(2)} ={' '}
                        +{riskBreakdown.corridor_risk_adjustment.adjustment_points.toFixed(1)}
                      </p>
                    </div>
                  )}
                  {riskBreakdown.additional_adjustments?.map((adj, idx) => (
                    <div key={idx} className="adjustment-item">
                      <strong>{adj.type}</strong>
                      <p>{adj.reason}</p>
                      <p>+{adj.adjustment_points.toFixed(1)} points</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Calculation Summary */}
              <div className="calculation-summary">
                <p><strong>Subtotal:</strong> {riskBreakdown.subtotal.toFixed(1)}</p>
                <p><strong>Adjustments:</strong> {(riskBreakdown.final_score - riskBreakdown.subtotal).toFixed(1)}</p>
                <p><strong>Final Score:</strong> <span style={{ fontSize: '1.2em', fontWeight: 'bold' }}>{riskBreakdown.final_score.toFixed(1)}</span>/100</p>
                <p><em>Confidence: {riskBreakdown.confidence_interval}</em></p>
              </div>
            </div>
          </CollapsibleSection>
        )}

        {/* Existing sections... */}
        {/* ... rest of the page ... */}
      </div>
    </USWDSLayout>
  );
}
```

Add CSS styling to `CompactDashboard.css`:
```css
.risk-breakdown {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.factor-summary table,
.component-details table,
.risk-breakdown table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.risk-breakdown table th,
.risk-breakdown table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.risk-breakdown table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.factor-group {
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-left: 3px solid #013060;
}

.factor-group h5 {
  margin: 0 0 8px 0;
  color: #013060;
  font-size: 14px;
}

.component-score { color: #ea580c; font-weight: bold; }
.component-weight { color: #666; }
.component-result { color: #22c55e; }

.adjustments {
  padding: 12px;
  background: #fffbea;
  border-left: 3px solid #ea580c;
}

.adjustment-item {
  margin-bottom: 12px;
  padding: 8px;
  background: white;
  border-radius: 4px;
}

.adjustment-item p {
  margin: 4px 0;
  font-size: 12px;
  color: #666;
}

.calculation-summary {
  padding: 16px;
  background: #f0f9ff;
  border-left: 3px solid #4AC4D3;
  border-radius: 4px;
}

.calculation-summary p {
  margin: 6px 0;
  font-size: 13px;
}

.confidence-note {
  color: #666;
  font-style: italic;
}
```

---

### STEP 4: Data Migration (30 minutes)

**Script:** `/scripts/migrate_risk_scores.py` (NEW)

```python
"""
Recalculate all existing shipment risk scores using 7-factor model
Run once after deploying new risk_scoring_engine
"""
import sys
from pathlib import Path
from datetime import datetime

# Add api module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from services.api.risk_scoring_engine import RiskScoringEngine
from core.shipments_db import get_all_shipments, update_shipment_risk_score

def migrate():
    engine = RiskScoringEngine()
    
    # Fetch all shipments
    data = get_all_shipments(limit=10000, offset=0)
    shipments = data['shipments']
    total = data['total']
    
    print(f"\nMigrating {total} shipments to 7-factor model...")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for i, shipment in enumerate(shipments, 1):
        try:
            # Calculate using 7-factor model
            breakdown = engine.score_shipment(shipment)
            
            # Update DB
            update_shipment_risk_score(
                shipment_id=shipment['id'],
                calculated_risk_score=breakdown.final_score,
                risk_score_calculated_at=datetime.utcnow(),
                risk_score_breakdown=breakdown.to_dict(),
                confidence_interval=breakdown.confidence_interval
            )
            
            success_count += 1
            
            # Print progress
            db_score = shipment.get('risk_score', 0)
            status = "✓" if abs(breakdown.final_score - db_score) < 5 else "⚠"
            print(
                f"[{i:3d}/{total}] {status} {shipment['id']:20s} "
                f"DB:{db_score:5.0f} → Calc:{breakdown.final_score:5.1f} "
                f"({breakdown.confidence_interval})"
            )
            
        except Exception as e:
            error_count += 1
            print(f"[{i:3d}/{total}] ❌ {shipment['id']:20s} ERROR: {str(e)[:50]}")
    
    print("=" * 60)
    print(f"\n✅ Migration complete!")
    print(f"   Success: {success_count}")
    print(f"   Errors:  {error_count}")
    print(f"\nNext steps:")
    print(f"  1. Review discrepancies between DB and calculated scores")
    print(f"  2. Run test suite to validate scores")
    print(f"  3. Deploy Phase 1 API changes")

if __name__ == "__main__":
    migrate()
```

Run migration:
```bash
cd /home/rahulvadera/cbp-sentry
python scripts/migrate_risk_scores.py
```

---

## Deployment Checklist

- [ ] Create `/api/services/risk_scoring/routes.py`
- [ ] Update `/api/main.py` to register routes
- [ ] Add new columns to `/api/core/shipments_db.py`
- [ ] Update schema in `/api/core/db.py`
- [ ] Run database migration: `python scripts/add_risk_score_columns.py`
- [ ] Update Investigation Page (`ModernCaseInvestigationPage.tsx`)
- [ ] Add CSS styling to `CompactDashboard.css`
- [ ] Test risk score calculation with sample shipment
- [ ] Run migration: `python scripts/migrate_risk_scores.py`
- [ ] Verify scores in Investigation View
- [ ] Remove dead code: delete `three_level_scorer.py` references
- [ ] Update documentation

---

## Testing

### Unit Test
```bash
cd /home/rahulvadera/cbp-sentry/api
pytest tests/test_risk_scoring.py -v
```

### Integration Test
```bash
# Start API
python -m uvicorn main:app --reload

# Test endpoint
curl -X POST http://localhost:8000/api/score/full-breakdown/greenfield \
  -H "Content-Type: application/json" \
  -d @/tmp/test_shipment.json

# Expected: 85-91 score with full breakdown
```

### Manual Test in UI
1. Open Investigation Page
2. Check that risk score calculates
3. Verify breakdown displays all 7 factors
4. Confirm calculation table shows component details
5. Check DB was updated with `calculated_risk_score`

---

## Success Metrics

✅ **Consistency:** Greenfield case shows 85-91 (not 91 in header and 39 in breakdown)  
✅ **Transparency:** Officer can see all 7 components with weights  
✅ **Accuracy:** Score aligns with expected values  
✅ **Performance:** Calculation < 2 seconds  
✅ **Persistence:** Calculated score saved to DB with timestamp  

---

## Rollback Plan

If Phase 1 fails:
1. Keep three_level_scorer.py as fallback
2. Revert Investigation Page to show threeLevelScore
3. Skip migration (don't update DB)
4. Debug error logs and redeploy

---

## Next Steps (Phase 2)

After Phase 1 is stable:
- Add officer feedback loop (correct/incorrect + reason)
- Train ML models (Isolation Forest, LightGBM)
- Retune factor weights based on feedback
- Deprecate three_level_scorer.py entirely
