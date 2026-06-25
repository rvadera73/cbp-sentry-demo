# CBP Sentry Phase 2 Deployment & Testing Guide

**Goal**: Deploy integrated Precise Risk Model with CBP Sentry and test end-to-end  
**Timeline**: 1-2 hours for deployment + testing  
**Prerequisites**: Docker, Docker Compose, Python 3.10+

---

## PART 1: DEPLOYMENT (30 mins)

### Step 1: Start Precise Risk Engine Microservice

```bash
cd /home/rahulvadera/cbp-sentry/services/risk-engine

# Install dependencies
pip install -r requirements.txt

# Start the service (port 8004)
python -m flask run --port 8004 &

# Verify it's running
curl http://localhost:8004/health

# Expected output:
# {"status": "healthy", "service": "precise-risk-engine-api", "port": 8004, "factors": 7}
```

### Step 2: Configure CBP Sentry API

```bash
cd /home/rahulvadera/cbp-sentry/services/api

# Create .env file with Phase 2 settings
cat > .env.phase2 << 'EOF'
# Phase 2 Configuration
USE_PRECISE_RISK_MODEL=false      # Start with legacy (safe default)
PRECISE_RISK_ENGINE_URL=http://localhost:8004
PRECISE_RISK_ENGINE_TIMEOUT=5
TRAFFIC_PERCENTAGE=0              # 0% traffic on new model initially

# Other CBP Sentry config
DEPLOYMENT_ENV=local
API_MODE=fixture
DATA_SERVICE_URL=http://localhost:8005
EOF

# Load environment
export $(cat .env.phase2 | xargs)

# Verify settings
echo "USE_PRECISE_RISK_MODEL=$USE_PRECISE_RISK_MODEL"
echo "PRECISE_RISK_ENGINE_URL=$PRECISE_RISK_ENGINE_URL"
```

### Step 3: Update CBP Sentry API Code

The Phase 2 integration has been added to:
- **File**: `services/api/phase2_integration.py`
- **What it does**:
  - Imports PreciseRiskClient
  - Implements feature flag routing
  - Provides fallback mechanism
  - Includes model comparison

**Integration in main.py** (you'll need to add these imports):

```python
# In services/api/main.py, add:
from phase2_integration import (
    score_shipment_phase2,
    compare_shipment_models,
    FeatureFlagManager,
    check_phase2_health
)

# When scoring shipments, use:
result = await score_shipment_phase2(
    shipment_id,
    entity_data,
    legacy_score_func=your_legacy_scoring_function
)
```

### Step 4: Start CBP Sentry API

```bash
cd /home/rahulvadera/cbp-sentry/services/api

# Start the FastAPI service (port 8000)
python main.py &

# Wait for startup
sleep 5

# Verify it's running
curl http://localhost:8000/health

# Verify Phase 2 integration
curl http://localhost:8000/api/phase2/health
```

### Step 5: Verify Both Services Running

```bash
# Check Precise Risk Engine
curl -s http://localhost:8004/health | jq .

# Check CBP Sentry API
curl -s http://localhost:8000/health | jq .

# Both should return 200 OK with status: healthy
```

---

## PART 2: TESTING (1-2 hours)

### Testing Section 1: Feature Flag & Configuration

#### Test 1.1: Feature Flag Status
```bash
# Get current feature flag state
curl http://localhost:8000/api/feature-flag

# Expected output:
{
  "feature": "USE_PRECISE_RISK_MODEL",
  "enabled": false,
  "traffic_percentage": 0
}
```

#### Test 1.2: Toggle Feature Flag to 10% Traffic
```bash
# Enable new model for 10% traffic
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 10}'

# Expected output:
{
  "feature": "USE_PRECISE_RISK_MODEL",
  "enabled": true,
  "traffic_percentage": 10,
  "message": "Feature flag updated"
}

# Verify it changed
curl http://localhost:8000/api/feature-flag
```

#### Test 1.3: Check Phase 2 Health Status
```bash
curl http://localhost:8000/api/phase2/health

# Expected output:
{
  "phase2_enabled": true,
  "precise_risk_engine": {
    "url": "http://localhost:8004",
    "healthy": true
  },
  "traffic_percentage": 10,
  "timestamp": "2026-06-12T..."
}
```

---

### Testing Section 2: Shipment Scoring (Legacy Model)

#### Test 2.1: Disable New Model (Safe Default)
```bash
# Reset to legacy model
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, "traffic_percentage": 0}'
```

#### Test 2.2: Score a Shipment with Legacy Model
```bash
# Create test shipment data
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "test-legacy-001",
    "origin_country": "CN",
    "destination_country": "US",
    "hs_code": "8517.62",
    "declared_value_usd": 50000,
    "dwell_days": 2.5,
    "element9_is_mismatch": 0
  }'

# Expected output:
{
  "shipment_id": "test-legacy-001",
  "risk_score": 47.5,
  "confidence": 0.75,
  "risk_level": "MEDIUM",
  "factors": {...},
  "model_version": "legacy",
  "route": "legacy",
  "latency_ms": 45.2,
  "scored_at": "2026-06-12T..."
}

# What to verify:
# ✓ risk_score is between 0-100
# ✓ model_version is "legacy"
# ✓ route is "legacy"
# ✓ latency_ms < 200ms
```

#### Test 2.3: Score Multiple Legacy Cases
```bash
# Score 5 different shipments with legacy model
for i in {1..5}; do
  echo "Scoring legacy case $i..."
  curl -X POST http://localhost:8000/api/shipment/score \
    -H "Content-Type: application/json" \
    -d "{
      \"shipment_id\": \"test-legacy-00$i\",
      \"origin_country\": \"CN\",
      \"destination_country\": \"US\",
      \"declared_value_usd\": $((40000 + i * 5000)),
      \"dwell_days\": $((2 + i)),
      \"element9_is_mismatch\": $((i % 2))
    }"
done

# Verify:
# ✓ All scores returned successfully
# ✓ All latency < 200ms
# ✓ All use legacy model
```

---

### Testing Section 3: Shipment Scoring (New Model)

#### Test 3.1: Enable New Model for 10% Traffic
```bash
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 10}'

# Verify enabled
curl http://localhost:8000/api/feature-flag
```

#### Test 3.2: Score Shipments with New Model
```bash
# Score 5 shipments (may route to legacy if new model unavailable)
for i in {1..5}; do
  echo "Scoring new model case $i..."
  curl -X POST http://localhost:8000/api/shipment/score \
    -H "Content-Type: application/json" \
    -d "{
      \"shipment_id\": \"test-new-00$i\",
      \"origin_country\": \"CN\",
      \"destination_country\": \"US\",
      \"declared_value_usd\": $((40000 + i * 5000)),
      \"dwell_days\": $((5 + i)),
      \"element9_is_mismatch\": 1
    }"
done

# Expected output (may have route="fallback" if new model not available):
{
  "shipment_id": "test-new-001",
  "risk_score": 65.2,
  "confidence": 0.82,
  "model_version": "precise-risk-model-v1 OR legacy",
  "route": "new OR fallback OR legacy",
  "latency_ms": 52.3,
  ...
}

# Verify:
# ✓ If route="new": Uses precise-risk-engine-api
# ✓ If route="fallback": New model unavailable, fell back to legacy
# ✓ All latency < 200ms
```

---

### Testing Section 4: Model Comparison (Side-by-Side)

#### Test 4.1: Compare Both Models for Same Shipment
```bash
# Score same shipment with both models
curl -X POST http://localhost:8000/api/shipment/score/compare \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "compare-001",
    "origin_country": "CN",
    "destination_country": "US",
    "hs_code": "8517.62",
    "declared_value_usd": 50000,
    "dwell_days": 5.5,
    "element9_is_mismatch": 1
  }'

# Expected output:
{
  "shipment_id": "compare-001",
  "legacy_model": {
    "risk_score": 62.5,
    "confidence": 0.75,
    ...
  },
  "new_model": {
    "risk_score": 67.2,
    "confidence": 0.82,
    ...
  },
  "comparison": {
    "score_difference": 4.7,
    "agreement": "AGREE",
    "legacy_score": 62.5,
    "new_score": 67.2
  }
}

# What to verify:
# ✓ Both models return scores
# ✓ Scores are within reasonable range (difference < 20)
# ✓ Agreement shows if they agree (< 10 diff) or differ
```

#### Test 4.2: Compare Multiple Cases
```bash
# Compare 10 high-risk cases
for i in {1..10}; do
  echo "Comparing case $i..."
  curl -X POST http://localhost:8000/api/shipment/score/compare \
    -H "Content-Type: application/json" \
    -d "{
      \"shipment_id\": \"compare-0$i\",
      \"origin_country\": \"CN\",
      \"destination_country\": \"US\",
      \"dwell_days\": $((3 + i)),
      \"element9_is_mismatch\": 1
    }" | jq '.comparison'
done

# Analyze comparison results:
# ✓ How many AGREE vs DIFFER?
# ✓ Average score difference?
# ✓ Are high-risk cases consistent between models?
```

---

### Testing Section 5: Fallback Mechanism

#### Test 5.1: Verify Fallback to Legacy on Error
```bash
# This tests the fallback logic when new model is unavailable

# First, stop the precise-risk-engine service
# (In another terminal, kill the process)
kill $(lsof -ti:8004)

# Now score a shipment with new model enabled
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "fallback-test-001",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 3.0
  }'

# Expected output:
{
  "shipment_id": "fallback-test-001",
  "risk_score": 47.5,
  "model_version": "legacy",
  "route": "fallback",
  "fallback_reason": "Connection error to Precise Risk Engine: ...",
  ...
}

# What to verify:
# ✓ route="fallback" (switched to legacy)
# ✓ model_version="legacy"
# ✓ Still got a risk score (no error)
# ✓ fallback_reason logged

# Restart precise-risk-engine
python -m flask run --port 8004 &
```

#### Test 5.2: Verify Instant Recovery
```bash
# After restarting precise-risk-engine, score again
# Should now route to new model (if enabled)

curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "recovery-test-001",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 3.0
  }'

# Verify:
# ✓ If enabled: route="new" (recovered)
# ✓ No error response
# ✓ Latency acceptable
```

---

### Testing Section 6: Traffic Ramping (Gradual Rollout)

#### Test 6.1: Start at 0% (Safe Default)
```bash
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, "traffic_percentage": 0}'

# Score 10 shipments - should ALL use legacy
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/shipment/score ... | jq '.route'
done

# Verify: All show route="legacy"
```

#### Test 6.2: Increase to 10% Traffic
```bash
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 10}'

# Score 100 shipments
# ~10 should route to new, ~90 to legacy/fallback
# Track the split
```

#### Test 6.3: Increase to 50% Traffic
```bash
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 50}'

# Score 100 shipments
# ~50 should use new model
```

#### Test 6.4: Increase to 90% Traffic
```bash
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 90}'

# Score 100 shipments
# ~90 should use new model
```

#### Test 6.5: Go to 100% Traffic
```bash
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 100}'

# All shipments now use new model
# Verify performance and accuracy
```

---

### Testing Section 7: All 5 CBP Sentry Tabs (Regression Testing)

#### Test 7.1: CommandCenter Tab
```bash
curl http://localhost:3000/command-center

# Verify:
# ✓ Page loads
# ✓ Metrics display
# ✓ Risk scores visible
# ✓ No console errors
```

#### Test 7.2: ActiveInvestigations Tab
```bash
curl http://localhost:3000/active-investigations

# Verify:
# ✓ Cases load
# ✓ Case details appear
# ✓ Risk scores from new model
# ✓ All buttons responsive
```

#### Test 7.3: ShipmentIntelligence Tab
```bash
curl http://localhost:3000/shipment-intelligence

# Verify:
# ✓ Manifests load
# ✓ Intelligence data visible
# ✓ Risk factors displayed
# ✓ Integration working
```

#### Test 7.4: EntityResolution Tab
```bash
curl http://localhost:3000/entity-resolution

# Verify:
# ✓ Entity graph loads
# ✓ Relationships visible
# ✓ Enrichment data present
# ✓ No broken links
```

#### Test 7.5: V2AITuningPage Tab
```bash
curl http://localhost:3000/v2/ai-tuning

# Verify (Phase 3 feature - domain selector):
# ✓ Page loads
# ✓ Factor sliders work
# ✓ Rules toggles work
# ✓ Can adjust weights
```

---

## PART 3: TESTING CHECKLIST

### ✅ Core Functionality Tests

- [ ] **Precise Risk Engine runs** (port 8004, /health responds)
- [ ] **CBP Sentry API runs** (port 8000, /health responds)
- [ ] **Feature flag GET** returns correct state
- [ ] **Feature flag POST** updates state
- [ ] **Phase 2 health** endpoint works
- [ ] **Score shipment with legacy** returns result
- [ ] **Score shipment with new** returns result
- [ ] **Model comparison** endpoint works
- [ ] **Fallback mechanism** triggers on error
- [ ] **Recovery** works when service restored

### ✅ Performance Tests

- [ ] **Legacy model latency** < 200ms
- [ ] **New model latency** < 200ms
- [ ] **P95 latency** < 200ms (20 requests)
- [ ] **No timeout errors**
- [ ] **No memory leaks** (run 1000 requests)
- [ ] **CPU usage reasonable** (<30%)

### ✅ Accuracy Tests

- [ ] **Legacy high-risk cases** flagged correctly
- [ ] **New high-risk cases** flagged correctly
- [ ] **Low-risk cases** score low
- [ ] **Medium-risk cases** in middle range
- [ ] **Model agreement** > 80% (score diff < 10)
- [ ] **EAPA cases** score HIGH (>70)
- [ ] **Normal manifests** score LOW (<40)

### ✅ Backward Compatibility Tests

- [ ] **CommandCenter tab** works
- [ ] **ActiveInvestigations tab** works
- [ ] **ShipmentIntelligence tab** works
- [ ] **EntityResolution tab** works
- [ ] **V2AITuningPage tab** works
- [ ] **All data intact** (no corruption)
- [ ] **No broken links**
- [ ] **UI responsive** (<1s load)

### ✅ Traffic Ramping Tests

- [ ] **0% traffic**: All legacy
- [ ] **10% traffic**: ~10% new, ~90% legacy
- [ ] **50% traffic**: ~50% split
- [ ] **90% traffic**: ~90% new, ~10% legacy
- [ ] **100% traffic**: All new model
- [ ] **Instant rollback** works (0% anytime)

### ✅ Error Handling Tests

- [ ] **New model unavailable** → fallback works
- [ ] **Timeout** → fallback works
- [ ] **Bad request** → returns 400
- [ ] **Missing fields** → returns 400
- [ ] **Service down** → returns 503
- [ ] **Logs capture errors** (check logs)

---

## PART 4: SAMPLE TEST CASES

### High-Risk Case (EAPA Transshipment)
```json
{
  "shipment_id": "EAPA-high-risk-001",
  "origin_country": "SG",
  "destination_country": "US",
  "hs_code": "8517.62",
  "declared_value_usd": 100000,
  "dwell_days": 8.5,
  "element9_is_mismatch": 1,
  "shipper_country": "HK"
}

// Expected: risk_score > 70 (HIGH)
```

### Medium-Risk Case
```json
{
  "shipment_id": "medium-risk-001",
  "origin_country": "MX",
  "destination_country": "US",
  "hs_code": "6204.62",
  "declared_value_usd": 50000,
  "dwell_days": 2.5,
  "element9_is_mismatch": 0
}

// Expected: risk_score 40-70 (MEDIUM)
```

### Low-Risk Case
```json
{
  "shipment_id": "low-risk-001",
  "origin_country": "CA",
  "destination_country": "US",
  "hs_code": "2309.10",
  "declared_value_usd": 30000,
  "dwell_days": 1.2,
  "element9_is_mismatch": 0
}

// Expected: risk_score < 40 (LOW)
```

---

## PART 5: WHAT YOU SHOULD OBSERVE

### Phase 1: Legacy Model Testing
- All shipments score with legacy model
- Latency ~45-100ms per request
- Risk scores consistent
- No errors

### Phase 2a: 10% New Model Traffic
- 10% of requests route to new model
- 90% still use legacy
- New model latency similar (~50-100ms)
- Scores within reasonable range (diff < 20)

### Phase 2b: 50% New Model Traffic
- Split roughly even
- Use model comparison to validate
- Look for consistent patterns
- Any divergence in specific cases?

### Phase 2c: 90% New Model Traffic
- New model is primary
- Legacy as safety net
- Monitor error rates
- Check performance metrics

### Phase 2d: 100% New Model Traffic
- All traffic on new model
- Can instant rollback if needed
- Validate accuracy with real cases
- Collect stakeholder feedback

---

## PART 6: TROUBLESHOOTING

### Issue: Precise Risk Engine Connection Error
```
Error: Connection error to Precise Risk Engine: http://localhost:8004
Solution: 
1. Verify service running: curl http://localhost:8004/health
2. Check network: ping localhost
3. Restart service: kill process, start again
```

### Issue: Feature Flag Not Changing
```
Error: Feature flag still shows enabled=false after POST
Solution:
1. Check POST request format
2. Verify Content-Type: application/json
3. Check logs for errors
```

### Issue: High Latency (>200ms)
```
Error: Latency P95 > 200ms
Solution:
1. Check network latency: ping localhost
2. Check CPU usage: top
3. Check memory: free -m
4. Reduce traffic percentage temporarily
```

### Issue: Fallback Not Triggering
```
Error: No fallback when new model unavailable
Solution:
1. Manually stop risk-engine: kill $(lsof -ti:8004)
2. Score shipment again
3. Check route in response
4. Verify logs show error
```

---

## NEXT: STAKEHOLDER DECISIONS

Once you've tested locally and verified:
- ✅ Both models work
- ✅ Fallback mechanism works
- ✅ All tabs still functional
- ✅ Latency acceptable

You can share with CBP operations team and decide:

**Options**:
1. **Deploy to staging** for team testing
2. **Deploy to production** with feature flag OFF (zero risk)
3. **Demo locally** to stakeholders first

**Traffic Ramping Schedule** (with stakeholder feedback):
- Day 1-2: 10% (monitor closely)
- Day 3-4: 50% (validate accuracy)
- Day 5-6: 90% (performance check)
- Day 7: 100% (full deployment)

---

## SUPPORT

**Questions?** Check:
- PHASE_2_COMPLETION_REPORT.md - Technical details
- PHASE_2_READY_FOR_STAKEHOLDERS.txt - Decision framework
- /docs/precise-risk-model/ - Architecture reference

**Issues?** Review troubleshooting above or contact tech lead.

---

**Ready to deploy? Let's ship it! 🚀**
