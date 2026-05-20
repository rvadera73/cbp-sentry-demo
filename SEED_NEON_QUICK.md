# Quick Neon Seeding - One Command

## Problem
Staging shows zero cases because Neon PostgreSQL database is empty.

## Solution
Use the Python seeding script to import data directly from local SQLite to Neon:

```bash
python3 scripts/seed_neon.py postgresql://neondb_owner:PASSWORD@HOST/neondb?sslmode=require
```

Or if you have DATABASE_URL set as environment variable:
```bash
python3 scripts/seed_neon.py
```

## What It Does
1. ✓ Reads local SQLite database (auto-seeded from Docker)
2. ✓ Connects to Neon PostgreSQL
3. ✓ Creates `shipments` table (if needed)
4. ✓ Imports 1,396 shipment records
5. ✓ Verifies import with count and risk distribution
6. ✓ Reports success/failure

## Prerequisites

### Option 1: Install psycopg2 (Recommended)
```bash
pip install psycopg2-binary
```

### Option 2: Use Local Docker Database
If psycopg2 not available, use SQL export method:
```bash
# Generate SQL file
./scripts/export_for_neon.sh

# Import into Neon
psql $DATABASE_URL < ./backups/cbp_sentry_neon_seed_*.sql
```

## Environment Variable
Set DATABASE_URL and script will use it:
```bash
export DATABASE_URL="postgresql://neondb_owner:PASSWORD@HOST/neondb?sslmode=require"
python3 scripts/seed_neon.py
```

## Output Example
```
→ Connecting to local SQLite: /app/data/cbp_sentry.db
✓ Extracted 1396 shipments from local SQLite
→ Connecting to Neon PostgreSQL...
✓ Connected to Neon
✓ Table 'shipments' ready (created or exists)
→ Importing 1396 shipments...
✓ Imported 100/1396 records
✓ Imported 200/1396 records
...
✓ Import complete!
  Total records: 1396
  High risk (>=70): 451
  Medium risk (50-70): 305
  Low risk (<50): 640

✓ Neon staging database is now seeded and ready!
```

## Where to Get DATABASE_URL
1. **From user memory**: Stored from IACP 2.1 project
2. **From GitHub Secrets**: Settings → Secrets and Variables → Actions
3. **From Neon Console**: https://console.neon.tech → Project → Connection String

## Example Connection String
```
postgresql://neondb_owner:npg_MsWUixB5V0yS@ep-square-art-apa1gid4-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

## Verify Success
After import:
```bash
# Connect to Neon
psql $DATABASE_URL

# Check record count
SELECT COUNT(*) FROM shipments;
# Should return: 1396

# View high-risk cases
SELECT id, shipper_name, risk_score 
FROM shipments 
WHERE risk_score >= 70 
ORDER BY risk_score DESC 
LIMIT 5;
```

## Next Step
Once seeded:
```bash
# Push to GitHub to trigger Cloud Run deployment
git push origin main

# Visit staging
https://sentry-ui-<HASH>.us-central1.run.app
# Dashboard should show 1,396 cases with scores
```

## Troubleshooting

**"psycopg2 not found"**
```bash
pip install psycopg2-binary
python3 scripts/seed_neon.py
```

**"Connection refused"**
- Check DATABASE_URL is correct
- Verify Neon instance is running
- Check network connectivity to Neon host

**"Table already exists"**
- Script will ask if you want to clear and reimport
- Answer `y` to overwrite or `n` to keep existing data

**"Import hangs"**
- Check Neon connection is stable
- Try SQL export method instead
- Reduce batch size in script

---

**File**: `scripts/seed_neon.py`  
**Status**: Ready to use  
**Dependencies**: psycopg2-binary (optional, SQL fallback available)
