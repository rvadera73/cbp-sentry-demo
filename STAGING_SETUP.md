# CBP Sentry - Staging Database Setup (Neon PostgreSQL)

## Problem

Staging deployment shows **zero cases** because the database is empty. The sentry-data service auto-seeds from SQLite locally, but staging uses Neon PostgreSQL which requires explicit data import.

## Solution

### Step 1: Generate SQL Export from Local Database

Run the export script (already done):
```bash
./scripts/export_for_neon.sh
```

Output file:
```
/home/rahulvadera/cbp-sentry/backups/cbp_sentry_neon_seed_YYYYMMDD_HHMMSS.sql
```

This contains:
- 1,396 shipment records (full manifest data)
- High-risk cases: Greenfield (91), Solaria (65)
- Medium-risk cases: various origins/commodities
- Low-risk decoy shipments: 18-29 scores
- Complete INSERT statements ready for PostgreSQL

### Step 2: Import into Neon Staging

**Option A: Command-line (psql)**

```bash
# Export your Neon connection string
export DATABASE_URL="postgresql://neondb_owner:...@ep-....c.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Import the SQL file
psql $DATABASE_URL < ./backups/cbp_sentry_neon_seed_*.sql

# Verify
psql $DATABASE_URL -c "SELECT COUNT(*) as total, MAX(risk_score) as max_risk FROM shipments;"
```

**Option B: Neon Console Web UI**

1. Go to https://console.neon.tech
2. Open your `cbp-sentry` project
3. Click "SQL Editor"
4. Paste the contents of `cbp_sentry_neon_seed_*.sql`
5. Execute

**Option C: GitHub Actions**

The deployment script will automatically:
1. Extract DATABASE_URL from Secret Manager
2. Run the import script
3. Verify data loaded
4. Restart sentry-data service

### Step 3: Verify Import

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

## Next Steps

1. **Immediate**: Run import to seed staging database
2. **Verify**: Visit staging UI and check dashboard shows cases
3. **Test**: Select a high-risk case (Greenfield, score 91) to verify detail view works
4. **Enhance**: Update sentry-data to natively support PostgreSQL (no SQL workaround needed)

## Files

- **Export script**: `scripts/export_for_neon.sh`
- **SQL export**: `backups/cbp_sentry_neon_seed_YYYYMMDD_HHMMSS.sql`
- **Setup**: This file (`STAGING_SETUP.md`)
- **Local status**: `LOCAL_DEPLOYMENT_STATUS.md`
