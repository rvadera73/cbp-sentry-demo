# CBP Sentry: Risk Scoring Infrastructure Setup (Phase 1)

**Date**: June 12, 2026
**Status**: Ready for Implementation
**Target Environments**: Development, Staging, Production

---

## Overview

This document describes the complete infrastructure setup for Phase 1 of the Precise Risk Model, including:

1. **PostgreSQL risk_scoring schema** with 12 tables
2. **GCP Cloud Storage** bucket for model artifacts
3. **Redis cache** for inference result caching
4. **CBP domain configuration** with 7-factor engine, 3 gates, and 8 rules

---

## Architecture

### Database Layer
- **Schema**: `risk_scoring` (isolated from main `public` schema)
- **Tables**: 12 tables supporting model management, scoring, feedback, and monitoring
- **Key Features**:
  - Slowly Changing Dimension Type 2 for rule parameter versioning
  - Immutable audit log for compliance
  - JSONB columns for flexible configuration
  - Indexed for high-performance querying

### Storage Layer
- **GCP Cloud Storage**: `gs://cbp-sentry-models`
- **Model Artifact Paths**:
  - `cbp/xgboost/` — XGBoost ensemble models
  - `cbp/isolation_forest/` — Anomaly detection models
  - `cbp/shap_explainer/` — Model interpretability artifacts
  - `cbp/training_data/` — Training datasets
  - `cbp/evaluation_results/` — Model evaluation metrics

### Cache Layer
- **Redis**: In-memory cache for inference results
- **Key Format**: `risk_score:cbp:{entity_id}`
- **TTL**: 7 days (604800 seconds)
- **Purpose**: Reduce database queries, improve latency

---

## Prerequisites

### System Requirements
- PostgreSQL 12+ (or compatible version)
- Python 3.8+
- Redis 6.0+ (optional; can be deployed separately)
- Google Cloud SDK (for GCP operations)

### Python Dependencies
```bash
pip install psycopg2-binary redis google-cloud-storage
```

### Environment Variables
```bash
# Required
export DATABASE_URL="postgresql://user:password@localhost:5432/cbp_sentry"

# Optional
export GCP_PROJECT_ID="cbp-sentry"
export REDIS_URL="redis://localhost:6379"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

---

## Setup Instructions

### Step 1: Verify PostgreSQL Connection

```bash
# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

### Step 2: Run Infrastructure Setup

```bash
cd /home/rahulvadera/cbp-sentry

# Execute the comprehensive setup script
python3 scripts/setup_risk_scoring_infrastructure.py \
    --postgres-url $DATABASE_URL \
    --gcp-project cbp-sentry \
    --redis-url "redis://localhost:6379" \
    --output-json /tmp/setup_result.json
```

### Step 3: Verify Setup

```bash
# Check PostgreSQL schema
psql $DATABASE_URL -c "
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'risk_scoring' ORDER BY table_name;
"

# Check CBP domain registration
psql $DATABASE_URL -c "
    SELECT domain_id, name, description FROM risk_scoring.domains
    WHERE name = 'cbp_illegal_transshipment';
"

# Check GCP bucket
gsutil ls -r gs://cbp-sentry-models/

# Check Redis connectivity
redis-cli -u $REDIS_URL ping
```

---

## Database Schema Overview

### 1. domains
Registers risk assessment domains.
- **Columns**: domain_id, name, description, created_at, updated_at

### 2. scorecards
Defines scoring configuration per domain.
- **Columns**: scorecard_id, domain_id, factors (JSONB), rules (JSONB), thresholds (JSONB)
- **Data**: 7 factors, 3 gates, 8 rules

### 3. features_cbp
Feature catalog for the CBP domain (7 core risk indicators).
- **Columns**: feature_id, name, description, type, data_type
- **Features**:
  1. shipper_sanction_risk
  2. destination_risk
  3. entity_history
  4. shipment_pattern_anomaly
  5. product_risk
  6. routing_anomaly
  7. regulatory_flag_history

### 4. rule_parameters (SCD Type 2)
Tracks rule parameter changes with version history.
- **Columns**: parameter_id, rule_id, parameter_name, parameter_value, valid_from, valid_to
- **Use Case**: Audit trail for rule configuration changes

### 5. rule_change_events
Immutable audit log of all rule changes.
- **Columns**: event_id, parameter_id, rule_id, change_type, old_value, new_value, changed_by, change_timestamp
- **Constraint**: IMMUTABLE (timestamps cannot be updated)

### 6. model_scores
Latest risk scores for entities (denormalized for performance).
- **Columns**: score_id, entity_id, domain_id, score, confidence, explanation (JSONB), timestamp
- **Unique Constraint**: (entity_id, domain_id)

### 7. feedback
Analyst feedback and ground truth labels.
- **Columns**: feedback_id, entity_id, domain_id, analyst_label, confidence, notes, analyst_id, timestamp

### 8. model_training_runs
Historical training iteration records.
- **Columns**: training_id, domain_id, model_version_id, training_start, training_end, training_size, auc, precision, recall, f1_score, hyperparameters (JSONB)

### 9. drift_alerts
Data drift detection monitoring.
- **Columns**: alert_id, domain_id, feature_name, ks_statistic, pvalue, drift_detected, alert_level, timestamp

### 10. model_versions
Model artifact versioning and deployment tracking.
- **Columns**: model_version_id, domain_id, model_name, model_type, model_path, trained_at, deployed_at, retired_at, auc, is_active

### 11. model_inference_cache
Redis-synced cache for inference results.
- **Columns**: cache_id, entity_id, domain_id, score, confidence, cached_at, expires_at, redis_key

### 12. model_performance_metrics
Aggregated performance metrics for monitoring.
- **Columns**: metric_id, domain_id, model_version_id, metric_name, metric_value, measured_at, cohort_filter

---

## CBP Domain Configuration

### Domain: cbp_illegal_transshipment

**Purpose**: Detect illegal transshipment attempts targeting United States customs enforcement.

### 7 Risk Factors (Equal Weight: 0.143 Each)

1. **shipper_sanction_risk** - OFAC/SDN match confidence
2. **destination_risk** - Destination country/port risk score
3. **entity_history** - Prior violations and compliance history
4. **shipment_pattern_anomaly** - Quantity/frequency/value anomalies
5. **product_risk** - HTS code and controlled item classification
6. **routing_anomaly** - Multi-hop, consolidation, re-export flags
7. **regulatory_flag_history** - Enforcement action count

### 3 Sequential Gates (Decision Boundaries)

| Gate | Name | Threshold | Rules | Purpose |
|------|------|-----------|-------|---------|
| 1 | Destination Risk | 0.70 | R1, R2 | Block OFAC sanctioned destinations |
| 2 | Entity Assessment | 0.65 | R3, R4, R8 | Identify problematic entities |
| 3 | Shipment Anomaly | 0.60 | R5, R6, R7 | Flag unusual shipping patterns |

### 8 Rules

| ID | Name | Gate | Trigger |
|----|------|------|---------|
| R1 | OFAC Sanction Match | 1 | Shipper/consignee matches SDN list (confidence > 0.85) |
| R2 | High-Risk Destination | 1 | Destination risk score > 0.70 |
| R3 | Entity Repeat Violator | 2 | 3+ violations in past 3 years |
| R4 | Conflicting Entity Data | 2 | Address/name variance confidence > 0.80 |
| R5 | Anomalous Quantity Jump | 3 | 2.5σ deviation from 180-day baseline |
| R6 | Unusual Routing Pattern | 3 | Multi-hop/consolidation detected |
| R7 | Controlled + High-Risk | 3 | Controlled product (BIS/AECA/ITAR) to high-risk destination |
| R8 | Regulatory Hold History | 2 | 2+ holds in past 365 days |

---

## File Structure

```
/home/rahulvadera/cbp-sentry/
├── scripts/
│   ├── setup_risk_scoring_infrastructure.py  [Main setup orchestrator]
│   └── sql/
│       ├── 01-risk_scoring-schema.sql        [12-table schema]
│       └── 02-cbp-domain-init.sql            [CBP domain config]
├── RISK_SCORING_INFRASTRUCTURE_SETUP.md      [This file]
└── [API and services...]
```

---

## Deployment Workflows

### Local Development

```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Start Redis
docker-compose up -d redis

# 3. Run setup
python3 scripts/setup_risk_scoring_infrastructure.py \
    --postgres-url "postgresql://postgres:postgres@localhost:5432/cbp_sentry" \
    --redis-url "redis://localhost:6379"

# 4. Verify
psql "postgresql://postgres:postgres@localhost:5432/cbp_sentry" -c \
    "SELECT COUNT(*) FROM risk_scoring.domains;"
```

### Cloud Deployment (GCP)

```bash
# 1. Create Cloud SQL instance
gcloud sql instances create cbp-sentry-postgres \
    --database-version POSTGRES_14 \
    --tier db-g1-small \
    --region us-central1

# 2. Create database
gcloud sql databases create cbp_sentry \
    --instance cbp-sentry-postgres

# 3. Run setup with Cloud SQL proxy
cloud-sql-proxy cbp-sentry:us-central1:cbp-sentry-postgres &
python3 scripts/setup_risk_scoring_infrastructure.py \
    --postgres-url "postgresql://postgres:PASSWORD@127.0.0.1:5432/cbp_sentry" \
    --gcp-project cbp-sentry

# 4. Create Redis instance
gcloud redis instances create cbp-sentry-cache \
    --size 1 \
    --region us-central1

# 5. Configure environment
gcloud compute project-info add-metadata \
    --metadata="REDIS_URL=redis://cbp-sentry-cache:6379"
```

---

## Success Criteria

- [x] risk_scoring schema created
- [x] All 12 tables created
- [x] CBP domain registered with 7 features
- [x] 8 rules configured with parameters
- [x] GCP bucket ready (gs://cbp-sentry-models)
- [x] Redis cache configured (7-day TTL)
- [x] SQL scripts ready for deployment

---

## Monitoring and Maintenance

### Health Checks

```sql
-- Check schema status
SELECT COUNT(*) as table_count FROM information_schema.tables
WHERE table_schema = 'risk_scoring';

-- Verify CBP domain
SELECT domain_id FROM risk_scoring.domains WHERE name = 'cbp_illegal_transshipment';

-- Check rule parameters
SELECT COUNT(*) FROM risk_scoring.rule_parameters;

-- Monitor cache performance
SELECT COUNT(*) FROM risk_scoring.model_inference_cache
WHERE expires_at > CURRENT_TIMESTAMP;
```

### Scaling Considerations

- **PostgreSQL**: Index strategy for high-volume scoring (entity_id lookups)
- **Redis**: Memory management for 7-day retention at scale (100K+ entities)
- **GCP**: Versioned model storage with lifecycle policies
- **Monitoring**: CloudSQL monitoring, Redis memory usage, bucket access logs

---

## Next Steps (Phase 2)

1. **Model Training Pipeline** — Train XGBoost and isolation forest models
2. **Inference API** — Real-time scoring endpoint with Redis caching
3. **Feedback Loop** — Analyst ground truth collection
4. **Monitoring Dashboard** — Performance and drift metrics
5. **Rule Engine** — Production rule evaluation with SCD Type 2 parameters

---

## Support and Troubleshooting

### PostgreSQL Connection Issues

```bash
# Verify connection
psql -U postgres -h localhost -d cbp_sentry -c "SELECT 1;"

# Check logs
docker logs postgres

# Reset connection
docker-compose down
docker-compose up -d postgres
```

### GCP Bucket Issues

```bash
# Verify bucket exists
gsutil ls gs://cbp-sentry-models/

# Check permissions
gsutil iam ch user:your-email@example.com:objectCreator gs://cbp-sentry-models

# Enable Cloud Storage API
gcloud services enable storage.googleapis.com
```

### Redis Connection Issues

```bash
# Test connection
redis-cli -u redis://localhost:6379 ping

# Check memory
redis-cli info memory

# Monitor keys
redis-cli keys "risk_score:*"
```

---

## References

- [PostgreSQL JSON/JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Redis Documentation](https://redis.io/documentation)
- [Slowly Changing Dimensions (SCD Type 2)](https://en.wikipedia.org/wiki/Slowly_changing_dimension)

---

**Setup Date**: June 12, 2026
**Last Updated**: June 12, 2026
**Status**: Ready for Implementation
