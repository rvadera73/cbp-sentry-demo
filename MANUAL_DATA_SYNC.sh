#!/bin/bash
# Manual Data Sync to GCS for Staging Deployment
# Run this on your local machine with gcloud installed

set -e

PROJECT_ID="cbp-sentry"
BUCKET="gs://cbp-sentry-appdata"
REGION="us-central1"

echo "=========================================="
echo "Manual Data Sync to GCS"
echo "=========================================="
echo ""

# Step 1: Check gcloud
echo "Step 1: Verifying gcloud installation..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud not found. Please install:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo "✅ gcloud found"
echo ""

# Step 2: Authenticate
echo "Step 2: Authenticating to GCP..."
gcloud auth login --no-launch-browser || true
gcloud config set project $PROJECT_ID
echo "✅ Authenticated to project: $PROJECT_ID"
echo ""

# Step 3: Verify bucket exists
echo "Step 3: Checking GCS bucket..."
if ! gsutil ls $BUCKET > /dev/null 2>&1; then
    echo "❌ Bucket does not exist: $BUCKET"
    echo "   Creating bucket..."
    gsutil mb -p $PROJECT_ID -l $REGION $BUCKET
fi
echo "✅ Bucket exists: $BUCKET"
echo ""

# Step 4: Verify data files
echo "Step 4: Checking local data files..."
if [ ! -f "data/cbp_sentry.db" ]; then
    echo "❌ Missing: data/cbp_sentry.db"
    exit 1
fi
if [ ! -f "data/cord_rag.db" ]; then
    echo "❌ Missing: data/cord_rag.db"
    exit 1
fi
echo "✅ Found data/cbp_sentry.db ($(du -h data/cbp_sentry.db | cut -f1))"
echo "✅ Found data/cord_rag.db ($(du -h data/cord_rag.db | cut -f1))"
echo ""

# Step 5: Upload databases
echo "Step 5: Uploading databases to GCS..."
echo "   Uploading cbp_sentry.db..."
gsutil -m cp data/cbp_sentry.db $BUCKET/cbp_sentry.db
echo "   ✅ cbp_sentry.db uploaded"

echo "   Uploading cord_rag.db..."
gsutil -m cp data/cord_rag.db $BUCKET/cord_rag.db
echo "   ✅ cord_rag.db uploaded"
echo ""

# Step 6: Upload license if exists
echo "Step 6: Uploading senzing.license..."
if [ -f "senzing/senzing.license" ]; then
    gsutil cp senzing/senzing.license $BUCKET/senzing.license
    echo "   ✅ senzing.license uploaded"
else
    echo "   ⚠️  senzing.license not found (optional, skipping)"
fi
echo ""

# Step 7: Verify
echo "Step 7: Verifying uploads..."
echo "   Files in GCS bucket:"
gsutil ls -lh $BUCKET/
echo ""

# Final status
echo "=========================================="
echo "✅ DATA SYNC COMPLETE"
echo "=========================================="
echo ""
echo "Staging deployment will now have:"
echo "  • cbp_sentry.db with dev data"
echo "  • cord_rag.db with entity data"
echo "  • senzing.license (if present)"
echo ""
echo "Services will mount this data when deployed:"
echo "  • sentry-api: /app/data → cbp_sentry.db"
echo "  • sentry-data: /app/data → cbp_sentry.db"
echo "  • sentry-cord: /app/cord-data → cord_rag.db"
echo ""
echo "Continue with GitHub Actions deployment now."
