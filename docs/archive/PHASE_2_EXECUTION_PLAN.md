# Phase 2 Execution Plan - Integration with CBP Sentry

**Timeline**: Weeks 5-8 (4 weeks)  
**Status**: Ready to execute NOW  
**Goal**: Integrate precise-risk-engine-api with cbp-sentry-api, ensure all 5 tabs work, test with real data

---

## Phase 2 Overview

### What We're Doing
1. **Service Integration** (Weeks 5-6)
   - Add HTTP calls from cbp-sentry-api to precise-risk-engine-api
   - Implement feature flag (use_legacy_model)
   - Archive legacy risk_scoring_engine.py

2. **UI Enhancements** (Week 7)
   - Add domain selector to V2AITuningPage
   - Dynamic factor loading per domain

3. **Testing & Rollout** (Week 8)
   - Regression testing (all 5 tabs)
   - Gradual traffic ramp (10%→50%→90%)
   - Go-live approval

### Success Criteria
- ✅ All 5 CBP Sentry tabs work unchanged
- ✅ Feature flag toggles between old/new model
- ✅ No performance degradation (<200ms latency)
- ✅ Backward compatible (zero breaking changes)
- ✅ Rollback tested and working

---

## Week 5-6: Service Integration

### Step 1: Add Feature Flag to cbp-sentry-api

**File**: `services/api/config.py` (or environment)

```python
# Feature flag for gradual rollout
USE_PRECISE_RISK_MODEL = os.getenv('USE_PRECISE_RISK_MODEL', 'false').lower() == 'true'
PRECISE_RISK_ENGINE_URL = os.getenv('PRECISE_RISK_ENGINE_URL', 'http://localhost:8004')
PRECISE_RISK_ENGINE_TIMEOUT = int(os.getenv('PRECISE_RISK_ENGINE_TIMEOUT', 5))
```

### Step 2: Create Risk Model Client

**File**: `services/api/clients/precise_risk_client.py`

```python
import requests
import logging
from typing import Dict, Any
from config import PRECISE_RISK_ENGINE_URL, PRECISE_RISK_ENGINE_TIMEOUT

logger = logging.getLogger(__name__)

class PreciseRiskClient:
    """HTTP client for precise-risk-engine-api"""
    
    def __init__(self, base_url: str = PRECISE_RISK_ENGINE_URL):
        self.base_url = base_url
        self.timeout = PRECISE_RISK_ENGINE_TIMEOUT
    
    def score_entity(self, domain: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score an entity using precise risk engine"""
        try:
            url = f"{self.base_url}/api/v1/scoring/score"
            payload = {
                "entity_id": entity_data.get("id", "unknown"),
                "entity_data": entity_data
            }
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling precise risk engine: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """Check if precise risk engine is available"""
        try:
            url = f"{self.base_url}/health"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except:
            return False
```

### Step 3: Refactor Risk Scoring Endpoint

**File**: `services/api/routes/shipments.py` (modify score method)

```python
from clients.precise_risk_client import PreciseRiskClient
from config import USE_PRECISE_RISK_MODEL

risk_client = PreciseRiskClient()

@shipments_bp.route('/shipment/<id>/score', methods=['GET'])
def score_shipment(id):
    """Score a shipment using either legacy or new model"""
    
    shipment = db.session.query(Shipment).get(id)
    if not shipment:
        return {"error": "Shipment not found"}, 404
    
    # Prepare entity data
    entity_data = {
        "id": shipment.id,
        "origin_country": shipment.origin,
        "destination_country": shipment.destination,
        "hs_code": shipment.hs_code,
        "declared_value_usd": shipment.value,
        "dwell_days": shipment.dwell_days,
        "element9_is_mismatch": shipment.element9_mismatch,
        # ... other fields
    }
    
    try:
        # Route to new model or legacy based on feature flag
        if USE_PRECISE_RISK_MODEL and risk_client.health_check():
            result = risk_client.score_entity('cbp', entity_data)
            result['model_version'] = 'precise-risk-model-v1'
        else:
            # Fallback to legacy
            result = legacy_score_shipment(shipment)
            result['model_version'] = 'legacy'
        
        return result, 200
    
    except Exception as e:
        # Fall back to legacy on error
        logger.error(f"Error in new model: {str(e)}, falling back to legacy")
        result = legacy_score_shipment(shipment)
        result['model_version'] = 'legacy'
        result['error'] = 'Used fallback model'
        return result, 200
```

### Step 4: Archive Legacy Code

```bash
# Rename legacy code (don't delete - keep for rollback)
mv services/api/services/risk_scoring_engine.py \
   services/api/services/risk_scoring_engine_legacy.py

mv services/api/services/risk_models.py \
   services/api/services/risk_models_legacy.py

# Add deprecation comment at top of legacy files
echo "# DEPRECATED: Use precise-risk-engine-api instead. Kept for rollback." \
  >> services/api/services/risk_scoring_engine_legacy.py
```

---

## Week 7: UI Enhancements - V2AITuningPage

### Step 1: Add Domain Selector

**File**: `ui/src/v2/pages/V2AITuningPage.tsx`

```typescript
import React, { useState, useEffect } from 'react';

interface V2AITuningPageProps {
  // existing props
}

const V2AITuningPage: React.FC<V2AITuningPageProps> = (props) => {
  const [selectedDomain, setSelectedDomain] = useState<string>('cbp');
  const [factors, setFactors] = useState<any[]>([]);
  
  // Load factors based on selected domain
  useEffect(() => {
    loadFactorsForDomain(selectedDomain);
  }, [selectedDomain]);
  
  const loadFactorsForDomain = async (domain: string) => {
    try {
      const response = await fetch(`/api/v1/metrics/${domain}`);
      const data = await response.json();
      setFactors(data.factors || []);
    } catch (e) {
      console.error('Error loading factors:', e);
    }
  };
  
  return (
    <div className="v2-ai-tuning-page">
      {/* Domain Selector */}
      <div className="domain-selector">
        <label>Select Domain:</label>
        <select 
          value={selectedDomain} 
          onChange={(e) => setSelectedDomain(e.target.value)}
        >
          <option value="cbp">CBP - Illegal Transshipment</option>
          <option value="fda">FDA - Imports Fraud (Phase 3)</option>
          <option value="opioid">Opioid Detection (Phase 3)</option>
        </select>
      </div>
      
      {/* Factor Sliders */}
      <div className="factors-section">
        {factors.map(factor => (
          <div key={factor.id} className="factor-slider">
            <label>{factor.name} ({(factor.weight * 100).toFixed(0)}%)</label>
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={factor.weight * 100}
              onChange={(e) => updateFactor(factor.id, parseInt(e.target.value) / 100)}
            />
          </div>
        ))}
      </div>
      
      {/* Rest of existing UI */}
    </div>
  );
};

export default V2AITuningPage;
```

---

## Week 8: Testing & Validation

### Integration Test Suite

```python
# File: services/api/tests/test_precise_risk_integration.py

import pytest
import requests
from config import USE_PRECISE_RISK_MODEL

class TestPreciseRiskIntegration:
    
    def test_health_check_both_services(self):
        """Ensure both cbp-sentry-api and precise-risk-engine-api are healthy"""
        cbp_health = requests.get('http://localhost:8000/health')
        engine_health = requests.get('http://localhost:8004/health')
        assert cbp_health.status_code == 200
        assert engine_health.status_code == 200
    
    def test_score_endpoint_uses_new_model(self):
        """Verify scoring endpoint calls new model when flag is true"""
        response = requests.get('http://localhost:8000/api/shipment/test-001/score')
        assert response.status_code == 200
        data = response.json()
        assert 'model_version' in data
        if USE_PRECISE_RISK_MODEL:
            assert data['model_version'] == 'precise-risk-model-v1'
    
    def test_fallback_to_legacy_on_error(self):
        """Verify fallback to legacy model if new model unavailable"""
        # Stop precise-risk-engine (simulate failure)
        # Call endpoint
        # Verify it returns legacy result with fallback notice
        pass
    
    def test_all_five_tabs_functional(self):
        """Regression test: All 5 CBP Sentry tabs work"""
        tabs = [
            'CommandCenter',
            'ActiveInvestigations',
            'ShipmentIntelligence',
            'EntityResolution',
            'V2AITuningPage'
        ]
        
        for tab in tabs:
            response = requests.get(f'http://localhost:3000/{tab}')
            assert response.status_code == 200, f"Tab {tab} broken"
    
    def test_feature_flag_toggle(self):
        """Test toggling feature flag"""
        # Set flag to False (legacy)
        os.environ['USE_PRECISE_RISK_MODEL'] = 'false'
        response = requests.get('http://localhost:8000/api/shipment/test-001/score')
        assert response.json()['model_version'] == 'legacy'
        
        # Set flag to True (new model)
        os.environ['USE_PRECISE_RISK_MODEL'] = 'true'
        response = requests.get('http://localhost:8000/api/shipment/test-001/score')
        assert response.json()['model_version'] == 'precise-risk-model-v1'
    
    def test_latency_under_threshold(self):
        """Verify API latency <200ms P95"""
        times = []
        for i in range(100):
            import time
            start = time.time()
            requests.get('http://localhost:8000/api/shipment/test-001/score')
            times.append((time.time() - start) * 1000)
        
        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 200, f"P95 latency {p95}ms exceeds threshold"
```

### Traffic Ramping Strategy

**Week 8 Timeline**:
- **Days 1-2**: 10% traffic on new model, 90% legacy (monitor metrics)
- **Days 3-4**: 50% traffic on new model, 50% legacy (compare results)
- **Days 5-6**: 90% traffic on new model, 10% legacy (full validation)
- **Day 7**: 100% traffic on new model OR rollback decision

```bash
# Script to manage traffic ramp
# File: scripts/traffic_ramp.sh

set_traffic_percentage() {
  local percentage=$1
  local use_new_model=$([[ $percentage -gt 50 ]] && echo 'true' || echo 'false')
  
  # Update feature flag
  kubectl set env deployment/cbp-sentry-api \
    USE_PRECISE_RISK_MODEL=$use_new_model \
    TRAFFIC_PERCENTAGE=$percentage
  
  echo "Traffic set to $percentage% new model"
}

# Execute ramp
set_traffic_percentage 10   # Day 1-2
sleep 2d
set_traffic_percentage 50   # Day 3-4
sleep 2d
set_traffic_percentage 90   # Day 5-6
sleep 2d
set_traffic_percentage 100  # Day 7 (if all good)
```

---

## Week 8 Decision Gate

### Go/No-Go Checklist

- [ ] XGBoost AUC maintained (no regression)
- [ ] All 4 API endpoints working
- [ ] Latency <200ms P95
- [ ] All 5 CBP Sentry tabs functional
- [ ] Feature flag toggle working
- [ ] Fallback to legacy tested
- [ ] Zero errors in 100+ production requests
- [ ] Stakeholder approval received

### Outcomes

**✅ GO**: All criteria met → Proceed to Phase 3 planning
**⚠️ REMEDIATE**: 1-2 issues → Fix and retest (2-3 days)
**❌ ROLLBACK**: 3+ issues → Revert to legacy, investigate, plan remediation

---

## Deliverables

### Code Changes
- [ ] Feature flag added to cbp-sentry-api
- [ ] PreciseRiskClient created and integrated
- [ ] Risk scoring endpoint refactored
- [ ] Legacy code archived (not deleted)
- [ ] Domain selector added to V2AITuningPage
- [ ] Integration test suite created

### Testing
- [ ] Unit tests passing (legacy + new model paths)
- [ ] Integration tests passing (both services)
- [ ] Regression tests passing (all 5 tabs)
- [ ] Latency benchmarks met
- [ ] Fallback tested and working

### Documentation
- [ ] Integration guide (how to call precise-risk-engine-api)
- [ ] Feature flag guide (how to toggle)
- [ ] Troubleshooting guide (common issues)
- [ ] Rollback procedure (if needed)

---

## Environment Setup

### .env Variables Needed

```bash
# cbp-sentry-api (.env.local)
USE_PRECISE_RISK_MODEL=false           # Start with legacy, ramp up
PRECISE_RISK_ENGINE_URL=http://localhost:8004
PRECISE_RISK_ENGINE_TIMEOUT=5

# precise-risk-engine-api (.env.local)
FLASK_ENV=production
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cbp_sentry
DB_USER=postgres
DB_PASSWORD=***
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## Estimated Effort

| Task | Owner | Hours | Days |
|------|-------|-------|------|
| Feature flag implementation | Backend | 4 | 1 |
| Risk client integration | Backend | 6 | 1-2 |
| V2AITuningPage domain selector | Frontend | 4 | 1 |
| Integration tests | QA | 8 | 1-2 |
| Traffic ramping & monitoring | DevOps | 4 | 3-4 |
| Regression testing | QA | 8 | 2 |
| Documentation | Tech Writer | 4 | 1 |
| **TOTAL** | | **38** | **~2 weeks** |

---

## Success = Production Ready

Once Phase 2 is complete and approved:
✅ Precise Risk Engine live in production
✅ All existing functionality preserved
✅ New model accessible to users
✅ Feature flag allows instant rollback
✅ Ready for stakeholder feedback and UAT

---

**Next**: Ready to start Week 5 implementation? ⬇️
