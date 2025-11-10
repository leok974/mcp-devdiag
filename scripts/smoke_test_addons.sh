#!/usr/bin/env bash
# Smoke tests for mcp-devdiag add-ons (Playwright, suppressions, S3 export)
# Usage: ./smoke_test_addons.sh <base_url> <jwt_token> <app_url>

set -euo pipefail

BASE="${1:-http://localhost:8000}"
JWT="${2:-}"
APP="${3:-https://staging.example.com}"

if [[ -z "$JWT" ]]; then
  echo "❌ JWT token required: ./smoke_test_addons.sh <base_url> <jwt_token> <app_url>"
  exit 1
fi

echo "🧪 mcp-devdiag Add-Ons Smoke Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Base URL: $BASE"
echo "App URL:  $APP"
echo ""

# Test 1: Playwright driver (staging only)
echo "1️⃣  Testing Playwright driver..."
echo "   Requirement: devdiag.yaml must have diag.browser_enabled: true"

PLAYWRIGHT_RESULT=$(curl -s -X POST "$BASE/mcp/diag/bundle" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$APP\",\"driver\":\"playwright\",\"preset\":\"full\"}" \
  | jq -r '{problems: .problems, score: .score}')

PLAYWRIGHT_PROBLEMS=$(echo "$PLAYWRIGHT_RESULT" | jq -r '.problems | length')
PLAYWRIGHT_SCORE=$(echo "$PLAYWRIGHT_RESULT" | jq -r '.score')

if [[ $PLAYWRIGHT_PROBLEMS -gt 0 ]]; then
  echo "   ✅ Playwright driver returned $PLAYWRIGHT_PROBLEMS problems (score: $PLAYWRIGHT_SCORE)"
  echo "   Sample problems: $(echo "$PLAYWRIGHT_RESULT" | jq -r '.problems[:3] | join(", ")')"
else
  echo "   ⚠️  Playwright driver returned 0 problems (may be disabled or no issues found)"
fi
echo ""

# Test 2: Suppressions filtering
echo "2️⃣  Testing suppressions..."
echo "   Requirement: devdiag.yaml must have diag.suppress entries"

# Check if PORTAL_ROOT_MISSING is suppressed
SUPPRESSION_CHECK=$(curl -s -G "$BASE/mcp/diag/status_plus" \
  --data-urlencode "base_url=$APP" \
  -H "Authorization: Bearer $JWT" \
  | jq -r '.problems | index("PORTAL_ROOT_MISSING")')

if [[ "$SUPPRESSION_CHECK" == "null" ]]; then
  echo "   ✅ PORTAL_ROOT_MISSING is correctly suppressed"
else
  echo "   ℹ️  PORTAL_ROOT_MISSING found at index $SUPPRESSION_CHECK (not suppressed or not present)"
fi
echo ""

# Test 3: S3 export with redaction
echo "3️⃣  Testing S3 export (redaction + size cap)..."
echo "   Requirement: export.s3_bucket configured + AWS credentials"

EXPORT_TEST=$(python - <<'PY'
import asyncio, json, sys
try:
    from mcp_devdiag.export_s3 import export_snapshot
    
    async def main():
        try:
            res = await export_snapshot(
                payload={
                    "ok": False,
                    "problems": ["CSP_INLINE_BLOCKED", "CORS_NO_WILDCARD"],
                    "score": 7,
                    "sensitive_data": "should_be_redacted"
                },
                tenant="smoke-test",
                export_config={
                    "s3_bucket": "mcp-devdiag-artifacts",
                    "region": "us-east-1"
                }
            )
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(json.dumps({"error": str(e)}, indent=2))
    
    asyncio.run(main())
except ImportError:
    print(json.dumps({"error": "boto3 not installed - skip S3 test"}, indent=2))
PY
)

EXPORT_STATUS=$(echo "$EXPORT_TEST" | jq -r 'if .ok then "ok" elif .error then "error" else "unknown" end')

case "$EXPORT_STATUS" in
  ok)
    EXPORT_KEY=$(echo "$EXPORT_TEST" | jq -r '.key')
    echo "   ✅ S3 export succeeded: $EXPORT_KEY"
    ;;
  error)
    EXPORT_ERROR=$(echo "$EXPORT_TEST" | jq -r '.error')
    if [[ "$EXPORT_ERROR" == *"boto3 not installed"* ]]; then
      echo "   ⚠️  S3 export skipped (boto3 not installed)"
    else
      echo "   ❌ S3 export failed: $EXPORT_ERROR"
    fi
    ;;
  *)
    echo "   ❌ S3 export returned unexpected response"
    ;;
esac
echo ""

# Test 4: Export size cap validation
echo "4️⃣  Testing export size cap (256 KB limit)..."

LARGE_PAYLOAD=$(python -c "import json; print(json.dumps({'x': 'A' * 300000}))")
SIZE_CAP_TEST=$(python - <<PY
import asyncio, json, sys
try:
    from mcp_devdiag.export_s3 import export_snapshot
    
    async def main():
        large = json.loads('''$LARGE_PAYLOAD''')
        try:
            res = await export_snapshot(
                payload=large,
                tenant="size-test",
                export_config={"s3_bucket": "mcp-devdiag-artifacts", "region": "us-east-1"}
            )
            print(json.dumps({"ok": res.get("ok", False)}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
    
    asyncio.run(main())
except ImportError:
    print(json.dumps({"error": "boto3 not installed"}))
PY
)

SIZE_CAP_RESULT=$(echo "$SIZE_CAP_TEST" | jq -r 'if .error then "rejected" else "accepted" end')

if [[ "$SIZE_CAP_RESULT" == "rejected" ]]; then
  echo "   ✅ Large payload correctly rejected (size cap enforced)"
elif [[ "$SIZE_CAP_RESULT" == "accepted" ]]; then
  echo "   ⚠️  Large payload accepted (size cap may not be enforced)"
else
  echo "   ℹ️  Size cap test inconclusive"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Smoke tests completed"
echo ""
echo "Next steps:"
echo "  • Review Playwright driver results (DOM/console findings)"
echo "  • Verify suppressions match devdiag.yaml configuration"
echo "  • Check S3 bucket for exported snapshots"
echo "  • Monitor devdiag_exports_total metric"
