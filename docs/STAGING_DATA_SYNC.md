# Staging Data Sync — Copy Dev Data to GCS Bucket

**Goal:** Ensure staging deployment has same data as dev environment

---

## 📊 Data Files to Sync

```
Local Dev Data:
  ✓ data/cbp_sentry.db        (15M) - Main application database
  ✓ data/cord_rag.db          (19M) - CORD entity resolution database
  ✓ senzing/senzing.license   (0.2K) - Senzing license

GCS Bucket (used by Cloud Run):
  gs://cbp-sentry-appdata/    - Shared storage for all services
    ├── cbp_sentry.db         (mounted to /app/data)
    ├── cord_rag.db           (mounted to /app/cord-data)
    └── senzing.license       (for optional Senzing service)
```

---

## 🔄 Sync Process (Before Deploying Stage)

### Option 1: Manual Sync (Recommended for first time)

**Step 1: Authenticate to GCP**
```bash
gcloud auth login
gcloud config set project cbp-sentry
```

**Step 2: Upload data to GCS bucket**
```bash
# Upload cbp_sentry.db
gsutil cp /home/rahulvadera/cbp-sentry/data/cbp_sentry.db \
  gs://cbp-sentry-appdata/cbp_sentry.db

# Upload cord_rag.db  
gsutil cp /home/rahulvadera/cbp-sentry/data/cord_rag.db \
  gs://cbp-sentry-appdata/cord_rag.db

# Upload senzing license (if using Senzing)
gsutil cp /home/rahulvadera/cbp-sentry/senzing/senzing.license \
  gs://cbp-sentry-appdata/senzing.license
```

**Step 3: Verify uploads**
```bash
gsutil ls -lh gs://cbp-sentry-appdata/

# Should show:
#  15M  2026-05-26T...  gs://cbp-sentry-appdata/cbp_sentry.db
#  19M  2026-05-26T...  gs://cbp-sentry-appdata/cord_rag.db
# 0.2K  2026-05-26T...  gs://cbp-sentry-appdata/senzing.license
```

---

### Option 2: Automated Sync (Add to GitHub Actions)

**Add to deploy.yml before bootstrap-bucket job:**

```yaml
  sync-data:
    name: Sync Dev Data to GCS
    runs-on: ubuntu-latest
    needs: [setup]
    if: github.event_name == 'push' && github.ref == 'refs/heads/stage'
    steps:
      - uses: actions/checkout@v4
      
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - uses: google-github-actions/setup-gcloud@v2
      
      - name: Upload databases to GCS
        run: |
          echo "Uploading cbp_sentry.db..."
          gsutil cp data/cbp_sentry.db gs://cbp-sentry-appdata/cbp_sentry.db
          
          echo "Uploading cord_rag.db..."
          gsutil cp data/cord_rag.db gs://cbp-sentry-appdata/cord_rag.db
          
          echo "Uploading senzing.license..."
          gsutil cp senzing/senzing.license gs://cbp-sentry-appdata/senzing.license || true
          
          echo "✅ Data sync complete"
          gsutil ls -lh gs://cbp-sentry-appdata/
```

---

## 🔐 Permissions Required

**GCP Service Account needs:**
- `roles/storage.objectAdmin` on `gs://cbp-sentry-appdata` bucket
- Already granted by bootstrap-bucket job in deploy.yml (line 110-117)

---

## 📋 Data Sync Checklist

Before deploying stage:

- [ ] Local dev data is up-to-date
  ```bash
  ls -lh /home/rahulvadera/cbp-sentry/data/
  # Should show recent cbp_sentry.db and cord_rag.db
  ```

- [ ] GCS bucket exists
  ```bash
  gcloud run services list --region us-central1
  # Verify services are deployed with appdata bucket
  ```

- [ ] Data uploaded to GCS
  ```bash
  gsutil ls -lh gs://cbp-sentry-appdata/
  # Should show cbp_sentry.db and cord_rag.db
  ```

- [ ] Stage branch deployment in progress
  ```
  GitHub Actions → Deploy — Sentry (Cloud Run) → stage branch
  ```

- [ ] Services mounted to data
  ```
  Services will automatically mount:
    gs://cbp-sentry-appdata/ → /app/data (API, Data service)
    gs://cbp-sentry-appdata/ → /app/cord-data (CORD service)
  ```

---

## ✅ After Deployment

**Verify data loaded in Cloud Run services:**

```bash
# Check API can access data
curl https://sentry-api.run.app/api/shipments?limit=5

# Should return shipment data from cbp_sentry.db

# Check CORD service
curl https://sentry-cord-integration.run.app/health

# Should respond with health status
```

---

## 🔄 Keep Syncing During Testing

If you make changes to local dev data and want to test in staging:

```bash
# After updating local data
gsutil cp data/cbp_sentry.db gs://cbp-sentry-appdata/cbp_sentry.db

# Services will pick up new data on next restart
# Or manually restart Cloud Run services:
gcloud run services update sentry-api --region us-central1 \
  --platform managed --no-traffic-split
```

---

## 📝 Summary

| Item | Status |
|------|--------|
| **4 Services** | ✅ All deployed (api, data, cord, ui) |
| **GCS Bucket** | ✅ Created and configured |
| **Data Upload** | ⏳ Manual OR automated in GitHub Actions |
| **Data Sync** | Do this BEFORE pushing stage branch |
| **Verification** | After deployment, test API endpoints |

---

## 🚀 Quick Command

**One-liner to sync all data:**
```bash
gsutil -m cp /home/rahulvadera/cbp-sentry/data/*.db gs://cbp-sentry-appdata/ && \
gsutil cp /home/rahulvadera/cbp-sentry/senzing/senzing.license gs://cbp-sentry-appdata/ || true && \
echo "✅ Data synced to staging"
```

