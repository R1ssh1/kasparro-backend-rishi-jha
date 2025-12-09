#!/bin/bash
# Smoke Test Suite for Kasparro Backend
# Verifies production deployment health and functionality

set -e  # Exit on error

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-}"
BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Helper functions
log_test() {
    echo -e "${BOLD}[TEST $1]${NC} $2"
}

log_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
}

# Test 1: Service Running
log_test "1/10" "Service Running"
if curl -s -o /dev/null -w "%{http_code}" "$API_URL/" | grep -q "200"; then
    log_pass "Service is responding"
else
    log_fail "Service is not responding"
fi

# Test 2: Health Endpoint
log_test "2/10" "Health Check"
HEALTH_RESPONSE=$(curl -s "$API_URL/health")
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    log_pass "Health endpoint returns healthy status"
else
    log_fail "Health endpoint not healthy: $HEALTH_RESPONSE"
fi

# Test 3: Database Connectivity
log_test "3/10" "Database Connectivity"
if echo "$HEALTH_RESPONSE" | grep -q '"database":"connected"'; then
    log_pass "Database is connected"
else
    log_fail "Database connection issue"
fi

# Test 4: Data Endpoint (Public)
log_test "4/10" "Public Data Endpoint"
DATA_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/data?limit=5")
HTTP_CODE=$(echo "$DATA_RESPONSE" | tail -n1)
DATA_BODY=$(echo "$DATA_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    RECORD_COUNT=$(echo "$DATA_BODY" | grep -o '"symbol":' | wc -l)
    if [ "$RECORD_COUNT" -gt 0 ]; then
        log_pass "Data endpoint returns records (count: $RECORD_COUNT)"
    else
        log_warn "Data endpoint returns 200 but no records found"
    fi
else
    log_fail "Data endpoint returned HTTP $HTTP_CODE"
fi

# Test 5: Pagination
log_test "5/10" "Pagination Support"
PAGE2_RESPONSE=$(curl -s "$API_URL/data?limit=5&offset=5")
if echo "$PAGE2_RESPONSE" | grep -q '"symbol":'; then
    log_pass "Pagination works (offset parameter)"
else
    log_warn "Pagination may not have enough data for offset test"
fi

# Test 6: Filtering
log_test "6/10" "Filtering Support"
FILTER_RESPONSE=$(curl -s "$API_URL/data?symbol=bitcoin&limit=1")
if echo "$FILTER_RESPONSE" | grep -q '"symbol":"bitcoin"'; then
    log_pass "Filtering works (symbol parameter)"
else
    log_warn "Filtering test inconclusive (bitcoin may not be in dataset)"
fi

# Test 7: Protected Endpoint - Invalid Auth
log_test "7/10" "Protected Endpoint - Invalid Auth"
INVALID_AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: invalid_key_12345" "$API_URL/stats")
INVALID_HTTP_CODE=$(echo "$INVALID_AUTH_RESPONSE" | tail -n1)

if [ "$INVALID_HTTP_CODE" = "401" ]; then
    log_pass "Protected endpoint rejects invalid API key (401)"
elif [ "$INVALID_HTTP_CODE" = "422" ]; then
    log_pass "Protected endpoint requires authentication (422)"
else
    log_fail "Protected endpoint returned unexpected code: $INVALID_HTTP_CODE"
fi

# Test 8: Protected Endpoint - Valid Auth (if API_KEY provided)
log_test "8/10" "Protected Endpoint - Valid Auth"
if [ -n "$API_KEY" ]; then
    VALID_AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$API_URL/stats")
    VALID_HTTP_CODE=$(echo "$VALID_AUTH_RESPONSE" | tail -n1)
    
    if [ "$VALID_HTTP_CODE" = "200" ]; then
        log_pass "Protected endpoint accepts valid API key"
    else
        log_fail "Protected endpoint returned HTTP $VALID_HTTP_CODE with valid key"
    fi
else
    log_warn "Skipping valid auth test (API_KEY not provided)"
fi

# Test 9: Metrics Endpoint
log_test "9/10" "Prometheus Metrics"
METRICS_RESPONSE=$(curl -s "$API_URL/metrics")
if echo "$METRICS_RESPONSE" | grep -q "# HELP"; then
    METRIC_COUNT=$(echo "$METRICS_RESPONSE" | grep -c "# HELP" || true)
    log_pass "Metrics endpoint returns Prometheus format ($METRIC_COUNT metrics)"
else
    log_fail "Metrics endpoint not returning valid Prometheus format"
fi

# Test 10: Run Comparison (if API_KEY provided)
log_test "10/10" "Run Comparison Endpoint"
if [ -n "$API_KEY" ]; then
    RUNS_RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$API_URL/runs")
    RUNS_HTTP_CODE=$(echo "$RUNS_RESPONSE" | tail -n1)
    
    if [ "$RUNS_HTTP_CODE" = "200" ]; then
        log_pass "Run comparison endpoint accessible"
    else
        log_fail "Run comparison endpoint returned HTTP $RUNS_HTTP_CODE"
    fi
else
    log_warn "Skipping run comparison test (API_KEY not provided)"
fi

# Summary
echo ""
echo "========================================="
echo -e "${BOLD}SMOKE TEST SUMMARY${NC}"
echo "========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check deployment.${NC}"
    exit 1
fi
