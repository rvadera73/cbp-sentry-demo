# Quick Start: Deploy & Test Phase 2 Integration (30 minutes)

## What You're Running (3 Services)

```
┌─────────────────────────────────────────────────────────────┐
│  Web Browser                                                 │
│  http://localhost:3000 (React UI - CBP Sentry Frontend)     │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP (REST API)
┌─────────────────▼───────────────────────────────────────────┐
│  CBP Sentry API  (FastAPI/Python)                           │
│  http://localhost:8000 (Port 8000)                          │
│  - score_shipment_phase2() routes to new OR legacy model     │
│  - Feature flag controls routing                             │
│  - Fallback mechanism if new model fails                    │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP (if USE_PRECISE_RISK_MODEL=true)
┌─────────────────▼───────────────────────────────────────────┐
│  Precise Risk Engine API (Flask/Python)                     │
│  http://localhost:8004 (Port 8004)  ← NEW SERVICE          │
│  - Trained XGBoost model                                    │
│  - Isolation Forest + SHAP                                  │
│  - cbp.yaml config (7 factors, 3 gates, 8 rules)           │
└─────────────────────────────────────────────────────────────┘
                  │ Shared
            ┌─────▼──────────┐
            │ PostgreSQL     │
            │ Redis Cache    │
            │ GCP Storage    │
            └────────────────┘
```

---

## TERMINAL 1: Start Precise Risk Engine (New Microservice)

```bash
# Navigate to risk engine
cd /home/rahulvadera/cbp-sentry/services/risk-engine

# Install dependencies (one time)
pip install -r requirements.txt

# Start the Flask service
python -m flask run --port 8004

# You should see:
# ======== Running on http://127.0.0.1:8004 ========
# WARNING: This is a development server...
```

**Keep this terminal open!** The service needs to stay running.

---

## TERMINAL 2: Configure & Start CBP Sentry API

```bash
# Navigate to API
cd /home/rahulvadera/cbp-sentry/services/api

# Create Phase 2 configuration
export USE_PRECISE_RISK_MODEL=false      # Start SAFE (legacy only)
export PRECISE_RISK_ENGINE_URL=http://localhost:8004
export PRECISE_RISK_ENGINE_TIMEOUT=5
export TRAFFIC_PERCENTAGE=0

# Verify imports work
python3 -c "from phase2_integration import *; print('✅ Phase 2 integration module loaded')"

# Start CBP Sentry API
python main.py

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Keep this terminal open!** The API needs to stay running.

---

## TERMINAL 3: Run Tests & Interact

```bash
# Use this terminal to test the system
cd /home/rahulvadera/cbp-sentry

# Test 1: Verify both services are running
echo "Testing Precise Risk Engine..."
curl -s http://localhost:8004/health | jq .

echo "Testing CBP Sentry API..."
curl -s http://localhost:8000/health | jq .

# Test 2: Check feature flag (should be OFF/false)
echo "Checking feature flag..."
curl -s http://localhost:8000/api/feature-flag | jq .

# Test 3: Score a shipment with LEGACY model (safe default)
echo "Scoring shipment with legacy model..."
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "test-001",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 2.5,
    "element9_is_mismatch": 0
  }' | jq .

# Test 4: ENABLE new model (change to 10% traffic)
echo "Enabling new model..."
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 10}' | jq .

# Test 5: Score again (should route to new model or fallback)
echo "Scoring shipment with new model enabled..."
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "test-002",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 2.5,
    "element9_is_mismatch": 1
  }' | jq .

# Test 6: Compare models side-by-side
echo "Comparing both models..."
curl -X POST http://localhost:8000/api/shipment/score/compare \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "compare-001",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 5.5,
    "element9_is_mismatch": 1
  }' | jq .

# Test 7: Disable new model (instant rollback)
echo "Disabling new model (rollback)..."
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, "traffic_percentage": 0}' | jq .

# Test 8: Verify all 5 tabs still work (optional, requires frontend)
# curl http://localhost:3000/command-center
# curl http://localhost:3000/active-investigations
# curl http://localhost:3000/shipment-intelligence
# curl http://localhost:3000/entity-resolution
# curl http://localhost:3000/v2/ai-tuning
```

---

## How to Test (Step-by-Step)

### STEP 1: Start Both Services (5 mins)

**Terminal 1:**
```bash
cd /home/rahulvadera/cbp-sentry/services/risk-engine
python -m flask run --port 8004
# Wait for: ======== Running on http://127.0.0.1:8004 ========
```

**Terminal 2:**
```bash
cd /home/rahulvadera/cbp-sentry/services/api
export USE_PRECISE_RISK_MODEL=false
python main.py
# Wait for: INFO:     Uvicorn running on http://0.0.0.0:8000
```

### STEP 2: Verify Setup (5 mins)

**Terminal 3:**
```bash
# Both should return 200 OK with status: healthy
curl http://localhost:8004/health
curl http://localhost:8000/health
```

### STEP 3: Test Legacy Model (5 mins)

**Terminal 3:**
```bash
# Score 3 shipments with legacy (safe default)
# Should all show: route="legacy", model_version="legacy"
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "legacy-1",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 2.5
  }' | jq '.route, .model_version, .latency_ms'
```

**Expected Output:**
```
"legacy"
"legacy"
47.3
```

✅ If you see this → Legacy model working!

### STEP 4: Test New Model (5 mins)

**Terminal 3:**
```bash
# Enable new model
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "traffic_percentage": 50}'

# Score 3 more shipments
# Should show: route="new", model_version="precise-risk-model-v1"
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "new-1",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 2.5
  }' | jq '.route, .model_version, .latency_ms'
```

**Expected Output:**
```
"new"
"precise-risk-model-v1"
52.1
```

✅ If you see this → New model working!

### STEP 5: Test Fallback (5 mins)

**Terminal 3:**
```bash
# Stop the precise-risk-engine service
# (go to Terminal 1, press Ctrl+C)

# Score again with new model enabled
# Should fallback: route="fallback", model_version="legacy"
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "fallback-test",
    "origin_country": "CN",
    "destination_country": "US",
    "declared_value_usd": 50000,
    "dwell_days": 2.5
  }' | jq '.route, .fallback_reason'

# Should show fallback_reason: "Connection error to..."

# Restart the service (Terminal 1)
# Then score again - should route to "new" again
```

---

## What's Actually Deployed

### Service 1: Precise Risk Engine API (Port 8004)
- **Location**: `/home/rahulvadera/cbp-sentry/services/risk-engine/`
- **Tech**: Flask (Python)
- **What it does**: Runs the trained XGBoost model
- **Files**:
  - `app.py` - Flask factory
  - `models/risk_model.py` - PreciseRiskModel class
  - `config/cbp.yaml` - 7 factors, 3 gates, 8 rules
  - `/models/*.pkl` - Trained models (XGBoost, Isolation Forest, SHAP)

### Service 2: CBP Sentry API (Port 8000)
- **Location**: `/home/rahulvadera/cbp-sentry/services/api/`
- **Tech**: FastAPI (Python)
- **What's new**:
  - `phase2_integration.py` - Feature flag + routing logic
  - Modified `main.py` - Uses phase2_integration for scoring
- **What it does**: Routes shipment scoring to new OR legacy model

### Service 3: Web Frontend (Port 3000)
- **Location**: `/home/rahulvadera/cbp-sentry/ui/`
- **Tech**: React (JavaScript)
- **What's unchanged**: All 5 tabs still work
- **What's improved**: Shows scores from either model

---

## Traffic Ramping Timeline

Once both services running and tested:

```
TIMESTAMP     PHASE          ACTION                           RESULT
────────────────────────────────────────────────────────────────────
Day 0, 10am   Legacy Only    USE_PRECISE_RISK_MODEL=false    All legacy
Day 0, 2pm    10% New        TRAFFIC_PERCENTAGE=10           90% legacy, 10% new
Day 1, 10am   50% New        TRAFFIC_PERCENTAGE=50           50/50 split
Day 2, 10am   90% New        TRAFFIC_PERCENTAGE=90           90% new, 10% legacy
Day 3, 10am   100% New       TRAFFIC_PERCENTAGE=100          All new model
Day 4, 10am   Decision       Stakeholder feedback → GO/NO-GO
```

**Instant Rollback Anytime:**
```bash
# If something wrong at ANY stage:
curl -X POST http://localhost:8000/api/feature-flag \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Immediate switch to legacy (no redeployment, no downtime)
```

---

## Checklist for You

### Before Starting:
- [ ] Downloaded/cloned CBP Sentry code
- [ ] Python 3.10+ installed
- [ ] pip dependencies can be installed
- [ ] 3 terminals available
- [ ] Ports 8000, 8004, 3000 free

### During Setup:
- [ ] Terminal 1: Risk engine starts (port 8004)
- [ ] Terminal 2: CBP API starts (port 8000)
- [ ] Terminal 3: Tests pass
  - [ ] /health endpoints respond
  - [ ] Feature flag accessible
  - [ ] Legacy model scores shipments
  - [ ] New model scores shipments
  - [ ] Fallback works (tested)

### During Testing:
- [ ] Score with legacy (5 cases)
- [ ] Score with new (5 cases)
- [ ] Compare models (3 cases)
- [ ] Test fallback (stop service, score, restart)
- [ ] Test traffic ramping (0%, 10%, 50%, 90%, 100%)

### After Testing:
- [ ] All 5 tabs still load
- [ ] No console errors
- [ ] Latency < 200ms
- [ ] Scores make sense
- [ ] Ready for stakeholder feedback

---

## Common Issues & Fixes

### "Connection refused" to localhost:8004
- **Cause**: Precise Risk Engine not running
- **Fix**: Check Terminal 1, start if needed

### "Connection refused" to localhost:8000
- **Cause**: CBP Sentry API not running
- **Fix**: Check Terminal 2, start if needed

### Feature flag returns error
- **Cause**: CBP API doesn't have phase2_integration.py
- **Fix**: Copy phase2_integration.py to services/api/

### Score returns "error": "Connection error"
- **Cause**: New model enabled but service down
- **Fix**: This is EXPECTED - fallback to legacy should trigger

### High latency (>1000ms)
- **Cause**: Services on same machine, high CPU load
- **Fix**: Close other apps, try again

### "ModuleNotFoundError: No module named 'flask'"
- **Cause**: Dependencies not installed
- **Fix**: `pip install -r requirements.txt` in risk-engine folder

---

## Success Criteria (30 minutes)

✅ **Precise Risk Engine** running on port 8004  
✅ **CBP Sentry API** running on port 8000  
✅ **Feature flag** responsive (GET/POST)  
✅ **Legacy model** scores shipments  
✅ **New model** scores shipments (if enabled)  
✅ **Fallback** works (switches to legacy on error)  
✅ **Model comparison** shows both scores  
✅ **All latency** < 200ms  
✅ **All 5 tabs** still functional  

---

## Next: Share with Stakeholders

Once you complete above checklist, you have:
1. ✅ Integrated Precise Risk Model with CBP Sentry
2. ✅ Tested end-to-end locally
3. ✅ Ready to demo to stakeholders

**Tell them**:
- "I have a working new risk model"
- "Feature flag lets us test safely (0% traffic initially)"
- "Can gradually increase traffic (10% → 50% → 90% → 100%)"
- "Can rollback instantly if needed"
- "All 5 tabs still work"
- "Want to test with real data?"

---

## TLDR - The Absolute Minimum

```bash
# Terminal 1
cd /home/rahulvadera/cbp-sentry/services/risk-engine
pip install -r requirements.txt
python -m flask run --port 8004

# Terminal 2
cd /home/rahulvadera/cbp-sentry/services/api
export USE_PRECISE_RISK_MODEL=false
python main.py

# Terminal 3
curl http://localhost:8004/health  # Should work
curl http://localhost:8000/health  # Should work
curl -X POST http://localhost:8000/api/shipment/score \
  -H "Content-Type: application/json" \
  -d '{"shipment_id":"test","origin_country":"CN","destination_country":"US","declared_value_usd":50000,"dwell_days":2.5}' | jq .

# Done! Both services running, feature flag OFF (safe), ready for testing.
```

---

**Ready? Start Terminal 1 above! 🚀**
