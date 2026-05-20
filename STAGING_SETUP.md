# CBP Sentry - Staging Database Setup (Neon PostgreSQL)

## Problem

Staging deployment shows **zero cases** because the database is empty. The sentry-data service auto-seeds from SQLite locally, but staging uses Neon PostgreSQL which requires explicit data import.

**IMPORTANT**: Database seeding should happen **BEFORE** deployment starts (not during CI/CD), so the services start with data already loaded.

## Solution

### Step 1: Seed Neon Database (Before Deployment)

Use the Python seeding script:

```bash
# Option 1: Pass connection string as argument
python3 scripts/seed_neon.py postgresql://neondb_owner:PASSWORD@HOST/neondb?sslmode=require

# Option 2: Use DATABASE_URL environment variable
export DATABASE_URL="postgresql://neondb_owner:PASSWORD@HOST/neondb?sslmode=require"
python3 scripts/seed_neon.py
```

**What it does:**
- ✓ Reads local SQLite database (1,396 records)
- ✓ Connects to Neon PostgreSQL
- ✓ Creates shipments table (if needed)
- ✓ Imports all records in batches
- ✓ Verifies import succeeded
- ✓ Shows risk distribution (high/medium/low)

**Installation (if needed):**
```bash
pip install psycopg2-binary
```

### Alternate: SQL Export Method

If psycopg2 not available:

```bash
# Generate SQL file
./scripts/export_for_neon.sh

# Import using psql
psql $DATABASE_URL < ./backups/cbp_sentry_neon_seed_*.sql
```

### Step 2: Verify Import Succeeded

Check sample high-risk cases:
```bash
SELECT id, shipper_name, origin_country, destination_country, risk_score
FROM shipments
WHERE risk_score >= 70
ORDER BY risk_score DESC
LIMIT 5;
```

Expected result:
```
id                    | shipper_name                      | origin_country | destination_country | risk_score
shipment-greenfield-001 | Greenfield Industrial Trading Co. | VN | US | 91
shipment-solaria-001     | Solaria Manufacturing Sdn. Bhd.   | MY | US | 65
(+ more high-risk cases)
```

Count by risk level:
```bash
SELECT
    COUNT(CASE WHEN risk_score >= 70 THEN 1 END) as high_risk,
    COUNT(CASE WHEN risk_score >= 50 AND risk_score < 70 THEN 1 END) as medium_risk,
    COUNT(CASE WHEN risk_score < 50 THEN 1 END) as low_risk
FROM shipments;
```

Expected:
```
high_risk | medium_risk | low_risk
    ~450  |     ~300    |  ~650
```

## Architecture: Local vs Staging

### Local (Docker Compose)
- **Database**: SQLite at `/app/data/cbp_sentry.db`
- **Auto-seed**: `seed_demo_data()` runs on sentry-data startup
- **Source**: `services/data/seed_data/manifest_feb_march_2026_with_isf.json`

### Staging (Cloud Run + Neon)
- **Database**: Neon PostgreSQL (managed, serverless)
- **Connection**: `DATABASE_URL` environment variable
- **Auto-seed**: SQL import (this document)
- **Source**: `backups/cbp_sentry_neon_seed_*.sql`

## Implementation Note

The sentry-data service (`services/data/db.py`) is currently SQLite-only. To fully support PostgreSQL in staging:

**Future Enhancement**: Update db.py to detect DATABASE_URL and use appropriate driver:
```python
import os
import sqlite3

db_url = os.getenv('DATABASE_URL')
if db_url and 'postgresql' in db_url:
    # Use PostgreSQL
    import psycopg2
    conn = psycopg2.connect(db_url)
else:
    # Use SQLite (default)
    conn = sqlite3.connect('/app/data/cbp_sentry.db')
```

For now, data import via SQL script is the workaround.

## Troubleshooting

### Dashboard Shows "Case Not Found"
**Symptom**: Cases show in list but error when selecting  
**Cause**: Database not seeded in staging  
**Fix**: Run import steps above

### API Returns Empty List
**Symptom**: `curl https://sentry-api-<HASH>.run.app/api/shipments` returns `{"shipments": []}`  
**Cause**: sentry-data connected to empty Neon database  
**Fix**: Verify import succeeded with step 3 verification query

### Connection Refused
**Symptom**: `psql` command fails with "connection refused"  
**Cause**: DATABASE_URL environment variable not set or incorrect  
**Fix**: Check GitHub Secrets in Settings → Secrets and Variables → Actions

```bash
# Verify Neon connection
echo $DATABASE_URL
# Should output: postgresql://user:pass@host/db...

# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

### Import Hangs or Times Out
**Symptom**: SQL import doesn't complete in reasonable time  
**Cause**: Neon connection issues or large file size  
**Fix**:
1. Use smaller import (first 100 records only for testing)
2. Import via Neon console UI instead
3. Check network connectivity
4. Split import into multiple batches

## Proper Deployment Flow

**BEFORE Pushing Code:**
1. ✓ Run seeding script: `python3 scripts/seed_neon.py`
2. ✓ Verify import: Check record count, high-risk cases visible
3. ✓ Commit code: `git add` and `git commit`

**Then Deploy:**
4. Push code: `git push origin main`
5. GitHub Actions will:
   - Build Docker images
   - Push to Artifact Registry  
   - Deploy to Cloud Run
   - Run smoke tests
6. Verify: Visit `https://sentry-ui-<HASH>.us-central1.run.app`
7. Test: Dashboard should show 1,396 cases, select Greenfield (91) to verify detail

**DO NOT:**
- ❌ Seed database during GitHub Actions pipeline
- ❌ Add seeding commands to .github/workflows/deploy.yml
- ❌ Rely on auto-seeding in staging (only works in local SQLite)

## Future Enhancement

Update sentry-data/db.py to natively support PostgreSQL (no SQL workaround needed):
```python
import os
db_url = os.getenv('DATABASE_URL')
if 'postgresql' in db_url:
    # Use PostgreSQL driver
else:
    # Use SQLite (local)

## Files

- **Export script**: `scripts/export_for_neon.sh`
- **SQL export**: `backups/cbp_sentry_neon_seed_YYYYMMDD_HHMMSS.sql`
- **Setup**: This file (`STAGING_SETUP.md`)
- **Local status**: `LOCAL_DEPLOYMENT_STATUS.md`
