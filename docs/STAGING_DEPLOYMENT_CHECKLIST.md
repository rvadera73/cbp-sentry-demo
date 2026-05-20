# CBP Sentry Staging Deployment Checklist

**Goal**: Deploy CBP Sentry to Google Cloud Run (staging)  
**Database**: Neon PostgreSQL (free tier, like IACP-2.1)  
**Time**: 30 minutes total  
**Status**: 🟡 Ready to execute

---

## Pre-Deployment: Create Neon Database

### 1. Create Neon Project (5 minutes)

1. Go to https://console.neon.tech
2. Sign up or log in
3. Click "Create project"
4. **Project name**: `cbp-sentry-staging`
5. **Region**: US East (us-east-2, matches IACP-2.1)
6. **Database**: postgres
7. Click "Create project"

### 2. Copy Connection String (2 minutes)

After project creation:
1. Click "Databases" in left sidebar
2. Select the default database (usually `neondb`)
3. Click "Connection string" button
4. Select "Pooled connection"
5. Copy the full URL (looks like):
   ```
   postgresql://user:password@ep-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

**Important**: Keep this URL safe — you'll need it for GitHub Secrets

### 3. Customize for CBP Sentry (Optional)

If you want a dedicated database:
1. In Neon console, click "Databases"
2. Click "Create database"
3. Name: `cbp_sentry`
4. Copy the connection string (will be similar URL, different database name)

---

## GCP Setup via Google Console (15 minutes)

If you have browser access to Google Console (no gcloud CLI):

1. Go to **https://console.cloud.google.com**
2. Select project: **cbp-sentry**
3. Create service account (IAM & Admin → Service Accounts):
   - Name: `sentry-deploy`
   - Roles: Cloud Run Admin, Artifact Registry Admin, Service Account User
   - **Copy the email address** (format: `sentry-deploy@cbp-sentry.iam.gserviceaccount.com`)

4. Create Artifact Registry (Artifact Registry → Create Repository):
   - Name: `cbp-sentry`
   - Format: Docker
   - Region: `us-central1`

5. Create Workload Identity Federation (IAM & Admin → Workload Identity Federation):
   - Pool name: `github-actions`
   - Provider type: OpenID Connect (OIDC)
   - Provider ID: `github`
   - Issuer URL: `https://token.actions.githubusercontent.com`
   - Attribute mapping:
     ```
     google.subject=assertion.sub
     attribute.repository=assertion.repository
     attribute.environment=assertion.environment
     ```
   - **Copy the provider resource name** (format: `projects/XXX/locations/us-central1/workloadIdentityPools/github-actions/providers/github`)

6. Enable APIs: Cloud Run, Artifact Registry, Cloud SQL Admin, IAM, Service Usage

**Keep these values handy** — you'll need them for GitHub Secrets in the next step.

---

## GitHub Secrets Setup (5 minutes)

Go to: https://github.com/rahulvadera/cbp-sentry/settings/secrets/actions

### Add These 6 Secrets

| Secret Name | Value | Source |
|---|---|---|
| `GCP_PROJECT_ID` | `cbp-sentry` | GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/XXX/locations/us-central1/workloadIdentityPools/github-actions/providers/github` | From GCP Console (Step 2.3) |
| `GCP_SERVICE_ACCOUNT_EMAIL` | `sentry-deploy@cbp-sentry.iam.gserviceaccount.com` | From GCP Console (Step 2.1) |
| `DATABASE_URL` | `postgresql://neondb_owner:npg_MsWUixB5V0yS@ep-square-art-apa1gid4-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require` | Neon database (already have) |
| `VESSELAPI_KEY` | `placeholder-key` | Update with real key later |
| `OFAC_API_KEY` | `placeholder-key` | Update with real key later |

**Steps to add each**:
1. Click "New repository secret"
2. Paste secret name
3. Paste value
4. Click "Add secret"

---

## Deploy to Staging (5 minutes)

Push code to trigger automatic deployment:

```bash
cd ~/cbp-sentry
git status  # Should be clean (all committed)
git push origin dev
```

**What happens automatically**:
1. GitHub Actions checks out code
2. Runs unit tests
3. Builds Docker images (api, data, ui)
4. Pushes to Artifact Registry
5. Deploys 3 services to Cloud Run
6. Runs smoke tests
7. Shows results in GitHub Actions

**Monitor**: https://github.com/rahulvadera/cbp-sentry/actions

---

## Verify Deployment (5 minutes)

### Check Cloud Run Services

```bash
gcloud run services list --project cbp-sentry --region us-central1 --format="table(name,status.url)"
```

Expected output:
```
NAME         STATUS.URL
sentry-api   https://sentry-api-cbp-sentry.run.app
sentry-data  https://sentry-data-cbp-sentry.run.app
sentry-ui    https://sentry-ui-cbp-sentry.run.app
```

### Test API Health

```bash
curl -f https://sentry-api-cbp-sentry.run.app/health
# Should return: {"status": "healthy", "service": "sentry-api"}
```

### Run Integration Tests

```bash
export STAGING_API_URL="https://sentry-api-cbp-sentry.run.app"
pytest -m integration services/api/tests/test_integration_staging.py -v

# Expected: All 15 tests pass
```

### Open Dashboard

```bash
open https://sentry-ui-cbp-sentry.run.app
# OR manually: https://sentry-ui-cbp-sentry.run.app
```

Should see:
- 1,191 cases loaded from manifest
- Cases sorted by risk score
- Clickable case details with H1/H2 scoring

---

## Summary: Ready to Go

✅ **Local development**: Works (docker-compose + SQLite)  
✅ **Tests**: Pass locally and in CI/CD  
✅ **Docker images**: Build automatically on every push  
✅ **Cloud infrastructure**: Created by setup_gcp_staging.sh  
✅ **GitHub Actions**: Configured in .github/workflows/deploy.yml  
✅ **OIDC authentication**: Configured (no static keys)  
✅ **Database**: Neon PostgreSQL (free tier)  

**Next step**: Create Neon database and add GitHub Secrets → push to dev → deploy!

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Developer: git push origin dev                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ GitHub Actions Workflow (.github/workflows/deploy.yml)      │
│ • Checkout code                                             │
│ • Run pytest                                                │
│ • Build Docker images                                       │
│ • Push to Artifact Registry (gcr.io)                       │
│ • Deploy 3 services to Cloud Run                           │
│ • Run smoke tests                                           │
└────────┬──────────────────────────────────┬──────────────────┘
         │                                  │
         ▼                                  ▼
┌──────────────────────────┐  ┌────────────────────────────┐
│ Artifact Registry        │  │ Cloud Run Services         │
│ gcr.io/cbp-sentry/...   │  │ • sentry-api:8000         │
│ • sentry-api:SHA        │  │ • sentry-data:8005        │
│ • sentry-data:SHA       │  │ • sentry-ui:80            │
│ • sentry-ui:SHA         │  │                            │
└──────────────────────────┘  └────────┬───────────────────┘
                                       │
                                       ▼
                              ┌─────────────────────┐
                              │ Neon PostgreSQL     │
                              │ cbp_sentry database │
                              └─────────────────────┘
```

---

## Troubleshooting

### "GitHub Actions deploy failed"
1. Check https://github.com/rahulvadera/cbp-sentry/actions
2. Click failed workflow → see error message
3. Common issues:
   - Missing GitHub Secrets → Add all 6
   - Invalid DATABASE_URL → Check Neon connection string format
   - gcloud auth failed → Verify OIDC provider URL matches exactly

### "Database connection failed"
1. Verify DATABASE_URL in GitHub Secrets is correct
2. Test locally:
   ```bash
   psql "postgresql://user:pass@ep-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
   # Should connect successfully
   ```
3. Check Cloud Run logs:
   ```bash
   gcloud run services logs read sentry-data --region us-central1 --limit 50
   ```

### "Services not responding"
1. Check Cloud Run health:
   ```bash
   gcloud run services describe sentry-api --region us-central1 --format=json | jq .status.conditions
   ```
2. Check if image deployed correctly:
   ```bash
   gcloud run services describe sentry-api --region us-central1 --format='value(spec.template.spec.containers[0].image)'
   ```

---

## Next Steps After Successful Deploy

1. ✅ Verify all 3 services are running
2. ✅ Run integration test suite
3. ✅ Open dashboard and explore cases
4. ✅ Test entity resolution (Senzing)
5. ✅ Share staging URL with team

---

## Post-Deployment: Production Promotion

When ready to promote to production:

```bash
git push origin main
# → Deploys to production (same infrastructure, prod settings)
```

Production differences (will be auto-configured):
- Separate GCP project or namespace
- Cloud SQL instead of Neon (larger instance)
- Higher resource limits
- More monitoring and alerting

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `bash scripts/setup_gcp_staging.sh` | One-time GCP setup |
| `git push origin dev` | Deploy to staging (automatic) |
| `git push origin main` | Deploy to production (automatic) |
| `gcloud run services list --project cbp-sentry --region us-central1` | List deployed services |
| `curl https://sentry-api-cbp-sentry.run.app/health` | Check API health |
| `gcloud run services logs read sentry-api --region us-central1 --limit 100` | View service logs |

---

**Status**: 🟢 Ready to deploy  
**Estimated Time to Live**: 30 minutes  
**Zero-trust Security**: ✅ OIDC, no static keys  
**Serverless**: ✅ Cloud Run + Neon PostgreSQL (both auto-scaling)
