#!/bin/bash

#######################################################################
# CBP Sentry - Local Startup Script
# Mimics GitHub Actions workflow for local development/testing
# Usage: ./scripts/local_startup.sh [clean]
#######################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/local_startup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_header() {
    echo -e "${BLUE}=== $1 ===${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}→ $1${NC}" | tee -a "$LOG_FILE"
}

# Clear log file
> "$LOG_FILE"

log_header "CBP Sentry Local Startup"

# ====================================================================
# STEP 1: Environment Setup
# ====================================================================
log_header "Step 1: Environment Setup"

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker first."
    exit 1
fi
log_success "Docker found: $(docker --version)"

if ! command -v docker-compose &> /dev/null; then
    # Try docker compose (newer format)
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose not found"
        exit 1
    fi
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi
log_success "Docker Compose available: $DOCKER_COMPOSE_CMD"

# ====================================================================
# STEP 2: Clean (Optional)
# ====================================================================
if [ "$1" = "clean" ]; then
    log_header "Step 2: Clean Previous Deployment"

    log_info "Stopping containers..."
    $DOCKER_COMPOSE_CMD down -v 2>&1 | grep -i "removing\|stopped" || true
    log_success "Containers stopped"

    log_info "Removing dangling images..."
    docker image prune -f --filter "dangling=true" 2>&1 | tail -1 || true
    log_success "Cleaned up"
else
    log_header "Step 2: Reusing Existing Images (use 'clean' argument to rebuild)"
    log_info "Stopping existing containers..."
    $DOCKER_COMPOSE_CMD down 2>&1 | grep -i "stopping\|stopped" || true
fi

# ====================================================================
# STEP 3: Build Docker Images
# ====================================================================
log_header "Step 3: Building Docker Images"

cd "$PROJECT_ROOT"

services=("sentry-data" "precise-risk-engine" "sentry-api" "sentry-ui")

for service in "${services[@]}"; do
    log_info "Building $service..."

    if [ "$service" = "sentry-ui" ]; then
        BUILD_CONTEXT="ui"
        DOCKERFILE="ui/Dockerfile"
    else
        BUILD_CONTEXT="services/$service"
        DOCKERFILE="services/$service/Dockerfile"
    fi

    if [ ! -f "$DOCKERFILE" ]; then
        log_error "Dockerfile not found: $DOCKERFILE"
        exit 1
    fi

    docker build -t "$service:latest" -f "$DOCKERFILE" "$BUILD_CONTEXT" >> "$LOG_FILE" 2>&1
    log_success "Built $service:latest"
done

# ====================================================================
# STEP 4: Start Services
# ====================================================================
log_header "Step 4: Starting Services with Docker Compose"

log_info "Starting containers..."
$DOCKER_COMPOSE_CMD up -d >> "$LOG_FILE" 2>&1
log_success "Docker Compose services started"

# ====================================================================
# STEP 5: Wait for Health Checks
# ====================================================================
log_header "Step 5: Waiting for Services to be Healthy"

MAX_WAIT=120
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$($DOCKER_COMPOSE_CMD ps --format "{{.Name}},{{.Status}}" 2>/dev/null || echo "")

    if echo "$STATUS" | grep -q "sentry-data.*healthy" && \
       echo "$STATUS" | grep -q "precise-risk-engine.*healthy" && \
       echo "$STATUS" | grep -q "sentry-api.*healthy" && \
       echo "$STATUS" | grep -q "sentry-ui.*healthy"; then
        log_success "All services are healthy"
        break
    fi

    echo -ne "\rWaiting for services... ${ELAPSED}s"
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    log_error "Services did not become healthy within ${MAX_WAIT}s"
    log_info "Current status:"
    $DOCKER_COMPOSE_CMD ps 2>&1 | tee -a "$LOG_FILE"
    exit 1
fi

echo -e "\r                              " # Clear the progress line

# ====================================================================
# STEP 6: Smoke Tests
# ====================================================================
log_header "Step 6: Running Smoke Tests"

SMOKE_TESTS=0
SMOKE_FAILURES=0

# Test sentry-data
log_info "Testing sentry-data service..."
if curl -sf http://localhost:8005/shipments > /dev/null 2>&1; then
    SHIPMENT_COUNT=$(curl -s http://localhost:8005/shipments 2>/dev/null | grep -o '"id":"SHP-' | wc -l)
    log_success "sentry-data responding (found $SHIPMENT_COUNT shipments)"
else
    log_error "sentry-data health check failed"
    SMOKE_FAILURES=$((SMOKE_FAILURES + 1))
fi
SMOKE_TESTS=$((SMOKE_TESTS + 1))

# Test precise-risk-engine (Phase 2)
log_info "Testing precise-risk-engine service..."
if curl -sf http://localhost:8007/health > /dev/null 2>&1; then
    log_success "precise-risk-engine responding on port 8007 (Phase 2 enabled)"
else
    log_error "precise-risk-engine health check failed"
    SMOKE_FAILURES=$((SMOKE_FAILURES + 1))
fi
SMOKE_TESTS=$((SMOKE_TESTS + 1))

# Test sentry-api
log_info "Testing sentry-api service..."
if curl -sf http://localhost:8000/api/shipments > /dev/null 2>&1; then
    API_SHIPMENT_COUNT=$(curl -s http://localhost:8000/api/shipments 2>/dev/null | grep -o '"id":"SHP-' | wc -l)
    log_success "sentry-api responding (found $API_SHIPMENT_COUNT shipments)"
else
    log_error "sentry-api health check failed"
    SMOKE_FAILURES=$((SMOKE_FAILURES + 1))
fi
SMOKE_TESTS=$((SMOKE_TESTS + 1))

# Test sentry-ui
log_info "Testing sentry-ui service..."
if curl -sf http://localhost:3001/ > /dev/null 2>&1; then
    log_success "sentry-ui responding on port 3001"
else
    log_error "sentry-ui health check failed"
    SMOKE_FAILURES=$((SMOKE_FAILURES + 1))
fi
SMOKE_TESTS=$((SMOKE_TESTS + 1))

# ====================================================================
# STEP 7: Summary
# ====================================================================
log_header "Step 7: Deployment Summary"

log_info "Service URLs:"
echo "  UI:  http://localhost:3001" | tee -a "$LOG_FILE"
echo "  API: http://localhost:8000" | tee -a "$LOG_FILE"
echo "  Data Service: http://localhost:8005" | tee -a "$LOG_FILE"
echo "  Precise Risk Engine: http://localhost:8007 (Phase 2)" | tee -a "$LOG_FILE"

if [ $SMOKE_FAILURES -eq 0 ]; then
    log_success "All smoke tests passed ($SMOKE_TESTS/$SMOKE_TESTS)"
    log_success "Local deployment ready!"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
    echo -e "${GREEN}✓ CBP Sentry is running locally${NC}" | tee -a "$LOG_FILE"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
    exit 0
else
    log_error "Smoke tests failed ($SMOKE_FAILURES failures)"
    log_info "View logs with: tail -f $LOG_FILE"
    log_info "View container logs with: docker compose logs -f"
    exit 1
fi
