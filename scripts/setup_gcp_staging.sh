#!/bin/bash
# GCP Bootstrap Script for CBP Sentry Staging Deployment
#
# One-time setup script that configures Google Cloud for Cloud Run deployment.
# Creates all necessary service accounts, IAM bindings, Artifact Registry, and Secrets.
#
# Usage:
#   bash scripts/setup_gcp_staging.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Owner/Editor role on target GCP project
#   - PROJECT_ID set in .env.local or as environment variable
#
# Output:
#   - Prints GitHub Secrets values to copy into https://github.com/.../settings/secrets
#   - Creates GCP project structure (will be idempotent if run again)

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 CBP Sentry GCP Bootstrap"
echo "=================================="
echo ""

# Load project ID from environment or .env file
if [ -z "$GCP_PROJECT_ID" ]; then
    if [ -f .env.local ]; then
        export $(grep GCP_PROJECT_ID .env.local | xargs)
    fi
fi

if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}ERROR: GCP_PROJECT_ID not set${NC}"
    echo "Set in .env.local or: export GCP_PROJECT_ID=cbp-sentry"
    exit 1
fi

PROJECT_ID="$GCP_PROJECT_ID"
GCP_REGION="us-central1"
ARTIFACT_REGISTRY_REPO="cbp-sentry"

echo -e "${GREEN}✓${NC} Project ID: $PROJECT_ID"
echo -e "${GREEN}✓${NC} Region: $GCP_REGION"
echo ""

# ============================================================================
# 1. Enable Required APIs
# ============================================================================
echo "1️⃣  Enabling required Google Cloud APIs..."

gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    compute.googleapis.com \
    artifactregistry.googleapis.com \
    iam.googleapis.com \
    secretmanager.googleapis.com \
    iap.googleapis.com \
    cloudresourcemanager.googleapis.com \
    sts.googleapis.com \
    --project "$PROJECT_ID" \
    --quiet

echo -e "${GREEN}✓${NC} APIs enabled"
echo ""

# ============================================================================
# 2. Create Artifact Registry Repository
# ============================================================================
echo "2️⃣  Creating Artifact Registry repository..."

if gcloud artifacts repositories describe "$ARTIFACT_REGISTRY_REPO" \
    --location "$GCP_REGION" \
    --project "$PROJECT_ID" \
    2>/dev/null; then
    echo -e "${GREEN}✓${NC} Artifact Registry repo already exists"
else
    gcloud artifacts repositories create "$ARTIFACT_REGISTRY_REPO" \
        --repository-format docker \
        --location "$GCP_REGION" \
        --project "$PROJECT_ID" \
        --quiet
    echo -e "${GREEN}✓${NC} Artifact Registry repo created"
fi

ARTIFACT_REGISTRY="${GCP_REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}"
echo ""

# ============================================================================
# 3. Create Service Accounts
# ============================================================================
echo "3️⃣  Creating service accounts..."

create_service_account() {
    local name=$1
    local display_name=$2

    if gcloud iam service-accounts describe "${name}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --project "$PROJECT_ID" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Service account $name already exists"
    else
        gcloud iam service-accounts create "$name" \
            --display-name "$display_name" \
            --project "$PROJECT_ID" \
            --quiet
        echo -e "${GREEN}✓${NC} Created service account: $name"
    fi
}

create_service_account "sentry-api" "Sentry API Cloud Run service"
create_service_account "sentry-data" "Sentry Data Cloud Run service"
create_service_account "sentry-ui" "Sentry UI Cloud Run service"
create_service_account "sentry-deploy" "GitHub Actions deployment service"

echo ""

# ============================================================================
# 4. Set IAM Bindings
# ============================================================================
echo "4️⃣  Setting IAM bindings..."

grant_role() {
    local service_account=$1
    local role=$2

    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member "serviceAccount:${service_account}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role "$role" \
        --quiet 2>/dev/null || true
}

# Cloud Run roles
grant_role "sentry-api" "roles/run.developer"
grant_role "sentry-data" "roles/run.developer"
grant_role "sentry-ui" "roles/run.developer"

# Secret Manager access (for reading secrets)
grant_role "sentry-api" "roles/secretmanager.secretAccessor"
grant_role "sentry-data" "roles/secretmanager.secretAccessor"

# Cloud SQL client (for database access)
grant_role "sentry-api" "roles/cloudsql.client"
grant_role "sentry-data" "roles/cloudsql.client"

# Artifact Registry reader (to pull images)
grant_role "sentry-api" "roles/artifactregistry.reader"
grant_role "sentry-data" "roles/artifactregistry.reader"
grant_role "sentry-ui" "roles/artifactregistry.reader"

# GitHub Actions deployment service
grant_role "sentry-deploy" "roles/run.admin"
grant_role "sentry-deploy" "roles/artifactregistry.admin"
grant_role "sentry-deploy" "roles/iam.serviceAccountUser"

echo -e "${GREEN}✓${NC} IAM bindings configured"
echo ""

# ============================================================================
# 5. Set Up Workload Identity Federation
# ============================================================================
echo "5️⃣  Setting up Workload Identity Federation (GitHub Actions OIDC)..."

WIF_POOL="github-actions"
WIF_PROVIDER="github"
WIF_POOL_ID="${PROJECT_ID}/${GCP_REGION}/${WIF_POOL}"

# Create Workload Identity Pool
if gcloud iam workload-identity-pools describe "$WIF_POOL" \
    --location="$GCP_REGION" \
    --project="$PROJECT_ID" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Workload Identity Pool already exists"
else
    gcloud iam workload-identity-pools create "$WIF_POOL" \
        --project="$PROJECT_ID" \
        --location="$GCP_REGION" \
        --display-name="GitHub Actions" \
        --quiet
    echo -e "${GREEN}✓${NC} Created Workload Identity Pool"
fi

# Create Workload Identity Provider
if gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER" \
    --workload-identity-pool="$WIF_POOL" \
    --location="$GCP_REGION" \
    --project="$PROJECT_ID" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Workload Identity Provider already exists"
else
    gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
        --project="$PROJECT_ID" \
        --location="$GCP_REGION" \
        --workload-identity-pool="$WIF_POOL" \
        --display-name="GitHub" \
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.environment=assertion.environment" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --quiet
    echo -e "${GREEN}✓${NC} Created Workload Identity Provider"
fi

# Get the Workload Identity Provider resource name
WIP_RESOURCE="projects/${PROJECT_ID}/locations/${GCP_REGION}/workloadIdentityPools/${WIF_POOL}/providers/${WIF_PROVIDER}"

# Bind GitHub Actions to service account
GITHUB_REPO="rahulvadera/cbp-sentry"
GITHUB_REPO_UPPER=$(echo "$GITHUB_REPO" | tr '/' ':')

gcloud iam service-accounts add-iam-policy-binding \
    "sentry-deploy@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${WIP_RESOURCE}/attribute.repository/${GITHUB_REPO}" \
    --quiet 2>/dev/null || true

echo -e "${GREEN}✓${NC} Workload Identity Federation configured"
echo ""

# ============================================================================
# 6. Create Cloud SQL PostgreSQL Instance (Staging)
# ============================================================================
echo "6️⃣  Creating Cloud SQL PostgreSQL instance..."

SQL_INSTANCE="sentry-staging"

if gcloud sql instances describe "$SQL_INSTANCE" --project="$PROJECT_ID" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Cloud SQL instance already exists"
    SQL_IP=$(gcloud sql instances describe "$SQL_INSTANCE" \
        --project="$PROJECT_ID" \
        --format='value(ipAddresses[0].ipAddress)')
else
    gcloud sql instances create "$SQL_INSTANCE" \
        --project="$PROJECT_ID" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region="$GCP_REGION" \
        --network=default \
        --enable-bin-log \
        --backup-start-time=03:00 \
        --quiet
    echo -e "${GREEN}✓${NC} Cloud SQL instance created"

    SQL_IP=$(gcloud sql instances describe "$SQL_INSTANCE" \
        --project="$PROJECT_ID" \
        --format='value(ipAddresses[0].ipAddress)')
fi

# Create database
if gcloud sql databases describe cbp_sentry \
    --instance="$SQL_INSTANCE" \
    --project="$PROJECT_ID" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Database already exists"
else
    gcloud sql databases create cbp_sentry \
        --instance="$SQL_INSTANCE" \
        --project="$PROJECT_ID" \
        --quiet
    echo -e "${GREEN}✓${NC} Database created"
fi

# Create postgres user
gcloud sql users create postgres \
    --instance="$SQL_INSTANCE" \
    --project="$PROJECT_ID" \
    --password 2>/dev/null || true

# Create mlops and cord schemas inside the cbp_sentry database
# These are PostgreSQL schemas (namespaces), not separate databases.
# sentry-data, cbp-risk-engine, and sentry-cord-integration share one Cloud SQL instance.
echo "Creating mlops and cord schemas in cbp_sentry database..."
gcloud sql connect "$SQL_INSTANCE" --user=postgres --project="$PROJECT_ID" << 'SQL' 2>/dev/null || true
CREATE SCHEMA IF NOT EXISTS cbp_sentry;
CREATE SCHEMA IF NOT EXISTS mlops;
CREATE SCHEMA IF NOT EXISTS cord;
SQL
echo -e "${GREEN}✓${NC} Schemas cbp_sentry, mlops, cord created (or already exist)"

echo -e "${GREEN}✓${NC} Cloud SQL configured (IP: $SQL_IP)"
echo ""

# ============================================================================
# 7. Create Secret Manager Secrets
# ============================================================================
echo "7️⃣  Creating Secret Manager secrets..."

create_secret() {
    local secret_name=$1
    local secret_value=$2

    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" 2>/dev/null; then
        # Update existing secret
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
            --data-file=- \
            --project="$PROJECT_ID" \
            --quiet 2>/dev/null
        echo -e "${GREEN}✓${NC} Updated secret: $secret_name"
    else
        # Create new secret
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --data-file=- \
            --project="$PROJECT_ID" \
            --replication-policy="automatic" \
            --quiet
        echo -e "${GREEN}✓${NC} Created secret: $secret_name"
    fi

    # Grant access to all Cloud Run services
    for sa in sentry-api sentry-data sentry-ui sentry-cord cbp-risk-engine; do
        gcloud secrets add-iam-policy-binding "$secret_name" \
            --project="$PROJECT_ID" \
            --member="serviceAccount:${sa}@${PROJECT_ID}.iam.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor" \
            --quiet 2>/dev/null || true
    done
}

# Generate a strong random password for database
DB_PASSWORD=$(openssl rand -base64 32)
DB_USER="postgres"
CLOUD_SQL_CONN="${PROJECT_ID}:${GCP_REGION}:${SQL_INSTANCE}"

# Each service gets its own DATABASE_URL pointing to the same Cloud SQL instance
# but with schema-specific search_path so they stay isolated.
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@/${SQL_INSTANCE}?host=/cloudsql/${CLOUD_SQL_CONN}&options=-c%20search_path%3Dcbp_sentry"
MLOPS_DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@/${SQL_INSTANCE}?host=/cloudsql/${CLOUD_SQL_CONN}&options=-c%20search_path%3Dmlops"
CORD_DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@/${SQL_INSTANCE}?host=/cloudsql/${CLOUD_SQL_CONN}&options=-c%20search_path%3Dcord"

# Create secrets
create_secret "DATABASE_URL"       "$DATABASE_URL"        # sentry-data (cbp_sentry schema)
create_secret "MLOPS_DATABASE_URL" "$MLOPS_DATABASE_URL"  # cbp-risk-engine (mlops schema)
create_secret "CORD_DATABASE_URL"  "$CORD_DATABASE_URL"   # sentry-cord-integration (cord schema)
create_secret "VESSELAPI_KEY"      "placeholder-vesselapi-key"
create_secret "OFAC_API_KEY"       "placeholder-ofac-api-key"

echo ""

# ============================================================================
# 8. Create VPC Connector (for Cloud SQL access)
# ============================================================================
echo "8️⃣  Creating VPC Connector (for Cloud SQL access)..."

VPC_CONNECTOR="sentry-sql-connector"

if gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" \
    --region="$GCP_REGION" \
    --project="$PROJECT_ID" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} VPC Connector already exists"
else
    gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR" \
        --region="$GCP_REGION" \
        --subnet=default \
        --min-instances=2 \
        --max-instances=3 \
        --machine-type=e2-micro \
        --project="$PROJECT_ID" \
        --quiet &
    # Allow background creation to continue
fi

echo ""

# ============================================================================
# 9. Summary & GitHub Secrets
# ============================================================================
echo "════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ GCP Bootstrap Complete!${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Copy these values into GitHub Settings → Secrets:"
echo ""
echo -e "${YELLOW}GCP_PROJECT_ID${NC}"
echo "$PROJECT_ID"
echo ""
echo -e "${YELLOW}GCP_WORKLOAD_IDENTITY_PROVIDER${NC}"
echo "$WIP_RESOURCE"
echo ""
echo -e "${YELLOW}GCP_SERVICE_ACCOUNT_EMAIL${NC}"
echo "sentry-deploy@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
echo -e "${YELLOW}DATABASE_URL${NC} (from Secret Manager)"
echo "postgresql://${DB_USER}@/${SQL_INSTANCE}?host=/cloudsql/${PROJECT_ID}:${GCP_REGION}:${SQL_INSTANCE}"
echo ""
echo "Note: Actual DATABASE_URL with password is in Secret Manager as 'DATABASE_URL'"
echo ""
echo -e "${YELLOW}VESSELAPI_KEY${NC}"
echo "placeholder-vesselapi-key  (update with real key when available)"
echo ""
echo -e "${YELLOW}OFAC_API_KEY${NC}"
echo "placeholder-ofac-api-key  (update with real key when available)"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Copy the GitHub secrets above to https://github.com/rahulvadera/cbp-sentry/settings/secrets/actions"
echo "2. Set Cloud SQL password: gcloud sql users set-password postgres --instance=$SQL_INSTANCE --password"
echo "3. Push to 'dev' branch to trigger GitHub Actions deployment"
echo "4. Monitor deploy at: https://github.com/rahulvadera/cbp-sentry/actions"
echo ""
echo "Verify deployment:"
echo "  gcloud run services list --project $PROJECT_ID --region $GCP_REGION"
echo ""
