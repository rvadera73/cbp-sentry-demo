# CBP Sentry Infrastructure Deployment Guide

**Phase 1: Risk Scoring Infrastructure (June 12, 2026)**

---

## Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install psycopg2-binary redis google-cloud-storage

# Set environment variables
export DATABASE_URL="postgresql://user:password@host:5432/cbp_sentry"
export GCP_PROJECT_ID="cbp-sentry"
export REDIS_URL="redis://localhost:6379"
```

### Deploy Infrastructure

```bash
cd /home/rahulvadera/cbp-sentry

# Run setup
python3 scripts/setup_risk_scoring_infrastructure.py \
    --postgres-url "$DATABASE_URL" \
    --gcp-project "$GCP_PROJECT_ID" \
    --redis-url "$REDIS_URL"

# Verify
python3 scripts/verify_risk_scoring_setup.py \
    --postgres-url "$DATABASE_URL" \
    --redis-url "$REDIS_URL"
```

---

## Component Details

### 1. PostgreSQL Schema (12 Tables)

**Location**: `scripts/sql/01-risk_scoring-schema.sql`

**Creates**:
- Schema: `risk_scoring`
- 12 tables with full indexing and constraints
- JSONB columns for configuration
- SCD Type 2 for rule parameter versioning
- Immutable audit log

**Estimated Size**: 50MB (initial)

### 2. CBP Domain Configuration

**Location**: `scripts/sql/02-cbp-domain-init.sql`

**Initializes**:
- Domain: `cbp_illegal_transshipment`
- 7 Risk Factors
- 3 Sequential Gates
- 8 Rules with parameters
- Feature catalog

### 3. GCP Cloud Storage

**Bucket**: `gs://cbp-sentry-models`

**Structure**:
```
gs://cbp-sentry-models/
├── cbp/
│   ├── xgboost/              [XGBoost ensemble models]
│   ├── isolation_forest/     [Anomaly detection models]
│   ├── shap_explainer/       [Model interpretability]
│   ├── training_data/        [Training datasets]
│   └── evaluation_results/   [Metrics and reports]
```

### 4. Redis Cache

**Configuration**:
- Host: `localhost:6379` (or GCP Memorystore)
- TTL: 7 days (604800 seconds)
- Key Pattern: `risk_score:cbp:{entity_id}`
- Capacity: 1GB (starter), scales to 5GB+

---

## Detailed Deployment Instructions

### Step 1: PostgreSQL Setup

#### Local Development (Docker)

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Wait for startup
sleep 10

# Create database
docker exec postgres psql -U postgres -c "CREATE DATABASE cbp_sentry;"

# Verify
docker exec postgres psql -U postgres -d cbp_sentry -c "SELECT version();"
```

#### Cloud SQL (GCP)

```bash
# Create instance
gcloud sql instances create cbp-sentry-postgres \
    --database-version POSTGRES_14 \
    --tier db-g1-small \
    --region us-central1 \
    --availability-type REGIONAL

# Create database
gcloud sql databases create cbp_sentry \
    --instance cbp-sentry-postgres

# Create user
gcloud sql users create postgres \
    --instance cbp-sentry-postgres \
    --password

# Start Cloud SQL Proxy
cloud-sql-proxy cbp-sentry:us-central1:cbp-sentry-postgres &
```

### Step 2: Run Schema Creation

```bash
# Set connection URL
export DATABASE_URL="postgresql://postgres:password@localhost:5432/cbp_sentry"

# Execute setup
python3 scripts/setup_risk_scoring_infrastructure.py \
    --postgres-url "$DATABASE_URL" \
    --gcp-project cbp-sentry

# Expected output:
# PHASE 1: PostgreSQL Schema Setup
# → Connecting to PostgreSQL...
# ✓ Connected to PostgreSQL
# → Executing 01-risk_scoring-schema.sql...
# ✓ Executed 01-risk_scoring-schema.sql
# → Executing 02-cbp-domain-init.sql...
# ✓ Executed 02-cbp-domain-init.sql
# ✓ Schema created with 12 tables
```

### Step 3: GCP Setup

```bash
# Authenticate
gcloud auth login
gcloud config set project cbp-sentry

# Create storage bucket
gsutil mb -l us-central1 gs://cbp-sentry-models

# Set permissions
gsutil iam ch serviceAccount:app@cbp-sentry.iam.gserviceaccount.com:objectCreator \
    gs://cbp-sentry-models
```

### Step 4: Redis Setup

#### Local Development (Docker)

```bash
# Start Redis container
docker-compose up -d redis

# Test connection
redis-cli -u redis://localhost:6379 ping
# Expected: PONG
```

#### GCP Memorystore

```bash
# Create instance
gcloud redis instances create cbp-sentry-cache \
    --size 1 \
    --region us-central1 \
    --redis-version 6.0

# Get connection details
gcloud redis instances describe cbp-sentry-cache --region us-central1

# Update environment
export REDIS_URL="redis://10.0.0.3:6379"
```

### Step 5: Verification

```bash
# Run comprehensive verification
python3 scripts/verify_risk_scoring_setup.py \
    --postgres-url "$DATABASE_URL" \
    --redis-url "$REDIS_URL"

# Check PostgreSQL
psql "$DATABASE_URL" -c "
    SELECT COUNT(*) as table_count FROM information_schema.tables
    WHERE table_schema = 'risk_scoring';
"
# Expected: 12

# Check CBP domain
psql "$DATABASE_URL" -c "
    SELECT domain_id, name FROM risk_scoring.domains
    WHERE name = 'cbp_illegal_transshipment';
"
# Expected: domain_id | cbp_illegal_transshipment

# Check Redis
redis-cli -u "$REDIS_URL" keys "cache:config:*"
# Expected: cache:config:ttl_seconds, etc.
```

---

## Database Connection Strings

### Local Development
```
postgresql://postgres:postgres@localhost:5432/cbp_sentry
```

### Cloud SQL (with Proxy)
```
postgresql://postgres:PASSWORD@127.0.0.1:5432/cbp_sentry
```

### Cloud SQL (Direct)
```
postgresql://postgres:PASSWORD@35.x.x.x:5432/cbp_sentry
```

### Neon (Serverless)
```
postgresql://user:password@ep-xxxxx.us-east-1.aws.neon.tech/cbp_sentry
```

---

## Configuration Files

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://...
GCP_PROJECT_ID=cbp-sentry

# Optional
REDIS_URL=redis://localhost:6379
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
```

### Application Configuration

Update `api/core/config.py` or `.env` with:

```python
# PostgreSQL
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/cbp_sentry'
)

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
REDIS_TTL = 7 * 24 * 60 * 60  # 7 days

# GCP
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'cbp-sentry')
GCP_BUCKET = 'cbp-sentry-models'
```

---

## Troubleshooting

### PostgreSQL Connection Errors

```bash
# Test connection
psql -h localhost -U postgres -d cbp_sentry -c "SELECT 1;"

# Check logs
docker logs postgres

# Reset Docker
docker-compose down -v
docker-compose up -d postgres
```

### Schema Not Created

```bash
# Manual schema creation
psql "$DATABASE_URL" < scripts/sql/01-risk_scoring-schema.sql

# Check schema
psql "$DATABASE_URL" -c "\dn risk_scoring"
```

### Redis Connection Failed

```bash
# Test local Redis
redis-cli ping

# Test with URL
redis-cli -u redis://localhost:6379 ping

# Check memory
redis-cli info memory
```

### GCP Bucket Not Accessible

```bash
# Verify bucket exists
gsutil ls gs://cbp-sentry-models/

# Check service account
gcloud auth list

# Grant permissions
gsutil iam ch user:email@example.com:objectAdmin gs://cbp-sentry-models
```

---

## Monitoring

### PostgreSQL Health

```sql
-- Check active connections
SELECT count(*) as active_connections FROM pg_stat_activity;

-- Monitor table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname = 'risk_scoring';

-- Check index usage
SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'risk_scoring';
```

### Redis Health

```bash
# Monitor memory
redis-cli info memory

# Check key count
redis-cli dbsize

# Scan keys
redis-cli --scan --pattern "risk_score:*"
```

### GCP Bucket

```bash
# Check bucket size
gsutil du -s gs://cbp-sentry-models

# List objects
gsutil ls -r gs://cbp-sentry-models

# Monitor access logs
gsutil logging get gs://cbp-sentry-models
```

---

## Scaling Considerations

### PostgreSQL
- **Sharding**: Entity-based partitioning at 100M+ records
- **Replication**: Read replicas for analytics
- **Archival**: Move old records to cold storage (>1 year)

### Redis
- **Cluster Mode**: Multi-node for >5GB data
- **Persistence**: RDB snapshots for backup
- **Monitoring**: CloudWatch metrics for memory usage

### GCP Storage
- **Lifecycle**: Transition to Coldline after 90 days
- **Versioning**: Enable object versioning for rollback
- **Access Logs**: Monitor IAM and usage

---

## Rollback Procedures

### Drop Schema (Caution!)

```sql
-- Drop risk_scoring schema
DROP SCHEMA IF EXISTS risk_scoring CASCADE;

-- Verify
SELECT * FROM information_schema.schemata WHERE schema_name = 'risk_scoring';
```

### Clear Redis Cache

```bash
redis-cli -u "$REDIS_URL" FLUSHDB
```

### Delete GCP Bucket

```bash
gsutil -m rm -r gs://cbp-sentry-models
```

---

## Next Steps

1. **Model Training** — Train initial XGBoost and isolation forest models
2. **Inference API** — Implement `/api/v1/score` endpoint
3. **Feedback Collection** — Set up ground truth labeling interface
4. **Monitoring Dashboard** — Deploy Grafana for metrics
5. **Load Testing** — Validate performance under production load

---

## Support

For issues or questions:
- PostgreSQL: Check logs in `docker logs postgres`
- Redis: Check logs in `docker logs redis`
- GCP: Visit Cloud Console (console.cloud.google.com)

---

**Deployment Date**: June 12, 2026
**Status**: Ready for Implementation
