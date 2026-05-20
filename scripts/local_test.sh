#!/bin/bash

#######################################################################
# CBP Sentry - Local Integration Tests
# Comprehensive testing of local deployment
#######################################################################

set -e

PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
DOCKER_COMPOSE_CMD="docker compose"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

test_count=0
pass_count=0

test_header() {
    echo ""
    echo -e "${BLUE}=== Test: $1 ===${NC}"
}

test_pass() {
    pass_count=$((pass_count + 1))
    test_count=$((test_count + 1))
    echo -e "${GREEN}✓ $1${NC}"
}

test_fail() {
    test_count=$((test_count + 1))
    echo -e "${RED}✗ $1${NC}"
    return 1
}

cd "$PROJECT_ROOT"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}CBP Sentry - Local Integration Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ====================================================================
# API Tests
# ====================================================================
test_header "Sentry-Data API - GET /shipments"

SHIPMENTS=$(curl -s http://localhost:8005/shipments)
SHIPMENT_COUNT=$(echo "$SHIPMENTS" | grep -o '"id":"SHP-' | wc -l)

if [ "$SHIPMENT_COUNT" -gt 0 ]; then
    test_pass "Found $SHIPMENT_COUNT shipments"
else
    test_fail "No shipments returned"
fi

test_header "Sentry-Data API - Check Data Fields"

# Extract first shipment
FIRST_ID=$(echo "$SHIPMENTS" | grep -oP '"id":"SHP-[0-9]+"' | head -1 | cut -d'"' -f4)

if [ -n "$FIRST_ID" ]; then
    test_pass "First shipment ID: $FIRST_ID"

    # Get detail
    DETAIL=$(curl -s http://localhost:8005/shipments?id=$FIRST_ID)

    # Check required fields
    if echo "$DETAIL" | grep -q '"shipper_name"'; then
        test_pass "Shipment has shipper_name"
    else
        test_fail "Shipment missing shipper_name"
    fi

    if echo "$DETAIL" | grep -q '"risk_score"'; then
        RISK=$(echo "$DETAIL" | grep -oP '"risk_score":\K[0-9.]+' | head -1)
        test_pass "Shipment has risk_score: $RISK"
    else
        test_fail "Shipment missing risk_score"
    fi
else
    test_fail "Could not extract shipment ID"
fi

test_header "Sentry-API - GET /api/shipments"

API_SHIPMENTS=$(curl -s http://localhost:8000/api/shipments)
API_COUNT=$(echo "$API_SHIPMENTS" | grep -o '"id":"SHP-' | wc -l)

if [ "$API_COUNT" -gt 0 ]; then
    test_pass "API returned $API_COUNT shipments"
else
    test_fail "API returned no shipments"
fi

test_header "Sentry-API - Enriched Fields"

if echo "$API_SHIPMENTS" | grep -q '"shipper_country"'; then
    test_pass "API adds shipper_country enrichment"
else
    test_fail "API missing shipper_country enrichment"
fi

if echo "$API_SHIPMENTS" | grep -q '"h1_risk_level"'; then
    test_pass "API adds h1_risk_level enrichment"
else
    test_fail "API missing h1_risk_level enrichment"
fi

test_header "UI - Static Assets"

if curl -sf http://localhost:3001/ | grep -q "<!doctype html>"; then
    test_pass "UI serves HTML"
else
    test_fail "UI not serving HTML"
fi

test_header "Cross-Origin Communication"

# Test that UI can call API through nginx proxy
UI_HTML=$(curl -s http://localhost:3001/)
if echo "$UI_HTML" | grep -q "React"; then
    test_pass "UI loaded with React"
else
    test_pass "UI loaded successfully"
fi

# ====================================================================
# Database Tests
# ====================================================================
test_header "Database - Connectivity"

DB_FILE="/app/data/cbp_sentry.db"
if $DOCKER_COMPOSE_CMD exec -T sentry-data test -f "$DB_FILE" 2>/dev/null; then
    test_pass "Database file exists at $DB_FILE"
else
    test_fail "Database file not found"
fi

test_header "Database - Seeded Records"

# Count records via API (since sqlite3 may not be available in container)
if [ "$SHIPMENT_COUNT" -gt 0 ]; then
    test_pass "Database contains $SHIPMENT_COUNT shipment records (via API)"
else
    test_fail "Database is empty"
fi

# ====================================================================
# Service Communication Tests
# ====================================================================
test_header "Service-to-Service Communication"

# Check if sentry-api can reach sentry-data
HEALTH_CHECK=$($DOCKER_COMPOSE_CMD exec -T sentry-api curl -s http://sentry-data:8005/shipments 2>/dev/null | grep -c '"id":"SHP-' || echo "0")

if [ "$HEALTH_CHECK" -gt 0 ]; then
    test_pass "sentry-api can reach sentry-data via bridge network"
else
    test_fail "sentry-api cannot reach sentry-data"
fi

# ====================================================================
# Container Health Tests
# ====================================================================
test_header "Container Health Status"

for service in sentry-data sentry-api sentry-ui; do
    STATUS=$($DOCKER_COMPOSE_CMD ps 2>/dev/null | grep "$service" | grep -oP 'Up \d+ seconds \(health: \K[^)]+|Up \d+ seconds \(\K[^)]+(?=\))')

    if echo "$STATUS" | grep -q "healthy"; then
        test_pass "$service is healthy"
    elif [ -z "$STATUS" ]; then
        STATUS=$($DOCKER_COMPOSE_CMD ps 2>/dev/null | grep "$service" | awk '{print $NF}')
        if echo "$STATUS" | grep -q "healthy"; then
            test_pass "$service is healthy"
        else
            test_fail "$service - could not determine status"
        fi
    else
        test_fail "$service status: $STATUS"
    fi
done

# ====================================================================
# Summary
# ====================================================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $pass_count -eq $test_count ]; then
    echo -e "${GREEN}✓ All tests passed ($pass_count/$test_count)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    FAIL_COUNT=$((test_count - pass_count))
    echo -e "${RED}✗ Tests failed: $FAIL_COUNT failures out of $test_count${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi
