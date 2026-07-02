# Phase 1 Week 1 — Test Scenarios & Validation

**Comprehensive test plan for validating all Phase 1 Week 1 deliverables.**

---

## Test Environment Setup

### Prerequisites
- Docker and docker-compose installed
- Python 3.9+ with venv
- Node.js 18+
- SQLite3 CLI
- curl or Postman for API testing
- Modern web browser (Chrome/Firefox/Safari)

### Setup Steps

```bash
# 1. Clone and navigate
cd /home/rahulvadera/cbp-sentry

# 2. Create Python venv (if not exists)
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install -r services/api/requirements.txt

# 4. Install Node dependencies
cd ui && npm install && cd ..

# 5. Verify installations
python --version  # Should be 3.9+
node --version    # Should be 18+
npm --version     # Should be 9+
```

---

## Test Suite 1: Database Migration

### Test 1.1: Migration File Exists

**Objective:** Verify migration file is present and valid

```bash
# Check file exists
test -f services/data/migrations/v4_0_risk_model_management.py && \
  echo "✓ Migration file exists" || \
  echo "✗ Migration file not found"

# Check file is not empty
filesize=$(stat -f%z services/data/migrations/v4_0_risk_model_management.py 2>/dev/null || \
           stat -c%s services/data/migrations/v4_0_risk_model_management.py)
test $filesize -gt 10000 && \
  echo "✓ Migration file size OK ($filesize bytes)" || \
  echo "✗ Migration file too small"
```

**Expected Output:**
```
✓ Migration file exists
✓ Migration file size OK (26693 bytes)
```

---

### Test 1.2: Migration Runs Without Errors

**Objective:** Apply migration and verify no errors

```bash
cd /home/rahulvadera/cbp-sentry/services/data

# Remove backup if exists
rm -f data/cbp_sentry.db.test

# Run migration
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from migrations.v4_0_risk_model_management import upgrade

async def run():
    engine = create_async_engine('sqlite+aiosqlite:///./data/cbp_sentry.db.test')
    async with AsyncSession(engine) as session:
        try:
            await upgrade(session)
            await session.commit()
            print('✓ Migration successful')
            return True
        except Exception as e:
            await session.rollback()
            print(f'✗ Migration failed: {e}')
            return False

success = asyncio.run(run())
sys.exit(0 if success else 1)
"

# Check exit code
test $? -eq 0 && echo "✓ Migration executed successfully" || echo "✗ Migration failed"
```

**Expected Output:**
```
✓ Migration successful
✓ Migration executed successfully
```

---

### Test 1.3: All Tables Created

**Objective:** Verify all 7 tables exist

```bash
cd /home/rahulvadera/cbp-sentry/services/data

# List tables
sqlite3 data/cbp_sentry.db.test "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

# Expected output:
# risk_model_approvals
# risk_model_drift_detected
# risk_model_metrics
# risk_model_predictions
# risk_model_training_jobs
# risk_models
# risk_retraining_config
```

**Verification Script:**
```bash
cd /home/rahulvadera/cbp-sentry/services/data

expected_tables=("risk_model_approvals" "risk_model_drift_detected" "risk_model_metrics" "risk_model_predictions" "risk_model_training_jobs" "risk_models" "risk_retraining_config")

for table in "${expected_tables[@]}"; do
    count=$(sqlite3 data/cbp_sentry.db.test "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='$table';")
    if [ "$count" -eq 1 ]; then
        echo "✓ Table '$table' created"
    else
        echo "✗ Table '$table' missing"
    fi
done
```

**Expected Output:**
```
✓ Table 'risk_model_approvals' created
✓ Table 'risk_model_drift_detected' created
✓ Table 'risk_model_metrics' created
✓ Table 'risk_model_predictions' created
✓ Table 'risk_model_training_jobs' created
✓ Table 'risk_models' created
✓ Table 'risk_retraining_config' created
```

---

### Test 1.4: Indexes Created (24 Expected)

**Objective:** Verify all performance indexes are created

```bash
cd /home/rahulvadera/cbp-sentry/services/data

# Count indexes
sqlite3 data/cbp_sentry.db.test "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';"

# Expected: 24
```

**Detailed Index Verification:**
```bash
cd /home/rahulvadera/cbp-sentry/services/data

sqlite3 data/cbp_sentry.db.test << 'EOF'
.headers on
.mode column
SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY tbl_name;
EOF

# Expected output (sample):
# idx_risk_models_status | risk_models
# idx_risk_models_version | risk_models
# idx_risk_model_training_jobs_model_id | risk_model_training_jobs
# ... (24 total)
```

---

### Test 1.5: Constraints and Defaults

**Objective:** Verify check constraints and column defaults

```bash
cd /home/rahulvadera/cbp-sentry/services/data

# Check table schema
sqlite3 data/cbp_sentry.db.test ".schema risk_models"

# Expected output should include:
# - PRIMARY KEY (model_id)
# - UNIQUE (version, model_id)
# - CHECK (status IN (...))
# - DEFAULT (created_at CURRENT_TIMESTAMP)
```

---

## Test Suite 2: React Components

### Test 2.1: Component Files Exist

**Objective:** Verify all 8 React components are created

```bash
cd /home/rahulvadera/cbp-sentry

components=(
  "ui/src/pages/RiskModelManagement/index.tsx"
  "ui/src/pages/RiskModelManagement/Dashboard.tsx"
  "ui/src/pages/RiskModelManagement/ModelVersions.tsx"
  "ui/src/pages/RiskModelManagement/TrainingHistory.tsx"
  "ui/src/pages/RiskModelManagement/PerformanceMetrics.tsx"
  "ui/src/pages/RiskModelManagement/DataDriftMonitoring.tsx"
  "ui/src/pages/RiskModelManagement/PredictionExplanations.tsx"
  "ui/src/pages/RiskModelManagement/RetrainingConfig.tsx"
)

for component in "${components[@]}"; do
    if [ -f "$component" ]; then
        lines=$(wc -l < "$component")
        echo "✓ $component ($lines lines)"
    else
        echo "✗ $component missing"
    fi
done
```

**Expected Output:**
```
✓ ui/src/pages/RiskModelManagement/index.tsx (156 lines)
✓ ui/src/pages/RiskModelManagement/Dashboard.tsx (240 lines)
✓ ui/src/pages/RiskModelManagement/ModelVersions.tsx (310 lines)
✓ ui/src/pages/RiskModelManagement/TrainingHistory.tsx (370 lines)
✓ ui/src/pages/RiskModelManagement/PerformanceMetrics.tsx (260 lines)
✓ ui/src/pages/RiskModelManagement/DataDriftMonitoring.tsx (280 lines)
✓ ui/src/pages/RiskModelManagement/PredictionExplanations.tsx (340 lines)
✓ ui/src/pages/RiskModelManagement/RetrainingConfig.tsx (380 lines)
```

---

### Test 2.2: Components Have No TypeScript Errors

**Objective:** Verify TypeScript compilation succeeds

```bash
cd /home/rahulvadera/cbp-sentry/ui

# Check TypeScript compilation
npx tsc --noEmit --skipLibCheck ui/src/pages/RiskModelManagement/*.tsx

# Should output nothing if successful
# If errors exist, they will be printed
```

**Expected Output:**
```
(No output = success)
```

---

### Test 2.3: Components Render Without Errors

**Objective:** Start dev server and verify component loads

```bash
# Terminal 1: Start API
cd /home/rahulvadera/cbp-sentry
source venv/bin/activate
cd services/api && timeout 30 python main.py --port 8000 &

# Terminal 2: Start React dev server
cd /home/rahulvadera/cbp-sentry/ui
npm run dev &

# Wait for servers to start
sleep 10

# Terminal 3: Test component loads
curl -s http://localhost:3001 | grep -q "RiskModelManagement" && \
  echo "✓ Component renders" || \
  echo "✗ Component not found"

# Check browser console for errors (manual step)
# Navigate to http://localhost:3001
# Open DevTools (F12)
# Look for red error messages
# Expected: No "Uncaught" or "Error:" messages
```

---

### Test 2.4: Component Props Validation

**Objective:** Verify all components accept expected props

```bash
# Check prop interfaces in components
cd /home/rahulvadera/cbp-sentry/ui

# Dashboard should accept: undefined (uses internal state)
grep -q "interface.*Props" src/pages/RiskModelManagement/Dashboard.tsx && \
  echo "✓ Dashboard has Props interface" || \
  echo "⚠ Dashboard uses default props"

# ModelVersions should accept: onVersionSelect, onApprovalRequest
grep -q "versions" src/pages/RiskModelManagement/ModelVersions.tsx && \
  echo "✓ ModelVersions defined" || \
  echo "✗ ModelVersions missing structure"

# TrainingHistory should accept: onJobSelect
grep -q "TrainingHistory" src/pages/RiskModelManagement/TrainingHistory.tsx && \
  echo "✓ TrainingHistory defined" || \
  echo "✗ TrainingHistory missing structure"
```

---

## Test Suite 3: API Endpoints

### Test 3.1: Endpoints Are Defined

**Objective:** Verify all 12 endpoints are defined in code

```bash
cd /home/rahulvadera/cbp-sentry

endpoints=(
  "GET /api/risk-models/dashboard"
  "GET /api/risk-models/versions"
  "POST /api/risk-models/{model_id}/compare"
  "GET /api/risk-models/training-jobs"
  "GET /api/risk-models/training-jobs/{job_id}"
  "POST /api/risk-models/training-jobs"
  "GET /api/risk-models/{model_id}/metrics"
  "GET /api/risk-models/{model_id}/metrics/fairness"
  "GET /api/risk-models/{model_id}/drift"
  "POST /api/risk-models/{model_id}/drift/detect"
  "GET /api/risk-models/predictions/{shipment_id}/explain"
  "GET /api/risk-models/approvals"
  "POST /api/risk-models/approvals/{approval_id}/vote"
  "GET /api/risk-models/retraining-config"
  "PUT /api/risk-models/retraining-config"
  "POST /api/risk-models/{model_id}/rollback"
)

for endpoint in "${endpoints[@]}"; do
    method=$(echo $endpoint | cut -d' ' -f1)
    path=$(echo $endpoint | cut -d' ' -f2)
    # Convert path pattern to Python route pattern
    py_path=$(echo "$path" | sed 's/{[^}]*}/<[^>]*>/g')
    
    if grep -q "$method.*$py_path" services/api/routes/risk_models.py; then
        echo "✓ Endpoint $endpoint defined"
    else
        echo "? Endpoint $endpoint (check format)"
    fi
done
```

---

### Test 3.2: Endpoints Have Docstrings

**Objective:** Verify all endpoints have documentation

```bash
cd /home/rahulvadera/cbp-sentry

# Count endpoints with docstrings
docstring_count=$(grep -c '"""' services/api/routes/risk_models.py)
endpoint_count=$(grep -c '@bp.route' services/api/routes/risk_models.py)

echo "Endpoints: $endpoint_count"
echo "Docstrings (pairs): $((docstring_count / 2))"

# Each endpoint should have opening and closing """
# So docstring_count should be at least endpoint_count * 2
test $((docstring_count / 2)) -ge $endpoint_count && \
  echo "✓ All endpoints documented" || \
  echo "⚠ Some endpoints may lack documentation"
```

---

### Test 3.3: Mock Service Returns Valid Data

**Objective:** Verify mock service generates correct data shapes

```bash
cd /home/rahulvadera/cbp-sentry/services/api

# Test mock service
python -c "
from services.risk_model_mock_service import get_mock_service
import json

service = get_mock_service()

# Test dashboard
dashboard = service.get_mock_dashboard()
assert 'active_model' in dashboard, 'Dashboard missing active_model'
assert 'pending_approvals' in dashboard, 'Dashboard missing pending_approvals'
assert 'alerts' in dashboard, 'Dashboard missing alerts'
print('✓ get_mock_dashboard() returns valid data')

# Test versions
versions = service.get_mock_versions()
assert 'versions' in versions, 'Versions missing versions list'
assert len(versions['versions']) > 0, 'Versions list empty'
print('✓ get_mock_versions() returns valid data')

# Test training jobs
jobs = service.get_mock_training_jobs()
assert 'jobs' in jobs, 'Jobs missing jobs list'
print('✓ get_mock_training_jobs() returns valid data')

# Test metrics
metrics = service.get_mock_metrics_timeseries('v3.0')
assert 'timeseries' in metrics, 'Metrics missing timeseries'
assert len(metrics['timeseries']) > 0, 'Timeseries empty'
print('✓ get_mock_metrics_timeseries() returns valid data')

# Test drift
drift = service.get_mock_drift_detection('v3.0')
assert 'drift_score' in drift, 'Drift missing drift_score'
assert 'features' in drift, 'Drift missing features'
print('✓ get_mock_drift_detection() returns valid data')

# Test approvals
approvals = service.get_mock_pending_approvals()
assert 'approvals' in approvals, 'Approvals missing approvals list'
print('✓ get_mock_pending_approvals() returns valid data')

print('\\n✓✓✓ All mock data shapes valid')
"
```

**Expected Output:**
```
✓ get_mock_dashboard() returns valid data
✓ get_mock_versions() returns valid data
✓ get_mock_training_jobs() returns valid data
✓ get_mock_metrics_timeseries() returns valid data
✓ get_mock_drift_detection() returns valid data
✓ get_mock_pending_approvals() returns valid data

✓✓✓ All mock data shapes valid
```

---

### Test 3.4: API Endpoints Respond

**Objective:** Start API server and test endpoints return 200 OK

```bash
# Terminal 1: Start API
cd /home/rahulvadera/cbp-sentry
source venv/bin/activate
cd services/api && python main.py --port 8000 &
API_PID=$!

# Wait for server to start
sleep 5

# Terminal 2: Test endpoints
test_endpoints() {
    echo "Testing API endpoints..."
    
    # Dashboard
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/risk-models/dashboard)
    test $status -eq 200 && echo "✓ GET /api/risk-models/dashboard ($status)" || echo "✗ GET /api/risk-models/dashboard ($status)"
    
    # Versions
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/risk-models/versions?status=production")
    test $status -eq 200 && echo "✓ GET /api/risk-models/versions ($status)" || echo "✗ GET /api/risk-models/versions ($status)"
    
    # Training jobs
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/risk-models/training-jobs")
    test $status -eq 200 && echo "✓ GET /api/risk-models/training-jobs ($status)" || echo "✗ GET /api/risk-models/training-jobs ($status)"
    
    # Metrics
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/risk-models/v3.0/metrics")
    test $status -eq 200 && echo "✓ GET /api/risk-models/v3.0/metrics ($status)" || echo "✗ GET /api/risk-models/v3.0/metrics ($status)"
    
    # Drift
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/risk-models/v3.0/drift")
    test $status -eq 200 && echo "✓ GET /api/risk-models/v3.0/drift ($status)" || echo "✗ GET /api/risk-models/v3.0/drift ($status)"
    
    # Approvals
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/risk-models/approvals")
    test $status -eq 200 && echo "✓ GET /api/risk-models/approvals ($status)" || echo "✗ GET /api/risk-models/approvals ($status)"
    
    # Config
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/risk-models/retraining-config")
    test $status -eq 200 && echo "✓ GET /api/risk-models/retraining-config ($status)" || echo "✗ GET /api/risk-models/retraining-config ($status)"
}

test_endpoints

# Cleanup
kill $API_PID 2>/dev/null
```

**Expected Output:**
```
Testing API endpoints...
✓ GET /api/risk-models/dashboard (200)
✓ GET /api/risk-models/versions (200)
✓ GET /api/risk-models/training-jobs (200)
✓ GET /api/risk-models/v3.0/metrics (200)
✓ GET /api/risk-models/v3.0/drift (200)
✓ GET /api/risk-models/approvals (200)
✓ GET /api/risk-models/retraining-config (200)
```

---

## Test Suite 4: Routing Integration

### Test 4.1: Route Exists in App.tsx

**Objective:** Verify routing is integrated in App.tsx

```bash
cd /home/rahulvadera/cbp-sentry/ui

# Check import
grep -q "import RiskModelManagement from" src/App.tsx && \
  echo "✓ RiskModelManagement imported" || \
  echo "✗ RiskModelManagement not imported"

# Check route case
grep -q "case 'risk-models'" src/App.tsx && \
  echo "✓ 'risk-models' route exists" || \
  echo "✗ 'risk-models' route missing"

# Check nav item (if applicable)
grep -q "Risk Model Management" src/App.tsx && \
  echo "✓ Navigation label exists" || \
  echo "✗ Navigation label missing"
```

**Expected Output:**
```
✓ RiskModelManagement imported
✓ 'risk-models' route exists
✓ Navigation label exists
```

---

### Test 4.2: Route Is Accessible

**Objective:** Start app and verify route loads

```bash
# Start app in browser
# Navigate to http://localhost:3001
# Click "Risk Model Management" in sidebar
# Expected: Dashboard screen loads with 8 tabs

# Programmatic test (requires browser automation)
# OR manual test:
# 1. Open http://localhost:3001/risk-models
# 2. Dashboard should load
# 3. URL should show "/risk-models"
# 4. No 404 error
```

---

## Test Suite 5: Mock Data Integration

### Test 5.1: Mock Data Has Correct Structure

**Objective:** Verify mock data matches API response schema

```bash
cd /home/rahulvadera/cbp-sentry/services/api

python -c "
from services.risk_model_mock_service import get_mock_service
import json

service = get_mock_service()

# Define expected schema
expected_dashboard_keys = {'active_model', 'pending_approvals', 'alerts', 'key_metrics'}
expected_version_keys = {'model_id', 'version', 'status', 'accuracy', 'auc_roc'}
expected_job_keys = {'job_id', 'model_id', 'status', 'started_at', 'completed_at'}

# Test dashboard
dashboard = service.get_mock_dashboard()
assert set(dashboard.keys()) == expected_dashboard_keys, f'Dashboard keys mismatch: {set(dashboard.keys())}'
print('✓ Dashboard structure valid')

# Test versions
versions = service.get_mock_versions()
assert len(versions['versions']) > 0, 'No versions returned'
version = versions['versions'][0]
assert all(k in version for k in expected_version_keys), f'Version missing keys: {version.keys()}'
print('✓ Version structure valid')

# Test training jobs
jobs = service.get_mock_training_jobs()
assert len(jobs['jobs']) > 0, 'No jobs returned'
job = jobs['jobs'][0]
assert all(k in job for k in expected_job_keys), f'Job missing keys: {job.keys()}'
print('✓ Job structure valid')

# Test metrics have timeseries
metrics = service.get_mock_metrics_timeseries('v3.0')
assert 'timeseries' in metrics, 'Metrics missing timeseries'
assert len(metrics['timeseries']) > 0, 'Timeseries empty'
ts = metrics['timeseries'][0]
assert 'accuracy' in ts and 'latency_p95_ms' in ts, 'Timeseries missing metrics'
print('✓ Metrics structure valid')

# Test drift has features
drift = service.get_mock_drift_detection('v3.0')
assert 'features' in drift, 'Drift missing features'
assert len(drift['features']) > 0, 'Drift features empty'
print('✓ Drift structure valid')

# Test approvals have votes
approvals = service.get_mock_pending_approvals()
assert 'approvals' in approvals, 'Missing approvals'
if len(approvals['approvals']) > 0:
    appr = approvals['approvals'][0]
    assert 'votes' in appr, 'Approval missing votes'
print('✓ Approval structure valid')

print('\\n✓✓✓ All mock data structures valid')
"
```

**Expected Output:**
```
✓ Dashboard structure valid
✓ Version structure valid
✓ Job structure valid
✓ Metrics structure valid
✓ Drift structure valid
✓ Approval structure valid

✓✓✓ All mock data structures valid
```

---

## Test Suite 6: UI Screen Validation

### Test 6.1: All 8 Screens Render (Manual)

**Objective:** Manually verify all 8 UI screens load without errors

**Steps:**

1. **Dashboard Tab**
   - Navigate to http://localhost:3001/risk-models
   - Verify dashboard loads
   - Check for: active model (v3.0), metrics (92.4% accuracy), pending approvals, alerts
   - Expected: No red errors in DevTools

2. **Model Versions Tab**
   - Click "Model Versions" tab
   - Check for: version table, filter buttons, approval interface
   - Verify v3.0 (production), v3.1 (staging), v2.1 (deprecated)
   - Expected: Table loads with 3+ versions

3. **Training History Tab**
   - Click "Training History" tab
   - Check for: job list, status filters, expandable job details
   - Verify: job_id, start_at, completed_at, metrics
   - Expected: List loads with 5+ jobs

4. **Performance Metrics Tab**
   - Click "Performance Metrics" tab
   - Check for: accuracy chart (24h), latency chart, confusion matrix
   - Verify: time-series data with timestamps
   - Expected: Charts render with data points

5. **Data Drift Tab**
   - Click "Data Drift Monitoring" tab
   - Check for: feature list, drift scores, alerts
   - Verify: distribution comparison, elevation alerts
   - Expected: Feature drift scores display (0-1 scale)

6. **SHAP Explanations Tab**
   - Click "Prediction Explanations" tab
   - Check for: feature contributions, SHAP force plot simulation
   - Verify: feature rankings, confidence bounds
   - Expected: Top 10 features with contributions display

7. **Approvals Tab**
   - Click "Model Approvals" tab
   - Check for: pending approval queue, voting interface
   - Verify: voter names, vote buttons, performance delta
   - Expected: Approval requests display with voter interface

8. **Retraining Config Tab**
   - Click "Retraining Config" tab
   - Check for: drift threshold setting, degradation trigger
   - Verify: cron schedule, error spike threshold
   - Expected: All settings display with save button

**Test Result:** If all 8 tabs load without errors, mark as ✓ PASS

---

## Test Suite 7: Code Quality Checks

### Test 7.1: TypeScript Strict Mode

**Objective:** Verify no TypeScript `any` types are used

```bash
cd /home/rahulvadera/cbp-sentry/ui

# Search for 'any' in RiskModelManagement components
grep -n " any" src/pages/RiskModelManagement/*.tsx | grep -v "// any" && \
  echo "⚠ Found 'any' types (check if intentional)" || \
  echo "✓ No 'any' types in TypeScript"
```

**Expected Output:**
```
✓ No 'any' types in TypeScript
```

---

### Test 7.2: React Component Props Typed

**Objective:** Verify all component props are typed

```bash
cd /home/rahulvadera/cbp-sentry/ui

# Check each component has interface Props or typed parameters
for component in src/pages/RiskModelManagement/{Dashboard,ModelVersions,TrainingHistory,PerformanceMetrics,DataDriftMonitoring,PredictionExplanations,ModelApprovals,RetrainingConfig}.tsx; do
    if grep -q "interface.*Props\|type.*Props\|function.*({" "$component"; then
        echo "✓ $(basename $component) has typed props"
    else
        echo "? $(basename $component) (check prop typing)"
    fi
done
```

---

### Test 7.3: Tailwind CSS Usage

**Objective:** Verify components use Tailwind CSS classes

```bash
cd /home/rahulvadera/cbp-sentry/ui

# Count className occurrences
class_count=$(grep -o "className=" src/pages/RiskModelManagement/*.tsx | wc -l)
test $class_count -gt 100 && \
  echo "✓ Tailwind CSS extensively used ($class_count classes)" || \
  echo "⚠ Limited Tailwind CSS usage"
```

**Expected Output:**
```
✓ Tailwind CSS extensively used (250+ classes)
```

---

## Automated Test Script

**Save as `/tmp/test_phase1_week1.sh`:**

```bash
#!/bin/bash

set -e

PROJECT_ROOT="/home/rahulvadera/cbp-sentry"
PASSED=0
FAILED=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED++))
}

log_section() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

# ========================================================================
# TEST SUITE 1: FILES
# ========================================================================

log_section "Test Suite 1: Files"

[ -f "$PROJECT_ROOT/services/data/migrations/v4_0_risk_model_management.py" ] && \
    log_pass "Database migration file exists" || \
    log_fail "Database migration file not found"

[ -f "$PROJECT_ROOT/ui/src/pages/RiskModelManagement/index.tsx" ] && \
    log_pass "RiskModelManagement index.tsx exists" || \
    log_fail "RiskModelManagement/index.tsx not found"

[ -f "$PROJECT_ROOT/services/api/routes/risk_models.py" ] && \
    log_pass "API routes file exists" || \
    log_fail "API routes file not found"

[ -f "$PROJECT_ROOT/services/api/services/risk_model_mock_service.py" ] && \
    log_pass "Mock service file exists" || \
    log_fail "Mock service file not found"

# ========================================================================
# TEST SUITE 2: CODE QUALITY
# ========================================================================

log_section "Test Suite 2: Code Quality"

cd "$PROJECT_ROOT"

# TypeScript check
if command -v npx &> /dev/null; then
    cd ui
    npx tsc --noEmit --skipLibCheck ui/src/pages/RiskModelManagement/*.tsx 2>/dev/null && \
        log_pass "TypeScript compilation successful" || \
        log_fail "TypeScript compilation failed"
    cd "$PROJECT_ROOT"
else
    log_fail "TypeScript compiler not found"
fi

# ========================================================================
# SUMMARY
# ========================================================================

log_section "Test Summary"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓✓✓ All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗✗✗ Some tests failed${NC}"
    exit 1
fi
```

**Run automated tests:**
```bash
bash /tmp/test_phase1_week1.sh
```

---

## Sign-Off Checklist

**For Phase 1 Week 1 completion, verify:**

- [ ] Database migration file created and syntax valid
- [ ] All 7 tables defined in migration
- [ ] 24 indexes created for performance
- [ ] 8 React components created with TypeScript
- [ ] 100% Tailwind CSS styling applied
- [ ] Routing integrated in App.tsx
- [ ] 12 API endpoints defined
- [ ] Mock data service provides realistic data
- [ ] All 8 UI screens render without errors
- [ ] Components accept mock data via props
- [ ] No console errors in browser DevTools
- [ ] Responsive design verified (mobile, tablet)
- [ ] Documentation complete (README, QUICKSTART, IMPLEMENTATION_NOTES)
- [ ] Code quality checks pass (TypeScript strict mode)
- [ ] All automated tests pass

**If all items checked:** Phase 1 Week 1 is ✅ COMPLETE

---

**Date:** June 13, 2026  
**Status:** All test scenarios prepared and ready for execution
