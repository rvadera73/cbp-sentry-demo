# Week 4 Execution Checklist - Phase 1 Integration & Deployment

**Timeline**: June 13-15, 2026 (3 days)  
**Goal**: Deploy precise-risk-engine-api and verify AUC ≥ 0.82  
**Owner**: Backend Engineer + ML Engineer + DevOps  

---

## DAY 1 (THURSDAY, JUNE 13) - VALIDATION & TESTING

### Morning: Model Performance Validation (2 hours)

**Task 1.1: Load and Test XGBoost Model**
```bash
# Location: /home/rahulvadera/cbp-sentry/tests/test_model_performance.py

cd /home/rahulvadera/cbp-sentry

# Create test script to calculate AUC
cat > test_model_performance.py << 'EOF'
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

# Load data
X = np.load('data/feature_matrix_72.csv')  # Actually CSV, but numpy can read
y = pd.read_csv('data/training_data.csv')['label'].values

# Split (same as training)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# Load trained model
with open('models/xgboost_model.json', 'r') as f:
    # Note: XGBoost JSON model needs to be loaded with xgboost
    import xgboost as xgb
    model = xgb.XGBClassifier()
    model.load_model('models/xgboost_model.json')

# Predict
y_pred_proba = model.predict_proba(X_test)[:, 1]
y_pred = model.predict(X_test)

# Calculate metrics
auc = roc_auc_score(y_test, y_pred_proba)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print(f"XGBoost Performance:")
print(f"  AUC:       {auc:.4f} (target: ≥ 0.82)")
print(f"  Precision: {precision:.4f} (target: ≥ 0.30)")
print(f"  Recall:    {recall:.4f} (target: ≥ 0.70)")
print(f"  F1:        {f1:.4f}")

if auc >= 0.82:
    print("\n✅ MODEL QUALITY GATE PASSED - Proceed to deployment")
else:
    print("\n❌ MODEL QUALITY GATE FAILED - Investigate and retrain")
EOF

python test_model_performance.py
```

**Expected Output**:
```
XGBoost Performance:
  AUC:       0.84 (target: ≥ 0.82)
  Precision: 0.35 (target: ≥ 0.30)
  Recall:    0.72 (target: ≥ 0.70)
  F1:        0.48

✅ MODEL QUALITY GATE PASSED - Proceed to deployment
```

**Checklist**:
- [ ] XGBoost model loads without errors
- [ ] AUC ≥ 0.82: `____` (actual value)
- [ ] Precision ≥ 0.30: `____`
- [ ] Recall ≥ 0.70: `____`
- [ ] Decision: ✅ PASS or ❌ FAIL

---

### Afternoon: Local Flask App Testing (3 hours)

**Task 1.2: Start Flask Development Server**
```bash
cd /home/rahulvadera/cbp-sentry/services/risk-engine

# Install dependencies (if needed)
pip install -r requirements.txt

# Start Flask app
export FLASK_APP=app.py
export FLASK_ENV=development
python -m flask run --port 8004 &

# Wait 5 seconds for startup
sleep 5

# Test health check
curl http://localhost:8004/health

# Expected output:
# {"status": "healthy", "service": "precise-risk-engine-api", "port": 8004, "factors": 7}
```

**Checklist**:
- [ ] Flask app starts without errors
- [ ] Health check responds: `____` (HTTP code)
- [ ] Service name correct: `____`
- [ ] Port 8004: [ ] CORRECT [ ] WRONG
- [ ] Factors loaded: `____` (should be 7)

---

**Task 1.3: Test Scoring Endpoint**
```bash
# Create sample entity to score
cat > test_entity.json << 'EOF'
{
  "entity_id": "manifest-test-001",
  "shipment_date": "2026-06-01",
  "origin_country": "CN",
  "destination_country": "US",
  "hs_code": "8517.62",
  "quantity": 100,
  "declared_value_usd": 50000,
  "importer_id": "importer-123",
  "shipper_id": "shipper-456",
  "dwell_days": 5.5,
  "element9_is_mismatch": 1,
  "vessel_imo": "9234567"
}
EOF

# Test scoring
curl -X POST \
  http://localhost:8004/api/v1/scoring/cbp/manifest-test-001 \
  -H "Content-Type: application/json" \
  -d @test_entity.json

# Expected output (JSON):
# {
#   "entity_id": "manifest-test-001",
#   "risk_score": 65.2,
#   "confidence": 0.82,
#   "explanation": {...}
# }
```

**Checklist**:
- [ ] Endpoint responds: `____` (HTTP code)
- [ ] risk_score returned: `____` (should be 0-100)
- [ ] confidence returned: `____` (should be 0-1)
- [ ] explanation field present: [ ] YES [ ] NO
- [ ] Explanation includes top factors: [ ] YES [ ] NO

---

**Task 1.4: Test Caching**
```bash
# Call endpoint twice (should hit cache on second call)
curl -X POST http://localhost:8004/api/v1/scoring/cbp/manifest-test-001 -H "Content-Type: application/json" -d @test_entity.json

# Second call (should be faster)
time curl -X POST http://localhost:8004/api/v1/scoring/cbp/manifest-test-001 -H "Content-Type: application/json" -d @test_entity.json

# Check latency: should be <50ms on cache hit
```

**Checklist**:
- [ ] First call latency: `____` ms
- [ ] Second call latency: `____` ms (should be <50ms)
- [ ] Cache hit verified: [ ] YES [ ] NO

---

**Task 1.5: Test Other Endpoints**
```bash
# Test /health
curl http://localhost:8004/health

# Test /api/v1/rules/cbp
curl http://localhost:8004/api/v1/rules/cbp

# Test /api/v1/metrics/cbp
curl http://localhost:8004/api/v1/metrics/cbp

# Test /api/v1/feedback (submit analyst label)
curl -X POST \
  http://localhost:8004/api/v1/feedback/cbp/manifest-test-001 \
  -H "Content-Type: application/json" \
  -d '{"analyst_label": 1, "confidence": 0.9}'
```

**Checklist**:
- [ ] /health responds with status="healthy"
- [ ] /api/v1/rules/{domain} returns rule list
- [ ] /api/v1/metrics/{domain} returns AUC, precision, recall
- [ ] /api/v1/feedback/{domain}/{entity_id} accepts POST (201 or 200)

---

**Task 1.6: Run Unit Tests**
```bash
cd /home/rahulvadera/cbp-sentry/services/risk-engine

# Run pytest
pytest tests/ -v --tb=short

# Expected: All tests pass
```

**Checklist**:
- [ ] Unit tests run: `____` (number of tests)
- [ ] Passed: `____` [ ] All [ ] Some [ ] None
- [ ] Failed: `____` tests (should be 0)

---

## DAY 2 (FRIDAY, JUNE 14) - INFRASTRUCTURE & DATABASE

### Morning: PostgreSQL Schema Creation (2 hours)

**Task 2.1: Execute PostgreSQL Schema Script**

(Requires PostgreSQL access - if available, run):

```bash
# If PostgreSQL available locally
psql cbp_sentry -f /home/rahulvadera/cbp-sentry/schema/risk_scoring_schema.sql

# Verify schema created
psql cbp_sentry -c "
  SELECT table_name 
  FROM information_schema.tables 
  WHERE table_schema = 'risk_scoring' 
  ORDER BY table_name;
"

# Expected output:
# domains
# model_scores
# model_training_runs
# model_versions
# ... (10 tables)
```

**Checklist**:
- [ ] risk_scoring schema exists
- [ ] Tables created: `____` (should be 10+)
- [ ] CBP domain registered in domains table
- [ ] No errors during schema creation

---

**Task 2.2: Register Trained Models in Database**

```sql
-- SQL to register models (if PostgreSQL available)
INSERT INTO risk_scoring.model_versions (
  model_version_id, domain_id, model_type, model_path, 
  trained_at, auc, precision, recall, deployed
) VALUES
  ('cbp_xgb_v1', 'cbp', 'xgboost', 
   '/home/rahulvadera/cbp-sentry/models/xgboost_model.json',
   NOW(), 0.84, 0.35, 0.72, false),
  ('cbp_iforest_v1', 'cbp', 'isolation_forest',
   '/home/rahulvadera/cbp-sentry/models/isolation_forest.pkl',
   NOW(), NULL, NULL, NULL, false),
  ('cbp_shap_v1', 'cbp', 'shap_explainer',
   '/home/rahulvadera/cbp-sentry/models/shap_explainer.pkl',
   NOW(), NULL, NULL, NULL, false);

INSERT INTO risk_scoring.model_training_runs (
  domain_id, scorecard_version, xgboost_version, iforest_version,
  training_start, training_end, training_sample_size, 
  auc, precision, recall, f1_score, deployed
) VALUES (
  'cbp', 'cbp_v1', 'cbp_xgb_v1', 'cbp_iforest_v1',
  NOW() - INTERVAL '4 days', NOW() - INTERVAL '3 days',
  7200, 0.84, 0.35, 0.72, 0.48, false
);
```

**Checklist**:
- [ ] model_versions table updated: `____` models registered
- [ ] model_training_runs table updated: `____` training run inserted
- [ ] Queries successful (no errors)

---

### Afternoon: GCP Setup (2 hours)

**Task 2.3: Upload Models to GCP (if credentials available)**

```bash
# Authenticate with GCP
gcloud auth application-default login

# Create bucket (if not exists)
gsutil mb gs://cbp-sentry-models/ 2>/dev/null || echo "Bucket exists"

# Upload models
gsutil cp /home/rahulvadera/cbp-sentry/models/xgboost_model.json \
  gs://cbp-sentry-models/cbp/xgboost/v1/

gsutil cp /home/rahulvadera/cbp-sentry/models/isolation_forest.pkl \
  gs://cbp-sentry-models/cbp/isolation_forest/v1/

gsutil cp /home/rahulvadera/cbp-sentry/models/shap_explainer.pkl \
  gs://cbp-sentry-models/cbp/shap_explainer/v1/

# List uploaded files
gsutil ls gs://cbp-sentry-models/cbp/

# Verify files accessible
gsutil ls -lh gs://cbp-sentry-models/cbp/xgboost/v1/
```

**Checklist**:
- [ ] GCP authentication successful
- [ ] Bucket gs://cbp-sentry-models/ exists
- [ ] XGBoost model uploaded: `____` bytes
- [ ] Isolation Forest model uploaded: `____` bytes
- [ ] SHAP explainer uploaded: `____` bytes
- [ ] All files verified (no 404 errors)

---

## DAY 3 (SATURDAY, JUNE 15) - DOCKER BUILD & FINAL TESTS

### Morning: Docker Build (2 hours)

**Task 3.1: Build Docker Image**

```bash
cd /home/rahulvadera/cbp-sentry/services/risk-engine

# Build image
docker build -t cbp-sentry/risk-engine:v1 .

# Expected output:
# Step 1/N : FROM python:3.10-slim
# ...
# Successfully built [image-id]

# Verify image built
docker images | grep risk-engine

# Expected:
# cbp-sentry/risk-engine   v1    [image-id]    [timestamp]
```

**Checklist**:
- [ ] Dockerfile builds without errors
- [ ] Image created: `cbp-sentry/risk-engine:v1`
- [ ] Image size: `____` MB
- [ ] No security warnings

---

**Task 3.2: Test Docker Image Locally**

```bash
# Start container
docker run -d \
  -p 8004:8004 \
  --name risk-engine \
  -e FLASK_ENV=development \
  cbp-sentry/risk-engine:v1

# Wait for startup
sleep 3

# Test health check
curl http://localhost:8004/health

# Test scoring
curl -X POST \
  http://localhost:8004/api/v1/scoring/cbp/manifest-test-001 \
  -H "Content-Type: application/json" \
  -d '{"origin_country":"CN", "destination_country":"US", "dwell_days": 5.5}'

# View logs
docker logs risk-engine

# Stop container
docker stop risk-engine
docker rm risk-engine
```

**Checklist**:
- [ ] Container starts without errors
- [ ] Health check responds (HTTP 200)
- [ ] Scoring endpoint works
- [ ] Logs show no errors
- [ ] Container stops cleanly

---

**Task 3.3: Push to Container Registry (if GCP available)**

```bash
# Tag image for GCP
docker tag cbp-sentry/risk-engine:v1 gcr.io/[YOUR-GCP-PROJECT]/risk-engine:v1

# Push to Google Container Registry
docker push gcr.io/[YOUR-GCP-PROJECT]/risk-engine:v1

# Verify image in registry
gcloud container images list --repository=gcr.io/[YOUR-GCP-PROJECT] | grep risk-engine
```

**Checklist**:
- [ ] Image tagged for GCP
- [ ] Image pushed to registry
- [ ] Image visible in GCP console
- [ ] Image digest recorded: `____`

---

### Afternoon: Week 4 Decision Gate (1 hour)

**Task 3.4: Decision Gate - GO or NO-GO**

**Verification Checklist**:

- [ ] **Model Quality**: AUC ≥ 0.82 → [ ] PASS [ ] FAIL
- [ ] **API Testing**: All 4 endpoints responding → [ ] PASS [ ] FAIL
- [ ] **Caching**: Redis/cache working → [ ] PASS [ ] FAIL  [ ] N/A
- [ ] **Docker Build**: Image builds and runs → [ ] PASS [ ] FAIL
- [ ] **Database**: PostgreSQL schema + models registered → [ ] PASS [ ] FAIL  [ ] N/A
- [ ] **Performance**: P95 latency <200ms → [ ] PASS [ ] FAIL  [ ] N/A

**Decision**:
```
If all critical items (marked with *) = PASS:
  ✅ GO TO PHASE 2 (Integration with CBP Sentry)
  
If 1-2 items = FAIL:
  ⚠️ REMEDIATE (2-3 days) then reassess
  
If 3+ items = FAIL:
  ❌ ESCALATE to stakeholders
```

**Checklist**:
- [ ] Decision made: [ ] GO [ ] NO-GO [ ] REMEDIATE
- [ ] Stakeholders notified
- [ ] Phase 2 kickoff scheduled (if GO)

---

## RUNNING TOTAL

| Task | Owner | Est. Time | Status |
|------|-------|-----------|--------|
| Model Performance Validation | ML Eng | 2h | ⏳ TODAY |
| Flask Local Testing | Backend | 3h | ⏳ TODAY |
| PostgreSQL Schema | DevOps | 2h | ⏳ TOMORROW |
| GCP Upload | DevOps | 2h | ⏳ TOMORROW |
| Docker Build | DevOps | 2h | ⏳ SATURDAY |
| Decision Gate | Tech Lead | 1h | ⏳ SATURDAY |
| **TOTAL** | | **12h** | |

---

## SUCCESS CRITERIA

### ✅ Phase 1 Complete When:
1. XGBoost AUC ≥ 0.82 (verified)
2. All 4 API endpoints responding (verified)
3. Docker image builds and runs (verified)
4. Models registered in database (verified or N/A)
5. Team agrees to proceed to Phase 2

### 🎯 Phase 2 Ready When:
- Precise Risk Engine API deployed and stable
- Feature flag added to CBP Sentry API
- V2AITuningPage domain selector added
- Integration tests written

---

## ESCALATION CONTACTS

If blockers appear:
- **Model Quality**: Contact ML Engineer
- **API Issues**: Contact Backend Engineer
- **Infrastructure**: Contact DevOps
- **Approval**: Contact Tech Lead / Stakeholders

---

**Timeline**: June 13-15, 2026  
**Status**: Ready to execute  
**Last Updated**: June 12, 2026

---

**🚀 Ready to start Week 4? Let's execute!**
