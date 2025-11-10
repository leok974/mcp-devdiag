# Add-Ons Testing Guide

Complete guide for testing mcp-devdiag optional add-ons: Playwright driver, suppressions, and S3 export.

## Prerequisites

```bash
# Core package
pip install mcp-devdiag

# Optional dependencies
pip install mcp-devdiag[playwright]  # For browser-based probes
pip install mcp-devdiag[export]      # For S3 export
```

## 1. Playwright Driver (Staging Sanity)

**Use case**: Runtime DOM inspection and console capture for staging environments.

### Configuration

In `devdiag.yaml` (staging only):

```yaml
diag:
  browser_enabled: true  # Enable Playwright driver
```

**⚠️ Production**: Always keep `browser_enabled: false` in production to avoid overhead.

### Smoke Test

```bash
# Set environment
BASE="https://devdiag.staging.example.com"
JWT="$STAGING_JWT"
APP="https://staging.example.com"

# Run full bundle with Playwright
curl -s -X POST "$BASE/mcp/diag/bundle" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"url":"'"$APP"'","driver":"playwright","preset":"full"}' \
  | jq '.problems,.score'
```

### Expected Results

- **Same problems as HTTP-only** (CSP headers, CORS, etc.)
- **Plus DOM/console-specific findings**:
  - `CSP_INLINE_BLOCKED` - Inline scripts blocked by CSP
  - `PORTAL_ROOT_MISSING` - React portal container missing
  - `DOM_OVERLAY_DETECTED` - Overlays without ARIA labels

### Installation (Playwright)

First time setup requires browser installation:

```bash
pip install playwright
playwright install chromium
```

---

## 2. Suppressions

**Use case**: Filter known non-issues from diagnostic results.

### Configuration

In `devdiag.yaml`:

```yaml
diag:
  suppress:
    - code: "PORTAL_ROOT_MISSING"
      reason: "Native toasts - not using React portals"
    - code: "CSP_INLINE_STYLE"
      reason: "Third-party widget styles - vendor limitation"
```

### Smoke Test

Add temporary suppression:

```yaml
diag:
  suppress:
    - code: "PORTAL_ROOT_MISSING"
      reason: "Native toasts"
```

Verify filtering:

```bash
curl -s -G "$BASE/mcp/diag/status_plus" \
  --data-urlencode "base_url=$APP" \
  -H "Authorization: Bearer $JWT" \
  | jq '.problems | index("PORTAL_ROOT_MISSING")'
```

**Expected**: `null` (code is suppressed)

### Use Cases

- **Known third-party issues**: Vendor libraries with CSP violations
- **Architecture decisions**: Native browser features instead of React patterns
- **Temporary waivers**: Planned fixes with tracking tickets

---

## 3. S3 Export Guardrails

**Use case**: Export redacted diagnostic snapshots to S3 for incident analysis.

### IAM Setup

**Minimal IAM policy** (attach to DevDiag role):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:AbortMultipartUpload"],
      "Resource": "arn:aws:s3:::mcp-devdiag-artifacts/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::mcp-devdiag-artifacts"
    }
  ]
}
```

See `docs/iam-devdiag-s3.json` for full policy.

### Bucket Policy (Stricter)

**Deny public access** and **enforce SSE**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyPublicAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::mcp-devdiag-artifacts/*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/DevDiagRole"
        }
      }
    },
    {
      "Sid": "EnforceSSE",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::mcp-devdiag-artifacts/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

See `docs/s3-bucket-policy.json` for template.

### Configuration

In `devdiag.yaml`:

```yaml
export:
  s3_bucket: "mcp-devdiag-artifacts"
  region: "us-east-1"
  key_prefix: "staging/"  # Optional organization
```

### Smoke Test

```python
python - <<'PY'
import asyncio, json
from mcp_devdiag.export_s3 import export_snapshot

async def main():
    res = await export_snapshot(
        payload={
            "ok": False,
            "problems": ["CSP_INLINE_BLOCKED"],
            "score": 7
        },
        tenant="demo",
        export_config={
            "s3_bucket": "mcp-devdiag-artifacts",
            "region": "us-east-1"
        }
    )
    print(json.dumps(res, indent=2))

asyncio.run(main())
PY
```

**Expected result**:

```json
{
  "ok": true,
  "bucket": "mcp-devdiag-artifacts",
  "key": "demo/snapshots/1699564823.json",
  "timestamp": 1699564823,
  "size_bytes": 142
}
```

### Safety Caps

**Export size limit** (configured in `devdiag.yaml`):

```yaml
limits:
  export_max_bytes: 262144  # 256 KB (default)
```

Large payloads are rejected with:

```
ValueError: Payload size 300000 bytes exceeds limit 262144 bytes
```

### Redaction

Only **safe keys** are exported:

```python
SAFE_KEYS = {
    "problems",
    "remediation",
    "evidence",
    "score",
    "ok",
    "fixes",
    "severity",
    "preset",
    "probes_run"
}
```

Sensitive data (tokens, user IDs, request bodies) is automatically stripped.

---

## 4. Observability

### Metrics

Export module exposes counters:

```python
from mcp_devdiag.export_s3 import get_export_metrics

metrics = get_export_metrics()
# {
#   "devdiag_exports_total": {"ok": 42, "error": 3},
#   "devdiag_last_export_unixtime": 1699564823
# }
```

### Prometheus Integration

Add to your metrics endpoint:

```python
# devdiag_exports_total{result="ok"} 42
# devdiag_exports_total{result="error"} 3
# devdiag_last_export_unixtime 1699564823
```

### Error Logging

Export failures are logged with context:

```
ERROR: S3 export failed: NoSuchBucket: The bucket does not exist
ERROR: S3 export rejected: payload size 300000 exceeds limit 262144
WARNING: S3 export failed: boto3 not installed
```

---

## 5. CI Integration

### GitHub Actions (Incident Export)

Automatically export diagnostics when PR is labeled `incident`:

```yaml
# .github/workflows/devdiag-export-dryrun.yml
on:
  pull_request:
    types: [labeled]

jobs:
  export-dryrun:
    if: github.event.label.name == 'incident'
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -s -X POST "$DEVDIAG_URL/mcp/devdiag/export_snapshot" \
            -H "Authorization: Bearer $OPERATOR_JWT" \
            -d '{"problems":["PR_INCIDENT"],"score":1}' | jq
    env:
      DEVDIAG_URL: ${{ secrets.DEVDIAG_URL }}
      OPERATOR_JWT: ${{ secrets.DEVDIAG_OPERATOR_JWT }}
```

See `.github/workflows/devdiag-export-dryrun.yml` for full workflow.

---

## 6. Complete Smoke Test Script

Run all add-ons tests:

```bash
./scripts/smoke_test_addons.sh <base_url> <jwt_token> <app_url>

# Example:
./scripts/smoke_test_addons.sh \
  https://devdiag.staging.example.com \
  "$STAGING_JWT" \
  https://staging.example.com
```

**Tests**:
1. ✅ Playwright driver (runtime DOM/console)
2. ✅ Suppressions filtering
3. ✅ S3 export with redaction
4. ✅ Export size cap enforcement

---

## 7. Production Checklist

Before enabling add-ons in production:

- [ ] **Playwright**: Keep `browser_enabled: false` (use HTTP-only probes)
- [ ] **Suppressions**: Document all suppress entries with reasons
- [ ] **S3 Export**: 
  - [ ] IAM policy attached to DevDiag role
  - [ ] Bucket policy enforces SSE-AES256
  - [ ] Bucket has public access blocked
  - [ ] Export size cap configured (256 KB default)
- [ ] **Metrics**: Expose export counters to Prometheus
- [ ] **Audit**: Log all export operations with tenant + timestamp
- [ ] **CI**: Test export in staging before production rollout

---

## 8. Troubleshooting

### Playwright Issues

**Problem**: `playwright not installed`

**Solution**:
```bash
pip install playwright
playwright install chromium
```

**Problem**: `TimeoutError: page.goto: Timeout exceeded`

**Solution**: Increase timeout or check URL accessibility:
```yaml
diag:
  browser_timeout: 30000  # 30 seconds
```

### S3 Export Issues

**Problem**: `NoSuchBucket`

**Solution**: Create bucket or verify name in `export.s3_bucket`

**Problem**: `AccessDenied`

**Solution**: Verify IAM policy and bucket policy allow DevDiag role

**Problem**: `Payload too large`

**Solution**: Reduce probe scope or increase `limits.export_max_bytes`

### Suppressions Not Working

**Problem**: Suppressed codes still appear in results

**Solution**: Verify:
1. Code name matches exactly (case-sensitive)
2. `devdiag.yaml` is in working directory
3. Service restarted after config change

---

## Resources

- **Full configuration**: `examples/devdiag-staging.yaml`
- **IAM policy**: `docs/iam-devdiag-s3.json`
- **Bucket policy**: `docs/s3-bucket-policy.json`
- **Smoke tests**: `scripts/smoke_test_addons.sh`
- **CI workflow**: `.github/workflows/devdiag-export-dryrun.yml`
