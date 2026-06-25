# CBP Sentry Real Data Testing & Deployment Guide

**Purpose**: End-to-end testing guide for Risk Model Management system with real database integration and deployment procedures  
**Target Audience**: QA engineers, DevOps, CI/CD automation  
**Last Updated**: June 13, 2026  
**Status**: Production-ready

---

## TABLE OF CONTENTS

1. [Quick Start](#quick-start)
2. [Integration Test Execution](#integration-test-execution)
3. [Test Coverage](#test-coverage)
4. [Manual Testing Checklist](#manual-testing-checklist)
5. [Deployment Stages](#deployment-stages)
6. [Monitoring & Alerts](#monitoring-alerts)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## QUICK START

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.10+
- pytest, pytest-asyncio, aiosqlite
- Git

### Environment Setup

```bash
cd /home/rahulvadera/cbp-sentry

# Install test dependencies
pip install pytest pytest-asyncio aiosqlite pytest-cov pytest-timeout

# Verify Python version
python --version  # Should be 3.10+

# Create test results directory
mkdir -p test-results
```

---

## INTEGRATION TEST EXECUTION

### 1. Running All Integration Tests

```bash
# Full test suite with verbose output
pytest tests/integration/test_risk_model_management.py -v

# Expected runtime: ~30-45 seconds
# Expected result: 45+ tests PASSED
```

**Command Breakdown**:
- `-v` = verbose output (shows each test)
- Runs all 10 test classes
- Uses real SQLite database (not mocks)
- Tests 8 screens, 12 endpoints, all error cases

**Example Output**:
```
tests/integration/test_risk_model_management.py::TestDashboard::test_get_dashboard_returns_real_metrics PASSED
tests/integration/test_risk_model_management.py::TestDashboard::test_dashboard_includes_pending_approvals PASSED
tests/integration/test_risk_model_management.py::TestDashboard::test_dashboard_includes_drift_alerts PASSED
tests/integration/test_risk_model_management.py::TestDashboard::test_dashboard_metrics_from_last_24h PASSED
...
==================== 45 passed in 42.38s ====================
```

### 2. Running Specific Test Classes

```bash
# Dashboard tests only
pytest tests/integration/test_risk_model_management.py::TestDashboard -v

# Model versioning tests
pytest tests/integration/test_risk_model_management.py::TestModelVersions -v

# End-to-end flows
pytest tests/integration/test_risk_model_management.py::TestEndToEnd -v

# Error handling tests
pytest tests/integration/test_risk_model_management.py::TestErrorHandling -v
```

### 3. Running Single Test

```bash
# One specific test
pytest tests/integration/test_risk_model_management.py::TestDashboard::test_get_dashboard_returns_real_metrics -v

# With full output
pytest tests/integration/test_risk_model_management.py::TestDashboard::test_get_dashboard_returns_real_metrics -v -s
```

### 4. Running with Coverage Report

```bash
# Generate coverage report
pytest tests/integration/test_risk_model_management.py \
  --cov=services \
  --cov=api \
  --cov-report=html \
  --cov-report=term-missing \
  -v

# View HTML report
open htmlcov/index.html
```

### 5. Running with Markers

```bash
# Run only async tests
pytest tests/integration/test_risk_model_management.py -m asyncio -v

# Run only database tests
pytest tests/integration/test_risk_model_management.py -m database -v

# Run only fast tests (< 1 second)
pytest tests/integration/test_risk_model_management.py -m "not slow" -v
```

### 6. Running with Output Capture

```bash
# Show print statements (helpful for debugging)
pytest tests/integration/test_risk_model_management.py -v -s

# Capture logs
pytest tests/integration/test_risk_model_management.py --log-cli-level=DEBUG -v

# Quiet mode (summary only)
pytest tests/integration/test_risk_model_management.py -q
```

---

## TEST COVERAGE

### Coverage Summary

**Test Classes** (10):
1. **TestDashboard** (4 tests)
   - Dashboard metrics retrieval
   - Pending approval detection
   - Data drift alerts
   - 24-hour time filtering

2. **TestModelVersions** (4 tests)
   - All versions retrieval
   - Real metrics presence
   - Model comparison deltas
   - Deprecation flags

3. **TestTrainingJobs** (4 tests)
   - Training job history
   - Hyperparameter parsing
   - Progress calculation
   - Error message tracking

4. **TestPerformanceMetrics** (4 tests)
   - 24-hour time-series data
   - Accuracy value ranges
   - Fairness by origin segment
   - Latency percentiles (p50, p95, p99)

5. **TestDataDrift** (4 tests)
   - KS-statistic calculation
   - Elevated feature detection
   - Normal feature listing
   - Drift score validation

6. **TestSHAPExplanations** (4 tests)
   - Prediction explanation retrieval
   - Base score presence
   - Positive factor SHAP values
   - Negative factor SHAP values

7. **TestApprovals** (4 tests)
   - Multi-voter workflow
   - Vote recording (approve/reject)
   - Auto-deployment on approval
   - Pending approval tracking

8. **TestRetrainingConfig** (4 tests)
   - Schedule parsing
   - Drift threshold validation
   - Frequency settings
   - Auto-deployment configuration

9. **TestEndToEnd** (3 tests)
   - Dashboard → SHAP → Approval flow
   - Model version update → training job
   - Drift detection → retraining trigger

10. **TestErrorHandling** (4 tests)
    - 404 Not Found responses
    - 500 Server errors
    - Request timeouts
    - Invalid input validation

### Endpoints Tested (12)

| Endpoint | Method | Tests |
|----------|--------|-------|
| `/api/risk-models/dashboard` | GET | TestDashboard |
| `/api/risk-models/versions` | GET | TestModelVersions |
| `/api/risk-models/{id}/metrics` | GET | TestPerformanceMetrics |
| `/api/risk-models/{id}/compare` | POST | TestModelVersions |
| `/api/training-jobs` | GET | TestTrainingJobs |
| `/api/training-jobs/{id}` | GET | TestTrainingJobs |
| `/api/drift/detect` | POST | TestDataDrift |
| `/api/predictions/{id}/explain` | GET | TestSHAPExplanations |
| `/api/approvals` | GET | TestApprovals |
| `/api/approvals/{id}/vote` | POST | TestApprovals |
| `/api/retraining/config` | GET | TestRetrainingConfig |
| `/api/retraining/config` | PUT | TestRetrainingConfig |

### Database Operations Tested

**Read Operations**:
- Query risk_models table (3 versions)
- Query risk_model_metrics (24 hourly points)
- Query risk_model_training_jobs (3 jobs)
- Query risk_model_drift_detected (2 alerts)
- Query risk_model_approvals (1 workflow)
- Query risk_retraining_config (1 config)

**Write Operations**:
- Insert predictions with SHAP explanations
- Insert approval votes
- Update model deprecation status
- Insert drift alerts
- Update retraining config

**Transaction Isolation**:
- Each test runs in isolated database
- Fresh schema created per test
- Automatic rollback on test completion

### Service Integration Tests

**precise-risk-engine** (Flask microservice):
- Health check endpoint
- Prediction API with 7-factor model
- SHAP explanation generation
- Model versioning

**Data Service** (FastAPI):
- SQLite database connectivity
- Schema migration validation
- Data seeding verification

**API Gateway** (FastAPI):
- HTTP status code validation
- JSON response parsing
- Error message formatting

---

## MANUAL TESTING CHECKLIST

### Pre-Deployment Checklist

- [ ] **Database**: Verify SQLite database location
- [ ] **Migrations**: Run schema migration `v4_0_risk_model_management`
- [ ] **Services**: Start all required services
- [ ] **Environment**: Verify .env files loaded correctly
- [ ] **Logs**: Clean old test logs from test-results/

### Step-by-Step Manual Test

#### Phase 1: Service Startup (5 minutes)

```bash
# 1. Start data service
cd /home/rahulvadera/cbp-sentry/services/data
python -m uvicorn main:app --host 0.0.0.0 --port 8005 &

# Wait for startup
sleep 3

# Verify health
curl http://localhost:8005/health
# Expected: {"status": "healthy"}

# 2. Start precise-risk-engine
cd /home/rahulvadera/cbp-sentry/services/risk-engine
python -m flask run --port 8004 &

# Wait for startup
sleep 3

# Verify health
curl http://localhost:8004/health
# Expected: {"status": "healthy", "factors": 7}

# 3. Start CORD integration service
cd /home/rahulvadera/cbp-sentry/services/cord-integration
python main.py &

# Wait for startup
sleep 3

# Verify health
curl http://localhost:8004/health
```

#### Phase 2: Database Preparation (3 minutes)

```bash
# 1. Apply migration (if not already applied)
cd /home/rahulvadera/cbp-sentry
python scripts/migrate_database.py --target v4_0_risk_model_management

# Verify schema
sqlite3 cbp_sentry.db ".tables"
# Expected output includes: risk_models, risk_model_metrics, risk_model_training_jobs, ...

# 2. Check existing data
sqlite3 cbp_sentry.db "SELECT COUNT(*) as model_count FROM risk_models;"
sqlite3 cbp_sentry.db "SELECT COUNT(*) as metric_count FROM risk_model_metrics;"
```

#### Phase 3: Run Integration Tests (5 minutes)

```bash
# Start test execution
pytest tests/integration/test_risk_model_management.py -v --tb=short

# Monitor for:
# ✅ All tests pass (45+ passed)
# ✅ No database errors
# ✅ No timeout errors
# ✅ All assertions succeed
```

#### Phase 4: Start UI (3 minutes)

```bash
# Terminal 1: Start development server
cd /home/rahulvadera/cbp-sentry/ui
npm install
npm run dev

# Expected: Vite server running on http://localhost:5173

# Terminal 2: Start API gateway (if separate from data service)
cd /home/rahulvadera/cbp-sentry/services/api
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
```

#### Phase 5: UI Integration Testing (10 minutes)

**Navigate to Risk Model Management Tab**:
1. Open browser: http://localhost:5173 (or http://localhost:3000)
2. Click "Risk Model Management" tab
3. Expected: Real data displayed from database (not mock values)

**Verify Dashboard Screen**:
- [ ] Model v3.0 displayed with accuracy 0.924
- [ ] Model v3.1 shown with "under review" status
- [ ] Pending approval from Sarah Chen visible
- [ ] Data drift alert for origin_country visible
- [ ] 24-hour accuracy trend chart populated

**Verify Model Versions Screen**:
- [ ] All 3 versions listed: v2.1, v3.0, v3.1
- [ ] v2.1 marked as "deprecated"
- [ ] v3.0 marked as "production"
- [ ] v3.1 marked as "candidate"
- [ ] Metrics displayed: accuracy, AUC-ROC, latency

**Verify Training Jobs Screen**:
- [ ] Job for v3.0 shown as "completed"
- [ ] Job for v3.1 shown as "running" with progress bar
- [ ] Job for v2.2 shown as "failed" with error message
- [ ] Hyperparameters expandable for each job

**Verify Performance Metrics Screen**:
- [ ] 24-hour accuracy trend chart visible
- [ ] Fairness metrics by origin (CN, MX, IN, HK)
- [ ] Latency percentiles: p50=45ms, p95=85ms, p99=120ms
- [ ] All values match database seed data

**Verify Data Drift Screen**:
- [ ] origin_country shows drift_score=0.34 (ELEVATED)
- [ ] commodity_value shows drift_score=0.08 (NORMAL)
- [ ] KS-statistic displayed for each feature
- [ ] "Elevated" features highlighted in red

**Verify SHAP Explanations**:
- [ ] Click on shipment prediction
- [ ] Base score displayed (45.2)
- [ ] Positive factors listed (AIS Dwell Anomaly: +8.5)
- [ ] Negative factors listed (Established Shipper Age: -3.1)
- [ ] Waterfall chart showing cumulative contribution

**Verify Approvals Screen**:
- [ ] v3.1 approval request visible
- [ ] Sarah Chen shown as approved
- [ ] John Davis shown as pending
- [ ] "Approve" / "Reject" buttons functional
- [ ] Vote recorded in database after click

**Verify Retraining Config Screen**:
- [ ] Schedule shows "Weekly Monday 02:00 UTC"
- [ ] Drift threshold shows "0.30"
- [ ] Auto-deployment toggle visible and configured
- [ ] Config editable (save changes)

### Expected Real Data Values

After test seeding, verify these values in database:

```sql
-- Check model v3.0 accuracy
SELECT accuracy FROM risk_model_metrics 
WHERE model_id = 'mdl-v3-0' 
LIMIT 1;
-- Expected: 0.924 (within range 0.920-0.928)

-- Check pending approvals
SELECT status FROM risk_model_approvals 
WHERE model_id = 'mdl-v3-1';
-- Expected: under_review

-- Check drift alert
SELECT drift_score FROM risk_model_drift_detected 
WHERE feature = 'origin_country';
-- Expected: 0.34

-- Check retraining schedule
SELECT schedule_cron FROM risk_retraining_config;
-- Expected: 0 2 * * 1 (Monday 02:00 UTC)
```

---

## DEPLOYMENT STAGES

### Stage 1: Local Development

**Objective**: Verify code works on developer machine  
**Duration**: 15-30 minutes  
**Owner**: Developer

#### Checklist

```bash
# 1. Clone/pull latest code
git clone <repo> || git pull origin main
cd cbp-sentry

# 2. Install dependencies
pip install -r requirements.txt
pip install -r services/api/requirements.txt
pip install -r services/risk-engine/requirements.txt
pip install -r ui/requirements.txt  # if applicable

# 3. Run integration tests locally
pytest tests/integration/test_risk_model_management.py -v --tb=short

# Expected: All 45+ tests PASS
# Expected runtime: < 1 minute
```

**Success Criteria**:
- [x] All integration tests pass
- [x] No database errors
- [x] No import errors
- [x] Test coverage >= 70%

### Stage 2: Continuous Integration (CI)

**Objective**: Automated testing on every commit  
**Duration**: 5-10 minutes per run  
**Owner**: GitHub Actions / GitLab CI

#### GitHub Actions Configuration

```yaml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install pytest pytest-asyncio aiosqlite pytest-cov pytest-timeout
        pip install -r requirements.txt
        pip install -r services/api/requirements.txt
        pip install -r services/risk-engine/requirements.txt
    
    - name: Run integration tests
      run: |
        pytest tests/integration/test_risk_model_management.py \
          -v \
          --tb=short \
          --cov=services \
          --cov=api \
          --cov-report=xml \
          --cov-report=term
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
    
    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: '✅ Integration tests passed!'
          })
```

**Success Criteria**:
- [x] All tests pass on push
- [x] Coverage report generated
- [x] No flaky tests
- [x] Build completes in < 10 minutes

### Stage 3: Staging Deployment

**Objective**: Test in production-like environment  
**Duration**: 20-30 minutes  
**Owner**: DevOps / Release Manager

#### Docker Compose Staging

```bash
# 1. Load staging configuration
export DEPLOYMENT_ENV=staging
export TRAFFIC_PERCENTAGE=10  # Only 10% traffic to new model
export API_URL=https://api.staging.example.com

# 2. Build Docker images
docker-compose build

# 3. Start services
docker-compose up -d

# 4. Verify services healthy
docker-compose ps
# Expected: All services running and healthy

# 5. Run smoke tests (quick verification)
pytest tests/integration/test_risk_model_management.py::TestDashboard -v --tb=short

# 6. Check logs for errors
docker-compose logs -f sentry-api | head -50
docker-compose logs -f precise-risk-engine | head -50

# 7. Run performance tests
curl -X GET http://localhost:8000/api/risk-models/dashboard \
  -H "Content-Type: application/json" \
  --write-out "Response time: %{time_total}s\n"
# Expected: < 0.5 seconds
```

**Verification Steps**:
- [ ] All services start without errors
- [ ] Health checks pass
- [ ] Dashboard queries respond in < 500ms
- [ ] Database operations in < 200ms
- [ ] No memory leaks (monitor for 5 minutes)
- [ ] Logs show no warnings/errors

#### Staging Test Execution

```bash
# 1. Apply database migration to staging DB
python scripts/migrate_database.py --env staging --target v4_0_risk_model_management

# 2. Seed test data
python scripts/seed_staging_data.py

# 3. Run full test suite
pytest tests/integration/test_risk_model_management.py \
  -v \
  --tb=short \
  --timeout=30 \
  --log-cli-level=INFO

# 4. Monitor metrics during test
# In separate terminal:
watch -n 1 'curl -s http://localhost:8000/metrics | grep risk_model'
```

**Success Criteria**:
- [x] All integration tests pass
- [x] API response time < 500ms
- [x] No database lock contention
- [x] No memory growth
- [x] Error rate < 0.1%

### Stage 4: Production Deployment

**Objective**: Deploy to production environment  
**Duration**: 30-60 minutes (with monitoring)  
**Owner**: Release Manager + On-Call Engineer

#### Pre-Deployment Verification

```bash
# 1. Create deployment checklist
echo "=== PRE-DEPLOYMENT CHECKLIST ===" > /tmp/deploy_checklist.txt
echo "[ ] All CI tests pass" >> /tmp/deploy_checklist.txt
echo "[ ] Staging tests pass" >> /tmp/deploy_checklist.txt
echo "[ ] Code review approved" >> /tmp/deploy_checklist.txt
echo "[ ] Database backups current" >> /tmp/deploy_checklist.txt
echo "[ ] Monitoring dashboards ready" >> /tmp/deploy_checklist.txt
echo "[ ] Rollback plan documented" >> /tmp/deploy_checklist.txt

# 2. Verify database backup
pg_dump cbp_sentry_prod > /backup/cbp_sentry_$(date +%Y%m%d_%H%M%S).sql
du -h /backup/cbp_sentry_prod.sql
```

#### Deployment Steps

```bash
# 1. Load production environment
export DEPLOYMENT_ENV=production
export TRAFFIC_PERCENTAGE=0  # Start at 0% traffic to new model
export API_URL=https://sentry-api-prod.example.com

# 2. Build production Docker images
docker build -t sentry-api:latest \
  --target production \
  -f services/api/Dockerfile .

docker build -t precise-risk-engine:latest \
  --target production \
  -f services/risk-engine/Dockerfile .

# 3. Push to registry
docker tag sentry-api:latest gcr.io/cbp-sentry/sentry-api:v1.2.3
docker tag precise-risk-engine:latest gcr.io/cbp-sentry/precise-risk-engine:v1.2.3

docker push gcr.io/cbp-sentry/sentry-api:v1.2.3
docker push gcr.io/cbp-sentry/precise-risk-engine:v1.2.3

# 4. Apply database migration
python scripts/migrate_database.py \
  --env production \
  --target v4_0_risk_model_management \
  --backup /backup/pre_migration_$(date +%s).sql

# 5. Deploy API service
kubectl set image deployment/sentry-api \
  sentry-api=gcr.io/cbp-sentry/sentry-api:v1.2.3 \
  --namespace=production

# 6. Wait for rollout
kubectl rollout status deployment/sentry-api --namespace=production

# 7. Deploy risk engine
kubectl set image deployment/precise-risk-engine \
  precise-risk-engine=gcr.io/cbp-sentry/precise-risk-engine:v1.2.3 \
  --namespace=production

# 8. Monitor deployment
kubectl logs -f -l app=sentry-api --namespace=production | tail -100
```

#### Canary Deployment (Recommended)

```bash
# 1. Deploy to 5% of traffic
export TRAFFIC_PERCENTAGE=5

# 2. Monitor for 5 minutes
for i in {1..30}; do
  echo "=== Minute $((i/6)) ===" 
  curl -s https://api-prod.example.com/metrics | grep error_rate
  sleep 10
done

# 3. If no errors, increase to 25%
export TRAFFIC_PERCENTAGE=25
# Monitor for 10 minutes

# 4. If still healthy, increase to 100%
export TRAFFIC_PERCENTAGE=100
# Monitor for 30 minutes before considering complete
```

#### Verification After Deployment

```bash
# 1. Health checks
curl https://api-prod.example.com/health
# Expected: {"status": "healthy"}

# 2. Run smoke tests (subset of integration tests)
pytest tests/integration/test_risk_model_management.py::TestDashboard \
  --timeout=30 \
  -v \
  --tb=short \
  -m "not slow"

# 3. Check for errors in logs
kubectl logs -l app=sentry-api --namespace=production | grep ERROR | wc -l
# Expected: 0 (or < 5 in first 10 minutes)

# 4. Monitor API response times
curl -w "@/tmp/curl_format.txt" -o /dev/null -s https://api-prod.example.com/api/risk-models/dashboard
# Expected: < 500ms
```

**Success Criteria**:
- [x] All services healthy
- [x] API response time < 500ms
- [x] Error rate < 0.1%
- [x] No database lock issues
- [x] No memory growth
- [x] All smoke tests pass

---

## MONITORING & ALERTS

### Key Metrics to Monitor

#### API Performance

```bash
# Response time (P95 latency)
prometheus_query 'histogram_quantile(0.95, http_request_duration_seconds{service="sentry-api"})'
# Target: < 500ms

# Request rate
prometheus_query 'rate(http_requests_total{service="sentry-api"}[5m])'
# Expected: Increase during deployment, then stabilize

# Error rate
prometheus_query 'rate(http_requests_total{status=~"5.."}[5m])'
# Target: < 0.1%
```

#### Database Performance

```bash
# Query latency (P95)
prometheus_query 'histogram_quantile(0.95, db_query_duration_seconds)'
# Target: < 200ms

# Connection pool usage
prometheus_query 'db_connections_active / db_connections_max'
# Target: < 0.8

# Slow query count
prometheus_query 'increase(db_slow_queries_total[5m])'
# Target: 0
```

#### Model Service Performance

```bash
# Risk engine response time
prometheus_query 'histogram_quantile(0.95, risk_engine_prediction_duration_seconds)'
# Target: < 2000ms

# Model inference success rate
prometheus_query 'rate(risk_engine_predictions_total{status="success"}[5m])'
# Target: > 99%

# Cache hit rate
prometheus_query 'rate(risk_engine_cache_hits_total[5m]) / rate(risk_engine_cache_requests_total[5m])'
# Target: > 80%
```

### Alert Rules

#### Critical Alerts (Page on-call immediately)

```yaml
# 1. Error rate spike
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01  # > 1%
for: 5m
action: PagerDuty

# 2. API unavailable
alert: APIDown
expr: up{job="sentry-api"} == 0
for: 2m
action: PagerDuty

# 3. Database connection failure
alert: DatabaseDown
expr: pg_up{job="cbp_sentry_db"} == 0
for: 2m
action: PagerDuty

# 4. Risk engine failure
alert: RiskEngineDown
expr: up{job="precise-risk-engine"} == 0
for: 2m
action: PagerDuty
```

#### Warning Alerts (Notify Slack)

```yaml
# 1. High response latency
alert: HighLatency
expr: histogram_quantile(0.95, http_request_duration_seconds{service="sentry-api"}) > 0.5
for: 10m
action: Slack #monitoring

# 2. High database query time
alert: SlowDatabaseQueries
expr: histogram_quantile(0.95, db_query_duration_seconds) > 0.2
for: 10m
action: Slack #monitoring

# 3. Memory usage trending up
alert: MemoryLeakDetected
expr: increase(container_memory_usage_bytes[30m]) / container_memory_usage_bytes > 0.2
for: 15m
action: Slack #monitoring

# 4. Model service degradation
alert: RiskEngineSlowResponse
expr: histogram_quantile(0.95, risk_engine_prediction_duration_seconds) > 2
for: 10m
action: Slack #monitoring
```

### Logging Configuration

```bash
# View live logs from all services
kubectl logs -f -l app=sentry-api --namespace=production \
  --timestamps=true \
  --tail=100 &

kubectl logs -f -l app=precise-risk-engine --namespace=production \
  --timestamps=true \
  --tail=100 &

# Search logs for errors
kubectl logs -l app=sentry-api --namespace=production \
  | grep ERROR \
  | tail -20

# Export logs for analysis
kubectl logs -l app=sentry-api --namespace=production \
  --timestamps=true \
  > /tmp/api_logs_$(date +%s).log
```

### Dashboard Setup (Grafana)

Create dashboard with:
- API request rate (requests/sec)
- API latency (P50, P95, P99)
- Error rate (%)
- Database connection pool usage (%)
- Model inference latency (ms)
- Cache hit rate (%)

---

## ROLLBACK PROCEDURES

### Scenario 1: Deployment Failed (Pre-Production)

```bash
# 1. Identify failure
kubectl describe deployment sentry-api --namespace=production

# 2. Check recent deployment history
kubectl rollout history deployment/sentry-api --namespace=production

# 3. Rollback to previous version
kubectl rollout undo deployment/sentry-api --namespace=production

# 4. Verify rollback
kubectl get deployment sentry-api --namespace=production
kubectl logs -f -l app=sentry-api --namespace=production | head -20

# 5. Investigate failure
# Review deployment logs, check for configuration errors, missing secrets, etc.
```

### Scenario 2: Tests Failing in Production

```bash
# 1. Stop new traffic to model
export TRAFFIC_PERCENTAGE=0

# 2. Kill deployment if necessary
kubectl delete pod -l app=sentry-api --namespace=production

# 3. Restore previous version
kubectl rollout undo deployment/sentry-api --namespace=production
kubectl rollout undo deployment/precise-risk-engine --namespace=production

# 4. Verify previous version working
pytest tests/integration/test_risk_model_management.py::TestDashboard -v

# 5. Notify stakeholders
# Send rollback notification to #incidents Slack channel
```

### Scenario 3: Database Migration Failed

```bash
# 1. Stop all API requests
# Maintenance mode: Scale down replicas
kubectl scale deployment sentry-api --replicas=0 --namespace=production

# 2. Restore database from backup
pg_restore -d cbp_sentry_prod \
  /backup/pre_migration_$(ls -t /backup | head -1 | cut -d_ -f4).sql

# 3. Verify database integrity
sqlite3 cbp_sentry.db ".schema risk_models"
sqlite3 cbp_sentry.db "SELECT COUNT(*) FROM risk_models;"

# 4. Restart API
kubectl scale deployment sentry-api --replicas=3 --namespace=production

# 5. Run smoke tests
pytest tests/integration/test_risk_model_management.py::TestDashboard -v
```

### Scenario 4: Performance Degradation

```bash
# 1. Identify slow component
# Check API logs for slow query warnings
kubectl logs -l app=sentry-api --namespace=production \
  | grep "slow_query\|duration > 500ms" | tail -20

# 2. Reduce traffic to model service
export TRAFFIC_PERCENTAGE=0

# 3. Check for blocking queries
sqlite3 cbp_sentry.db ".mode line"
sqlite3 cbp_sentry.db "SELECT COUNT(*) FROM sqlite_master WHERE type='index';"

# 4. Trigger manual index rebuild
python scripts/rebuild_database_indexes.py

# 5. Gradually restore traffic
export TRAFFIC_PERCENTAGE=10  # Monitor for 5 minutes
export TRAFFIC_PERCENTAGE=50  # Monitor for 10 minutes
export TRAFFIC_PERCENTAGE=100 # Full traffic
```

---

## TROUBLESHOOTING

### Common Issues & Solutions

#### Issue 1: "No such table: risk_models"

**Cause**: Database migration not applied

**Solution**:
```bash
# 1. Check current schema version
python scripts/get_schema_version.py
# Output: Current version: v3.0

# 2. Apply missing migration
python scripts/migrate_database.py --target v4_0_risk_model_management

# 3. Verify schema
sqlite3 cbp_sentry.db ".tables"
# Should include: risk_models, risk_model_metrics, risk_model_training_jobs, ...
```

#### Issue 2: Tests Timeout After 30 Seconds

**Cause**: Database lock or slow query

**Solution**:
```bash
# 1. Check for blocking queries
sqlite3 cbp_sentry.db "SELECT * FROM pragma_database_list;"

# 2. Kill long-running queries
sqlite3 cbp_sentry.db "SELECT * FROM sqlite_stat1 LIMIT 10;"

# 3. Increase timeout in pytest.ini
# Change: timeout = 30
# To:     timeout = 60

# 4. Rebuild indexes
python scripts/rebuild_database_indexes.py

# 5. Rerun tests
pytest tests/integration/test_risk_model_management.py -v --timeout=60
```

#### Issue 3: "Event loop is closed" Error

**Cause**: AsyncIO event loop configuration

**Solution**:
```bash
# 1. Ensure pytest marker used
# ✓ @pytest.mark.asyncio
# async def test_something(self, test_db):

# 2. Check pytest.ini
# Should have: asyncio_mode = auto

# 3. Install pytest-asyncio
pip install pytest-asyncio>=0.21.0

# 4. Rerun tests
pytest tests/integration/test_risk_model_management.py -v
```

#### Issue 4: Health Check Fails

**Cause**: Service not started or port conflict

**Solution**:
```bash
# 1. Check if ports available
lsof -i :8000
lsof -i :8004
lsof -i :8005

# 2. Kill process on conflicting port
kill -9 <PID>

# 3. Start service with explicit port
python -m flask run --port 8004 &
sleep 2

# 4. Test health endpoint
curl -v http://localhost:8004/health
# Expected: {"status": "healthy"}
```

#### Issue 5: Tests Show Stale Data

**Cause**: Database not cleaned between runs

**Solution**:
```bash
# 1. Remove test database
rm -f /tmp/test_risk_models.db

# 2. Re-run tests (fresh database created)
pytest tests/integration/test_risk_model_management.py -v

# 3. Verify fresh data
sqlite3 /tmp/test_risk_models.db "SELECT COUNT(*) FROM risk_models;"
# Should show 3 (freshly seeded)
```

#### Issue 6: Coverage Below 70%

**Cause**: Tests not covering all code paths

**Solution**:
```bash
# 1. Generate detailed coverage report
pytest tests/integration/test_risk_model_management.py \
  --cov=services \
  --cov=api \
  --cov-report=html \
  --cov-report=term-missing

# 2. Review missing lines
# Open htmlcov/index.html and identify uncovered code

# 3. Add tests for missing paths
# Edit test_risk_model_management.py and add missing test cases

# 4. Re-run coverage
pytest tests/integration/test_risk_model_management.py --cov=services --cov=api --cov-report=html
```

#### Issue 7: Database Lock Contention

**Cause**: Concurrent test writes

**Solution**:
```bash
# 1. Check for lock
sqlite3 cbp_sentry.db ".mode line"
sqlite3 cbp_sentry.db "PRAGMA integrity_check;"

# 2. Disable concurrent writes in tests
# In pytest.ini: addopts = -n 1  # Single process only

# 3. Increase lock timeout
# In test fixture:
db.execute("PRAGMA busy_timeout = 5000;")  # 5 seconds

# 4. Use WAL mode (Write-Ahead Logging)
sqlite3 cbp_sentry.db "PRAGMA journal_mode = WAL;"

# 5. Rerun tests
pytest tests/integration/test_risk_model_management.py -v -n 1
```

---

## APPENDIX: QUICK REFERENCE

### Command Reference

```bash
# Run all tests
pytest tests/integration/test_risk_model_management.py -v

# Run with coverage
pytest tests/integration/test_risk_model_management.py --cov=api --cov=services --cov-report=html

# Run specific class
pytest tests/integration/test_risk_model_management.py::TestDashboard -v

# Run single test
pytest tests/integration/test_risk_model_management.py::TestDashboard::test_get_dashboard_returns_real_metrics -v

# Run with output
pytest tests/integration/test_risk_model_management.py -v -s

# Run with debugging
pytest tests/integration/test_risk_model_management.py -v -s --log-cli-level=DEBUG

# Run with timeout
pytest tests/integration/test_risk_model_management.py --timeout=60 -v

# Run quiet mode
pytest tests/integration/test_risk_model_management.py -q
```

### File Locations

| Item | Path |
|------|------|
| Test Suite | `/home/rahulvadera/cbp-sentry/tests/integration/test_risk_model_management.py` |
| Test Docs | `/home/rahulvadera/cbp-sentry/tests/integration/TEST_SUITE_DOCUMENTATION.md` |
| Database | `/home/rahulvadera/cbp-sentry/cbp_sentry.db` |
| API Service | `/home/rahulvadera/cbp-sentry/services/api/` |
| Risk Engine | `/home/rahulvadera/cbp-sentry/services/risk-engine/` |
| Docker Compose | `/home/rahulvadera/cbp-sentry/docker-compose.yml` |

### Environment Variables

| Var | Purpose | Default |
|-----|---------|---------|
| `DEPLOYMENT_ENV` | Environment name | `local` |
| `USE_PRECISE_RISK_MODEL` | Enable new model | `false` |
| `TRAFFIC_PERCENTAGE` | % traffic to new model | `0` |
| `PRECISE_RISK_ENGINE_URL` | Risk engine URL | `http://localhost:8004` |
| `DATABASE_URL` | DB connection string | `sqlite:///./data/cbp_sentry.db` |
| `API_PORT` | API port | `8000` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### Test Data Defaults

- **Models**: 3 versions (v2.1 deprecated, v3.0 production, v3.1 candidate)
- **Metrics**: 24 hourly points (past 24h), per model
- **Training Jobs**: 3 jobs (completed, running, failed)
- **Fairness Segments**: CN, MX, IN, HK
- **Latency Percentiles**: p50=45ms, p95=85ms, p99=120ms
- **Drift Alerts**: origin_country (elevated), commodity_value (normal)
- **Approvals**: 1 workflow (v3.1, 1 approved, 1 pending)
- **Retraining Config**: Weekly Monday 02:00 UTC, threshold 0.30

---

## SUPPORT & REFERENCES

For additional information:

- **Full Test Documentation**: `tests/integration/TEST_SUITE_DOCUMENTATION.md`
- **Quick Start Guide**: `tests/integration/QUICK_START.md`
- **Test Manifest**: `tests/integration/MANIFEST.md`
- **API Design**: `RISK_MODEL_MANAGEMENT_API.md`
- **Phase 2 Deployment**: `DEPLOYMENT_AND_TESTING_GUIDE.md`

---

**Document Version**: 1.0  
**Last Updated**: June 13, 2026  
**Status**: Production Ready
