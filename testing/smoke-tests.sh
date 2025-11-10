#!/bin/bash
# Smoke tests for DevDiag deployment validation
# Run after deploying to staging/production

set -e

# Configuration
HOST="${DEVDIAG_HOST:-https://staging.example.com}"
READER_TOKEN="${READER_TOKEN:-}"
OPERATOR_TOKEN="${OPERATOR_TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "===================================================================="
echo "DevDiag Smoke Tests"
echo "===================================================================="
echo "Host: $HOST"
echo ""

# Check prerequisites
if [ -z "$READER_TOKEN" ]; then
    echo -e "${RED}ERROR: READER_TOKEN environment variable not set${NC}"
    exit 1
fi

if [ -z "$OPERATOR_TOKEN" ]; then
    echo -e "${YELLOW}WARNING: OPERATOR_TOKEN not set, skipping operator tests${NC}"
fi

# Test 1: Auth Sanity - Probe allowed endpoint
echo -e "${YELLOW}Test 1: Auth Sanity - Probe Allowed Endpoint${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$HOST/mcp/devdiag/get_request_diagnostics" \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://staging.api.example.com/healthz",
    "method": "GET"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Probe succeeded (HTTP $HTTP_CODE)"
    echo "$BODY" | jq -r '.status, .latency_ms'
else
    echo -e "${RED}✗ FAIL${NC} - Expected 200, got HTTP $HTTP_CODE"
    echo "$BODY"
    exit 1
fi
echo ""

# Test 2: Deny Non-Allowlisted URL
echo -e "${YELLOW}Test 2: Deny Non-Allowlisted URL${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HOST/mcp/devdiag/get_request_diagnostics" \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/blocked",
    "method": "GET"
  }')

if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Non-allowlisted URL blocked (HTTP $HTTP_CODE)"
else
    echo -e "${RED}✗ FAIL${NC} - Expected 403, got HTTP $HTTP_CODE"
    exit 1
fi
echo ""

# Test 3: Get Metrics
echo -e "${YELLOW}Test 3: Get Metrics${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" "$HOST/mcp/devdiag/get_metrics?window=15m" \
  -H "Authorization: Bearer $READER_TOKEN")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Metrics retrieved (HTTP $HTTP_CODE)"
    echo "$BODY" | jq -r '.status?, .rates?, .latency_ms?'
else
    echo -e "${RED}✗ FAIL${NC} - Expected 200, got HTTP $HTTP_CODE"
    echo "$BODY"
    exit 1
fi
echo ""

# Test 4: Get Status
echo -e "${YELLOW}Test 4: Get Status${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$HOST/mcp/devdiag/get_status" \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status retrieved (HTTP $HTTP_CODE)"
    echo "$BODY" | jq -r '.mode?, .sampling?, .tenant?'
else
    echo -e "${RED}✗ FAIL${NC} - Expected 200, got HTTP $HTTP_CODE"
    echo "$BODY"
    exit 1
fi
echo ""

# Test 5: Reader Cannot Set Mode (should fail)
echo -e "${YELLOW}Test 5: Reader Cannot Set Mode (Authorization Check)${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HOST/mcp/devdiag/set_mode" \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "prod:incident",
    "ttl_seconds": 600
  }')

if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Reader blocked from setting mode (HTTP $HTTP_CODE)"
else
    echo -e "${RED}✗ FAIL${NC} - Expected 403, got HTTP $HTTP_CODE (reader should not have set_mode access)"
    exit 1
fi
echo ""

# Operator Tests (only if token provided)
if [ -n "$OPERATOR_TOKEN" ]; then
    echo -e "${YELLOW}Test 6: Operator Can Set Mode${NC}"
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$HOST/mcp/devdiag/set_mode" \
      -H "Authorization: Bearer $OPERATOR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "mode": "prod:observe",
        "ttl_seconds": null
      }')

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Operator set mode successfully (HTTP $HTTP_CODE)"
        echo "$BODY" | jq
    else
        echo -e "${RED}✗ FAIL${NC} - Expected 200, got HTTP $HTTP_CODE"
        echo "$BODY"
        exit 1
    fi
    echo ""
fi

# Test 7: Policy Validation (Local)
echo -e "${YELLOW}Test 7: Policy Tests (CI Validation)${NC}"
if command -v pytest &> /dev/null; then
    if pytest -q tests/test_devdiag_policy.py 2>&1 | grep -q "passed"; then
        echo -e "${GREEN}✓ PASS${NC} - Policy tests passed"
    else
        echo -e "${RED}✗ FAIL${NC} - Policy tests failed"
        exit 1
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC} - pytest not available locally"
fi
echo ""

echo "===================================================================="
echo -e "${GREEN}All smoke tests passed!${NC}"
echo "===================================================================="
echo ""
echo "Next steps:"
echo "1. Monitor error rates and latencies"
echo "2. Validate sampling overhead (should be <0.5% CPU)"
echo "3. Check probe success rate ≥99%"
echo "4. Review audit logs for operator actions"
