# Cloud Run Deployment Guide

**Target**: Deploy CBP Sentry to Google Cloud Run (staging/production)  
**Time**: ~30 minutes total (mostly automated)  
**Prerequisites**: 
- GCP project (cbp-sentry) created
- gcloud CLI installed and authenticated
- GitHub repo with write access

---

## Overview: 3-Step Deployment

```
1. GCP Bootstrap (15 min)  → Runs once per project
   ↓
2. Set GitHub Secrets (5 min) → Copy output from step 1
   ↓
3. Git Push to Deploy (5 min) → Automatic via GitHub Actions
   ↓
   Services live on Cloud Run
```

---

## Step 1: GCP Bootstrap (One-Time Setup)

Run the GCP bootstrap script to configure your Google Cloud project:

```bash
export GCP_PROJECT_ID=cbp-sentry
bash scripts/setup_gcp_staging.sh
```

This will:
- ✅ Enable required APIs (Cloud Run, SQL Admin, IAM, Secret Manager, Artifact Registry)
- ✅ Create Artifact Registry repo (`cbp-sentry`)
- ✅ Create 4 service accounts (api, data, ui, deploy)
- ✅ Set up Workload Identity Federation (GitHub Actions OIDC integration)
- ✅ Create Cloud SQL PostgreSQL instance (`sentry-staging`)
- ✅ Create secrets in Secret Manager
- ✅ Create VPC Connector for database access

**Watch for output at the end** — it prints GitHub Secrets you need to copy.

### Example Output

```
═══════════════════════════════════════════════════════════════
✅ GCP Bootstrap Complete!
═══════════════════════════════════════════════════════════════

Copy these values into GitHub Settings → Secrets:

GCP_PROJECT_ID
cbp-sentry

GCP_WORKLOAD_IDENTITY_PROVIDER
projects/1234567890/locations/us-central1/workloadIdentityPools/github-actions/providers/github

GCP_SERVICE_ACCOUNT_EMAIL
sentry-deploy@cbp-sentry.iam.gserviceaccount.com

[... more secrets ...]
```

---

## Step 2: Set GitHub Secrets

Go to your GitHub repository settings and add these secrets:

**Path**: https://github.com/rahulvadera/cbp-sentry/settings/secrets/actions

### Required Secrets (from Step 1 output)

| Secret | Value | From |
|---|---|---|
| `GCP_PROJECT_ID` | `cbp-sentry` | Script output |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/.../workloadIdentityPools/.../providers/github` | Script output |
| `GCP_SERVICE_ACCOUNT_EMAIL` | `sentry-deploy@cbp-sentry.iam.gserviceaccount.com` | Script output |
| `DATABASE_URL` | From Secret Manager | Script output |
| `VESSELAPI_KEY` | Your VesselAPI key (or placeholder) | Manual or script |
| `OFAC_API_KEY` | Your OFAC key (or placeholder) | Manual or script |

**Adding Secrets**:
1. Click "New repository secret"
2. Paste secret name (e.g., `GCP_PROJECT_ID`)
3. Paste value from script output
4. Click "Add secret"

Repeat for all 6 secrets.

### Note on API Keys
- `VESSELAPI_KEY` and `OFAC_API_KEY` can be placeholders initially
- They're only used if `API_MODE=live` (fixture mode works without real keys)
- Add real keys later when integrations are ready

---

## Step 3: Deploy via GitHub Actions

Deploy to staging or production by pushing code:

### Deploy to Staging
```bash
git push origin dev
# → GitHub Actions automatically builds, pushes image, deploys to Cloud Run
# → Monitoring: https://github.com/rahulvadera/cbp-sentry/actions
```

### Deploy to Production
```bash
git push origin main
# → GitHub Actions builds, pushes, deploys to prod (same process, different env)
```

**What happens automatically**:
1. GitHub Actions checks out code
2. Runs unit tests (pytest)
3. Builds Docker images for api, data, ui
4. Pushes to Artifact Registry
5. Deploys 3 services to Cloud Run:
   - `sentry-api` (port 8000)
   - `sentry-data` (port 8005)
   - `sentry-ui` (port 80)
6. Runs smoke tests (curl health checks)
7. Sends Slack notification (if configured)

### Monitor Deployment

**In GitHub**:
- https://github.com/rahulvadera/cbp-sentry/actions
- Click latest workflow run to see step-by-step progress

**In Google Cloud**:
```bash
# List deployed services
gcloud run services list --project cbp-sentry --region us-central1

# Watch a service
gcloud run services describe sentry-api --project cbp-sentry --region us-central1

# Stream logs
gcloud run services logs read sentry-api --project cbp-sentry --region us-central1 --limit 100
```

---

## Verify Deployment

### Quick Checks

```bash
# Get service URLs
gcloud run services list --project cbp-sentry --region us-central1 --format="table(name,status.url)"

# Test API health
curl -f https://sentry-api-[PROJECT].run.app/health

# Test UI availability
curl -f https://sentry-ui-[PROJECT].run.app/ > /dev/null && echo "✅ UI is up"
```

### Integration Tests (Against Staging)

```bash
# Set staging URL
export STAGING_API_URL="https://sentry-api-cbp-sentry.run.app"

# Run integration test suite
pytest -m integration services/api/tests/test_integration_staging.py -v

# Expected: All 15 tests pass
# - Health checks
# - Shipment CRUD
# - Score consistency
# - Manifest verification
```

---

## Troubleshooting Deployment

### "Artifact not found in Artifact Registry"
**Problem**: GitHub Actions couldn't push the Docker image  
**Solution**:
```bash
# Verify Artifact Registry exists
gcloud artifacts repositories describe cbp-sentry --location us-central1 --project cbp-sentry

# Check authentication in CI/CD
# GitHub Actions needs permission to push
# Already configured by setup_gcp_staging.sh
```

### "Cloud SQL database connection failed"
**Problem**: Cloud Run services can't reach database  
**Solution**:
```bash
# Verify VPC Connector exists
gcloud compute networks vpc-access connectors list --region us-central1 --project cbp-sentry

# Check Cloud SQL instance is running
gcloud sql instances describe sentry-staging --project cbp-sentry

# Verify service account has cloudsql.client role
gcloud projects get-iam-policy cbp-sentry \
  --flatten="bindings[].members" \
  --filter="bindings.members:sentry-api@cbp-sentry.iam.gserviceaccount.com"
```

### "Secret not found"
**Problem**: Cloud Run can't access secret  
**Solution**:
```bash
# List all secrets
gcloud secrets list --project cbp-sentry

# Check which service can access it
gcloud secrets get-iam-policy DATABASE_URL --project cbp-sentry
```

### "Permission denied" errors in Cloud Run logs
**Problem**: Service lacks permissions to call other services  
**Solution**:
```bash
# Re-run bootstrap (idempotent, won't delete anything)
bash scripts/setup_gcp_staging.sh

# Or manually grant permissions
gcloud projects add-iam-policy-binding cbp-sentry \
  --member="serviceAccount:sentry-api@cbp-sentry.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --quiet
```

---

## Costs

### Free Tier Usage (Monthly)
| Service | Limit | Cost |
|---|---|---|
| Cloud Run | 2M requests + 360K GB-seconds | Free |
| Cloud SQL | `db-f1-micro` micro instance + 30GB | Free tier |
| Artifact Registry | 0.5GB storage | Free tier |
| Secret Manager | 6 secrets | Free (up to 1M operations = ~$0) |
| VPC Connector | ~$0.10/hour = ~$7/month | Charged |

**Total monthly**: ~$7-10 for VPC Connector (optional, can remove if not using Cloud SQL)

### For Production
- Upgrade Cloud SQL to `db-n1-standard-2` for HA
- Scale up Cloud Run instances (currently min-1, max-100)
- These will incur standard GCP pricing

---

## Post-Deployment

### Enable Real Integrations

**VesselAPI** (AIS vessel tracking):
1. Subscribe at https://vesselapi.com
2. Get API key
3. Update GitHub secret: `VESSELAPI_KEY=your-key`
4. Set `API_MODE=live` in Cloud Run env vars
5. Redeploy (git push origin dev)

**OFAC SDN List** (sanctions screening):
1. Get API key from Treasury Department
2. Update GitHub secret: `OFAC_API_KEY=your-key`
3. Redeploy

**Senzing** (entity resolution):
1. Get Senzing license from senzing.com
2. Create secret: `SENZING_LICENSE`
3. Update docker-compose to mount license
4. Rebuild and redeploy

### Monitoring

Set up alerts in Google Cloud:
```bash
# CPU usage alert
gcloud alpha monitoring policies create \
  --display-name="Cloud Run CPU High" \
  --condition-display-name="sentry-api CPU > 80%" \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --project cbp-sentry
```

### Scaling

Monitor and adjust:
```bash
# Current settings (from deploy.yml):
# - API: 2GB mem, 2CPU, min-1, max-100 instances
# - Data: 1GB mem, 1CPU, min-1, max-100 instances
# - UI: 512MB mem, 0.5CPU, min-1, max-100 instances

# Update if needed
gcloud run services update sentry-api \
  --memory 4Gi \
  --cpu 4 \
  --min-instances 2 \
  --max-instances 50 \
  --project cbp-sentry \
  --region us-central1
```

---

## Rollback

If a deployment fails:

```bash
# Revert to previous image version
gcloud run services update sentry-api \
  --image gcr.io/cbp-sentry/cbp-sentry/sentry-api:previous-sha \
  --project cbp-sentry \
  --region us-central1

# Or just re-run the pipeline on a known-good commit
git push origin main~1:main  # Push previous commit
# GitHub Actions will auto-deploy the previous version
```

---

## Next Steps

1. ✅ Run `bash scripts/setup_gcp_staging.sh`
2. ✅ Add GitHub Secrets
3. ✅ Push to dev branch
4. ✅ Monitor GitHub Actions workflow
5. ✅ Run integration tests against staging
6. ✅ Promote to production (push to main)

---

## Additional Resources

- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **Workload Identity**: https://cloud.google.com/iam/docs/workload-identity
- **GitHub Actions**: https://docs.github.com/en/actions
- **Project Architecture**: docs/ARCHITECTURE.md
- **Integration Status**: docs/INTEGRATION_STATUS.md
