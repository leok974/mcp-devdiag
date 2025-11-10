#!/usr/bin/env bash
# Quick reference: mcp-devdiag add-ons smoke tests
# Copy-paste these into your terminal after setting variables

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SETUP (run once per session)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BASE="https://devdiag.staging.example.com"  # Your DevDiag server
JWT="$STAGING_JWT"                           # Reader or Operator token
APP="https://staging.example.com"            # Target application

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 1: PLAYWRIGHT DRIVER (staging only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Requirement: devdiag.yaml must have diag.browser_enabled: true

curl -s -X POST "$BASE/mcp/diag/bundle" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"url":"'"$APP"'","driver":"playwright","preset":"full"}' \
  | jq '{problems: .problems[:5], score: .score}'

# Expected: Same problems as HTTP-only + DOM/console findings
# Examples: CSP_INLINE_BLOCKED, PORTAL_ROOT_MISSING, DOM_OVERLAY_DETECTED

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 2: SUPPRESSIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Requirement: devdiag.yaml must have diag.suppress entries
# Example:
#   diag:
#     suppress:
#       - code: "PORTAL_ROOT_MISSING"
#         reason: "Native toasts"

curl -s -G "$BASE/mcp/diag/status_plus" \
  --data-urlencode "base_url=$APP" \
  -H "Authorization: Bearer $JWT" \
  | jq '.problems | index("PORTAL_ROOT_MISSING")'

# Expected: null (code is suppressed)
# If not null: code isn't suppressed or doesn't exist in results

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 3: S3 EXPORT (redacted bundles)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Requirement: export.s3_bucket configured + AWS credentials

python - <<'PY'
import asyncio, json
try:
    from mcp_devdiag.export_s3 import export_snapshot
    
    async def main():
        try:
            res = await export_snapshot(
                payload={
                    "ok": False,
                    "problems": ["CSP_INLINE_BLOCKED", "CORS_NO_WILDCARD"],
                    "score": 7,
                    "sensitive_data": "should_be_redacted"  # Will be removed
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
    print(json.dumps({"error": "boto3 not installed - run: pip install boto3"}, indent=2))
PY

# Expected: {"ok": true, "bucket": "...", "key": "smoke-test/snapshots/...", ...}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 4: EXPORT SIZE CAP (256 KB limit)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Generate 300 KB payload (should be rejected)

python - <<'PY'
import asyncio, json
try:
    from mcp_devdiag.export_s3 import export_snapshot
    
    async def main():
        large_payload = {"x": "A" * 300000}  # ~300 KB
        try:
            res = await export_snapshot(
                payload=large_payload,
                tenant="size-test",
                export_config={
                    "s3_bucket": "mcp-devdiag-artifacts",
                    "region": "us-east-1"
                }
            )
            print(json.dumps({"result": "accepted (size cap not enforced!)"}))
        except ValueError as e:
            print(json.dumps({"result": "rejected", "reason": str(e)}))
    
    asyncio.run(main())
except ImportError:
    print(json.dumps({"error": "boto3 not installed"}))
PY

# Expected: "rejected" with "exceeds limit 262144 bytes"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 5: EXPORT METRICS (observability)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

python - <<'PY'
from mcp_devdiag.export_s3 import get_export_metrics
import json

metrics = get_export_metrics()
print(json.dumps(metrics, indent=2))
PY

# Expected:
# {
#   "devdiag_exports_total": {"ok": N, "error": M},
#   "devdiag_last_export_unixtime": <timestamp>
# }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FULL SMOKE TEST (all add-ons)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

./scripts/smoke_test_addons.sh "$BASE" "$JWT" "$APP"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VERIFY S3 BUCKET CONTENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

aws s3 ls s3://mcp-devdiag-artifacts/smoke-test/snapshots/ --recursive

# Expected: List of timestamped JSON files

# Download and inspect a snapshot
aws s3 cp s3://mcp-devdiag-artifacts/smoke-test/snapshots/<timestamp>.json - | jq

# Verify redaction: only safe keys present (problems, score, ok, etc.)
# No sensitive data: no tokens, user IDs, request bodies

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TROUBLESHOOTING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Playwright not found:
pip install playwright
playwright install chromium

# boto3 not found:
pip install boto3

# S3 access denied:
# - Verify IAM policy attached: docs/iam-devdiag-s3.json
# - Check bucket policy: docs/s3-bucket-policy.json

# Suppressions not working:
# - Verify devdiag.yaml has diag.suppress entries
# - Check code name matches exactly (case-sensitive)
# - Restart service after config change

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DOCS & RESOURCES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Full guide:        docs/ADDONS.md
# IAM policy:        docs/iam-devdiag-s3.json
# Bucket policy:     docs/s3-bucket-policy.json
# Config example:    examples/devdiag-staging.yaml
# Summary:           docs/ADDONS_SUMMARY.md
