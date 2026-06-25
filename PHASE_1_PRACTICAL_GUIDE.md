# Phase 1: Practical Execution Guide

**Status**: Ready to execute NOW (June 12, 2026)  
**Realistic Timeline**: 4 weeks  
**Approach**: Real code + agent guidance (not agent-only)

---

## HONEST ASSESSMENT

The workflow agents generate PLANS, not actual code/data/models. To implement Phase 1, we need to:

1. **Create actual data structures** (databases, files, etc.)
2. **Write actual code** (feature engineering, model training, APIs)
3. **Deploy actual services** (Docker, GCP, etc.)
4. Use agents for **guidance, validation, and decision-making**—not as primary execution

---

## WEEK 1: START HERE (1 week to complete)

### Step 1.1: Verify EAPA Data Access
**Time**: 1-2 hours

```bash
# Check what EAPA data exists
find /home/rahulvadera/cbp-sentry -name "*eapa*" -o -name "*transship*" 2>/dev/null

# Check database for EAPA table
psql cbp_sentry -c "
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public' 
  AND table_name ILIKE '%eapa%' OR table_name ILIKE '%transship%';
"

# Count how many confirmed transshipment cases exist
psql cbp_sentry -c "SELECT COUNT(*) FROM manifests WHERE is_confirmed_transshipment = true;"
```

**Expected Output**:
- EAPA data location identified (file or DB table)
- 287 confirmed transshipment cases confirmed
- Field structure documented

---

### Step 1.2: Create PostgreSQL Schema
**Time**: 2 hours

```bash
# Create schema file
cat > /home/rahulvadera/cbp-sentry/schema/risk_scoring_schema.sql << 'EOF'
-- Create risk_scoring schema
CREATE SCHEMA IF NOT EXISTS risk_scoring;

-- Domains table
CREATE TABLE IF NOT EXISTS risk_scoring.domains (
  domain_id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Scorecards table
CREATE TABLE IF NOT EXISTS risk_scoring.scorecards (
  scorecard_id VARCHAR(100) PRIMARY KEY,
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  factors JSONB,
  rules JSONB,
  thresholds JSONB,
  git_commit_sha VARCHAR(40),
  activated_at TIMESTAMP,
  deactivated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Features table
CREATE TABLE IF NOT EXISTS risk_scoring.features_cbp (
  feature_id VARCHAR(100) PRIMARY KEY,
  feature_name VARCHAR(255) NOT NULL,
  feature_description TEXT,
  factor_category VARCHAR(50),
  data_type VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Model training runs
CREATE TABLE IF NOT EXISTS risk_scoring.model_training_runs (
  training_id SERIAL PRIMARY KEY,
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  scorecard_version VARCHAR(50),
  xgboost_version VARCHAR(50),
  iforest_version VARCHAR(50),
  training_start TIMESTAMP,
  training_end TIMESTAMP,
  training_sample_size INT,
  auc FLOAT,
  precision FLOAT,
  recall FLOAT,
  f1_score FLOAT,
  deployed BOOLEAN DEFAULT FALSE,
  deployed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Model scores
CREATE TABLE IF NOT EXISTS risk_scoring.model_scores (
  score_id SERIAL PRIMARY KEY,
  entity_id VARCHAR(100),
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  risk_score FLOAT,
  confidence FLOAT,
  explanation JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Model versions
CREATE TABLE IF NOT EXISTS risk_scoring.model_versions (
  model_version_id VARCHAR(50) PRIMARY KEY,
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  model_type VARCHAR(50),
  model_path VARCHAR(255),
  trained_at TIMESTAMP,
  deployed_at TIMESTAMP,
  auc FLOAT,
  precision FLOAT,
  recall FLOAT,
  deployed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Insert CBP domain
INSERT INTO risk_scoring.domains (domain_id, name, description)
VALUES ('cbp', 'CBP Illegal Transshipment', 'Detect misdeclared shipments')
ON CONFLICT DO NOTHING;
EOF

# Apply schema
psql cbp_sentry -f /home/rahulvadera/cbp-sentry/schema/risk_scoring_schema.sql

# Verify tables created
psql cbp_sentry -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'risk_scoring';"
```

**Expected Output**:
```
 table_name
---------------------
 domains
 scorecards
 features_cbp
 model_training_runs
 model_scores
 model_versions
(6 rows)
```

---

### Step 1.3: Export Training Data
**Time**: 2-3 hours

```bash
# Create data directory
mkdir -p /home/rahulvadera/cbp-sentry/data
mkdir -p /home/rahulvadera/cbp-sentry/models

# Export EAPA cases (positive class)
psql cbp_sentry -c "
  COPY (
    SELECT 
      manifest_id as entity_id,
      shipment_date,
      origin_country,
      destination_country,
      hs_code,
      quantity,
      declared_value,
      importer_id,
      shipper_id,
      1 as label
    FROM manifests 
    WHERE is_confirmed_transshipment = true
    LIMIT 287
  ) TO STDOUT WITH (FORMAT csv, HEADER true)
" > /home/rahulvadera/cbp-sentry/data/eapa_cases.csv

# Count: should be 287
wc -l /home/rahulvadera/cbp-sentry/data/eapa_cases.csv

# Export non-EAPA manifests (negative class) - sample 10K
psql cbp_sentry -c "
  COPY (
    SELECT 
      manifest_id as entity_id,
      shipment_date,
      origin_country,
      destination_country,
      hs_code,
      quantity,
      declared_value,
      importer_id,
      shipper_id,
      0 as label
    FROM manifests 
    WHERE is_confirmed_transshipment = false
    ORDER BY RANDOM()
    LIMIT 10000
  ) TO STDOUT WITH (FORMAT csv, HEADER true)
" > /home/rahulvadera/cbp-sentry/data/normal_manifests.csv

# Combine into single training file
(cat /home/rahulvadera/cbp-sentry/data/eapa_cases.csv && tail -n +2 /home/rahulvadera/cbp-sentry/data/normal_manifests.csv) \
  > /home/rahulvadera/cbp-sentry/data/training_data.csv

# Verify: should be 10,288 lines (287 + 10K + header)
wc -l /home/rahulvadera/cbp-sentry/data/training_data.csv
```

**Expected Output**:
- `eapa_cases.csv`: 288 lines (287 cases + header)
- `normal_manifests.csv`: 10,001 lines (10K cases + header)
- `training_data.csv`: 10,288 lines (10,287 cases + header)

---

### Step 1.4: Create Metadata
**Time**: 30 min

```bash
cat > /home/rahulvadera/cbp-sentry/data/training_metadata.json << 'EOF'
{
  "total_samples": 10287,
  "positive_cases": 287,
  "negative_cases": 10000,
  "class_balance_pct": 2.79,
  "date_created": "2026-06-12",
  "eapa_source": "cbp_sentry.manifests (is_confirmed_transshipment = true)",
  "manifest_source": "cbp_sentry.manifests (is_confirmed_transshipment = false)",
  "train_test_split": "70/30 stratified",
  "required_fields": [
    "entity_id", "shipment_date", "origin_country", "destination_country",
    "hs_code", "quantity", "declared_value", "importer_id", "shipper_id", "label"
  ],
  "status": "ready_for_feature_engineering"
}
EOF

cat /home/rahulvadera/cbp-sentry/data/training_metadata.json
```

---

## WEEK 1 CHECKPOINT ✅

- [ ] EAPA data located (287 confirmed cases)
- [ ] PostgreSQL risk_scoring schema created (6+ tables)
- [ ] training_data.csv created (10,287 samples)
- [ ] training_metadata.json created
- [ ] Files verified in `/home/rahulvadera/cbp-sentry/data/`

**Go/No-Go Decision**: If all 4 checkboxes ✅, proceed to Week 2. Otherwise, escalate.

---

## WEEK 2: FEATURE ENGINEERING

**Status**: Awaiting Week 1 checkpoint completion

Once training_data.csv is ready, create feature engineering script:

```python
# Location: /home/rahulvadera/cbp-sentry/scripts/feature_engineering.py
# Full implementation in next section (waiting for Week 1 completion)
```

---

## DELIVERABLES CHECKLIST

| Week | Task | Status | Owner | Deadline |
|------|------|--------|-------|----------|
| 1 | Data validation (287 EAPA + 10K manifests) | TBD | Data Eng | June 14 |
| 1 | PostgreSQL risk_scoring schema | TBD | Backend | June 14 |
| 1 | GCP Cloud Storage bucket setup | TBD | DevOps | June 14 |
| 1 | Redis cache configuration | TBD | DevOps | June 14 |
| **CHECKPOINT** | **Week 1 Decision Gate** | TBD | Team | June 14 EOD |
| 2 | Feature engineering (72 features) | TBD | ML | June 21 |
| 3 | Model training (XGBoost, Isolation Forest, SHAP) | TBD | ML | June 28 |
| 3 | Microservice scaffold (precise-risk-engine-api) | TBD | Backend | June 28 |
| **CHECKPOINT** | **Week 3 Decision Gate** | TBD | Team | June 28 EOD |
| 4 | Integration & deployment to GCP | TBD | Backend+DevOps | July 5 |
| 4 | End-to-end testing + rollout | TBD | QA | July 5 |
| **CHECKPOINT** | **Phase 1 Complete** | TBD | Team | July 5 EOD |

---

## HOW TO PROCEED

### Option A: Execute Week 1 Now (2-3 hours)
Run the bash commands above in sequence. This is the actual, practical path forward.

### Option B: Get Agent Guidance
I can run agents to validate/review your Week 1 execution, suggest improvements, or help with complex decisions.

### Option C: Hybrid (Recommended)
1. Execute Week 1 steps (real work)
2. Have agents review the outputs
3. Get approval before proceeding to Week 2

---

## What Are You Choosing?

- **A**: Execute Week 1 now (practical)
- **B**: Get agent analysis before executing
- **C**: Hybrid (execute + review)

Let me know which approach, and I'll guide you through the next steps!
