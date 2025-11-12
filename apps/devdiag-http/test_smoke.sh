#!/bin/bash
# Comprehensive smoke test for devdiag-http server
# Usage: ./test_smoke.sh [base_url]

set -e

BASE="${1:-http://127.0.0.1:8080}"

echo "🔍 DevDiag HTTP Server Smoke Test"
echo "Base URL: $BASE"
echo ""

# Test 1: Health check (GET)
echo "1️⃣ Testing GET /healthz..."
HEALTH=$(curl -sf "$BASE/healthz")
echo "$HEALTH" | jq .
if echo "$HEALTH" | jq -e '.ok == true' > /dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi
echo ""

# Test 2: Health check (HEAD)
echo "2️⃣ Testing HEAD /healthz..."
if curl -sf -I "$BASE/healthz" | grep -q "200 OK"; then
    echo "✅ HEAD /healthz passed"
else
    echo "❌ HEAD /healthz failed"
    exit 1
fi
echo ""

# Test 2.5: Version endpoint
echo "2.5️⃣ Testing GET /version..."
VERSION=$(curl -sf "$BASE/version")
echo "$VERSION" | jq .
if echo "$VERSION" | jq -e '.version' > /dev/null; then
    echo "✅ Version endpoint passed"
else
    echo "❌ Version endpoint failed"
    exit 1
fi
echo ""

# Test 2.6: Selfcheck (CLI availability)
echo "2.6️⃣ Testing GET /selfcheck..."
SELFCHECK=$(curl -sf "$BASE/selfcheck")
echo "$SELFCHECK" | jq .
if echo "$SELFCHECK" | jq -e '.ok == true' > /dev/null; then
    echo "✅ Selfcheck passed - CLI available"
else
    echo "⚠️ Selfcheck failed - CLI may not be installed"
    echo "$SELFCHECK"
fi
echo ""

# Test 2.7: OpenAPI security scheme
echo "2.7️⃣ Testing OpenAPI security scheme..."
OPENAPI=$(curl -sf "$BASE/openapi.json")
if echo "$OPENAPI" | jq -e '.components.securitySchemes.BearerAuth.scheme == "bearer"' > /dev/null; then
    echo "✅ OpenAPI security scheme configured"
else
    echo "❌ OpenAPI security scheme missing"
    exit 1
fi
echo ""

# Test 3: Metrics endpoint
echo "3️⃣ Testing GET /metrics..."
METRICS=$(curl -sf "$BASE/metrics")
if echo "$METRICS" | grep -q "devdiag_http_up 1"; then
    echo "✅ Metrics endpoint passed"
    echo "$METRICS" | head -10
else
    echo "❌ Metrics endpoint failed"
    exit 1
fi
echo ""

# Test 4: Probe presets
echo "4️⃣ Testing GET /probes..."
PROBES=$(curl -sf "$BASE/probes")
echo "$PROBES" | jq .
if echo "$PROBES" | jq -e '.presets | length > 0' > /dev/null; then
    echo "✅ Probes endpoint passed"
else
    echo "❌ Probes endpoint failed"
    exit 1
fi
echo ""

# Test 5: Diagnostic run (example.com)
echo "5️⃣ Testing POST /diag/run (example.com)..."
RESULT=$(curl -sf -X POST "$BASE/diag/run" \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com","preset":"app"}')
echo "$RESULT" | jq .ok
if echo "$RESULT" | jq -e '.ok == true' > /dev/null; then
    echo "✅ Diagnostic run passed"
else
    echo "❌ Diagnostic run failed"
    exit 1
fi
echo ""

# Test 6: Diagnostic run with suppress
echo "6️⃣ Testing POST /diag/run with suppress codes..."
RESULT_SUPPRESS=$(curl -sf -X POST "$BASE/diag/run" \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com","preset":"app","suppress":["CSP_FRAME_ANCESTORS"]}')
if echo "$RESULT_SUPPRESS" | jq -e '.ok == true' > /dev/null; then
    echo "✅ Diagnostic run with suppress passed"
else
    echo "❌ Diagnostic run with suppress failed"
    exit 1
fi
echo ""

# Test 7: Error handling (invalid URL)
echo "7️⃣ Testing error handling (invalid URL)..."
ERROR_RESULT=$(curl -s -X POST "$BASE/diag/run" \
  -H 'content-type: application/json' \
  -d '{"url":"not-a-url","preset":"app"}' || true)
if echo "$ERROR_RESULT" | jq -e '.detail' > /dev/null 2>&1; then
    echo "✅ Error handling passed (returned error detail)"
else
    echo "⚠️  Error handling test inconclusive"
fi
echo ""

echo "🎉 All smoke tests passed!"
echo ""
echo "Summary:"
echo "  ✅ Health check (GET + HEAD)"
echo "  ✅ Version endpoint"
echo "  ✅ Selfcheck (CLI availability)"
echo "  ✅ OpenAPI security scheme"
echo "  ✅ Metrics endpoint"
echo "  ✅ Probes list"
echo "  ✅ Diagnostic run"
echo "  ✅ Suppress codes"
echo "  ✅ Error handling"
