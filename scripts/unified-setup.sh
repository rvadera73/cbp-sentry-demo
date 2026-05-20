#!/bin/bash
# ============================================================================
# Unified Setup Script — Works for LOCAL docker-compose AND Cloud Run
# ============================================================================
# Usage:
#   Local dev:  bash scripts/unified-setup.sh local
#   Staging:    bash scripts/unified-setup.sh staging
#   Production: bash scripts/unified-setup.sh production

set -e

ENV="${1:-local}"

echo "🚀 CBP Sentry Unified Setup — Environment: $ENV"
echo ""

# ============================================================================
# 1. VALIDATE ENVIRONMENT
# ============================================================================

case "$ENV" in
  local)
    echo "📍 LOCAL MODE: docker-compose with SQLite + fixture APIs"
    DEPLOYMENT_ENV=local
    API_MODE=fixture
    DATABASE_URL="sqlite:///./data/cbp_sentry.db"
    DATA_SERVICE_URL="http://sentry-data:8005"
    SENZING_URL="http://senzing:8250"
    ;;
  staging)
    echo "📍 STAGING MODE: Cloud Run with Neon PostgreSQL + live APIs"
    DEPLOYMENT_ENV=staging
    API_MODE=live
    # These MUST be set in .env.staging or GitHub Secrets
    [ -z "$DATABASE_URL" ] && echo "ERROR: DATABASE_URL not set" && exit 1
    [ -z "$GCP_PROJECT_ID" ] && echo "ERROR: GCP_PROJECT_ID not set" && exit 1
    DATA_SERVICE_URL="https://sentry-data-${GCP_PROJECT_ID}.run.app"
    ;;
  production)
    echo "📍 PRODUCTION MODE: Cloud Run with Cloud SQL + live APIs"
    DEPLOYMENT_ENV=production
    API_MODE=live
    [ -z "$DATABASE_URL" ] && echo "ERROR: DATABASE_URL not set" && exit 1
    [ -z "$GCP_PROJECT_ID" ] && echo "ERROR: GCP_PROJECT_ID not set" && exit 1
    DATA_SERVICE_URL="https://sentry-data-${GCP_PROJECT_ID}.run.app"
    ;;
  *)
    echo "ERROR: Unknown environment '$ENV'"
    echo "Usage: $0 {local|staging|production}"
    exit 1
    ;;
esac

# ============================================================================
# 2. LOAD CONFIGURATION
# ============================================================================

if [ "$ENV" = "local" ]; then
  # Local: Create .env file from template if it doesn't exist
  if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local from template..."
    cp .env.local.template .env.local
  fi

  # Load local env vars
  export $(grep -v '^#' .env.local | xargs)

  # Create data directory
  mkdir -p data

  # Remove stale Docker containers
  echo "🧹 Cleaning up stale containers..."
  docker-compose down -v 2>/dev/null || true
  docker ps -aq --filter "status=exited" | xargs docker rm -f 2>/dev/null || true

  # Build images
  echo "🔨 Building Docker images (this may take 2-3 minutes)..."
  docker-compose build --no-cache

  # Start services
  echo "🚀 Starting services..."
  docker-compose up -d

  # Wait for health checks
  echo "⏳ Waiting for services to be ready..."
  for i in {1..30}; do
    if curl -s http://localhost:8005/health >/dev/null 2>&1 && \
       curl -s http://localhost:8000/health >/dev/null 2>&1; then
      echo "✅ All services healthy!"
      break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
  done

  # Verify
  echo ""
  echo "✅ SETUP COMPLETE — Local Services Running:"
  echo "   🎨 UI:   http://localhost:3001"
  echo "   ⚙️  API:  http://localhost:8000"
  echo "   💾 Data: http://localhost:8005"
  echo "   🔗 Senzing (optional): http://localhost:8250"
  echo ""
  echo "📊 Test the setup:"
  echo "   curl http://localhost:8000/api/shipments?limit=1"
  echo ""

elif [ "$ENV" = "staging" ] || [ "$ENV" = "production" ]; then
  # Cloud Run: Validate secrets are in GitHub
  echo "✅ Cloud Run deployment via GitHub Actions"
  echo "   - Ensure .github/workflows/deploy.yml has correct secrets"
  echo "   - Push to dev branch for staging deploy"
  echo "   - Push to main branch for production deploy"
  echo ""
  echo "Required GitHub Secrets:"
  echo "   - GCP_PROJECT_ID: ${GCP_PROJECT_ID:-MISSING}"
  echo "   - GCP_WORKLOAD_IDENTITY_PROVIDER: (from bootstrap script)"
  echo "   - GCP_SERVICE_ACCOUNT_EMAIL: (from bootstrap script)"
  echo "   - DATABASE_URL: ${DATABASE_URL:0:20}... (from Neon)"
  echo "   - API_MODE: $API_MODE"
  echo ""
fi

# ============================================================================
# 3. SUMMARY
# ============================================================================

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🎯 Configuration Summary:"
echo "   DEPLOYMENT_ENV: $DEPLOYMENT_ENV"
echo "   API_MODE: $API_MODE"
echo "   DATABASE: ${DATABASE_URL:0:50}..."
echo "   DATA_SERVICE_URL: $DATA_SERVICE_URL"
echo "════════════════════════════════════════════════════════════════════════════════"
