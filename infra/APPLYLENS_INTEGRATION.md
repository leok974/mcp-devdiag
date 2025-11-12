# ApplyLens → DevDiag Integration

## Backend Proxy Configuration

Add to `apps/backend/.env`:

```bash
# DevDiag Integration
DEVDIAG_BASE=https://devdiag.leoklemet.com
DEVDIAG_ENABLED=1
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=applylens.app,.applylens.app,api.applylens.app
DEVDIAG_JWT=<your-service-account-jwt>
```

## CI Configuration (HTTP Path)

`.github/workflows/devdiag-quickcheck.yml`:

```yaml
name: DevDiag Quickcheck
on:
  pull_request:
    branches: ["main"]
jobs:
  devdiag:
    runs-on: ubuntu-latest
    env:
      DEVDIAG_BASE: https://devdiag.leoklemet.com
      DEVDIAG_JWT: ${{ secrets.DEVDIAG_JWT }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Health check
        run: |
          curl -fsS "$DEVDIAG_BASE/healthz" | jq .
          curl -fsS "$DEVDIAG_BASE/selfcheck" | jq .
      
      - name: Probe ApplyLens
        run: |
          body='{"url":"https://applylens.app","preset":"app","tenant":"applylens"}'
          hdr=("-H" "content-type: application/json")
          [ -n "$DEVDIAG_JWT" ] && hdr+=("-H" "authorization: Bearer $DEVDIAG_JWT")
          curl -fsS -X POST "$DEVDIAG_BASE/diag/run" "${hdr[@]}" -d "$body" > diag.json
          
          echo "### Diagnostic Results" >> $GITHUB_STEP_SUMMARY
          echo "**Target:** https://applylens.app" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          
          echo "**Top Problem Codes:**" >> $GITHUB_STEP_SUMMARY
          jq -r '.result.problems[]?.code' diag.json | sort | uniq -c | sort -nr | head -20 | sed 's/^/* /' >> $GITHUB_STEP_SUMMARY || echo "* No problems found ✅" >> $GITHUB_STEP_SUMMARY
      
      - name: Policy gate
        run: jq -e '(.result.problems // [] | length) < 25' diag.json
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: devdiag-results
          path: diag.json
```

**GitHub Secrets Required:**
- `DEVDIAG_JWT` - Service account JWT for https://devdiag.leoklemet.com

## CI Configuration (MCP Stdio Path)

**Alternative:** Pure CLI without HTTP server (faster builds):

`.github/workflows/devdiag-mcp-quickcheck.yml`:

```yaml
name: DevDiag Quickcheck (MCP)
on:
  pull_request:
    branches: ["main"]
jobs:
  mcp-probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      
      - name: Install dependencies
        run: pip install "mcp-devdiag[playwright,export]==0.2.1" jq
      
      - name: Run MCP probe
        run: |
          python scripts/mcp_probe.py \
            --url https://applylens.app \
            --preset app \
            --pretty > diag.json
          
          echo "### Diagnostic Results" >> $GITHUB_STEP_SUMMARY
          echo "**Target:** https://applylens.app" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          
          echo "**Top Problem Codes:**" >> $GITHUB_STEP_SUMMARY
          jq -r '.problems[]?.code' diag.json | sort | uniq -c | sort -nr | head -20 | sed 's/^/* /' >> $GITHUB_STEP_SUMMARY || echo "* No problems found ✅" >> $GITHUB_STEP_SUMMARY
      
      - name: Policy gate
        run: jq -e '(.problems // [] | length) < 25' diag.json
```

**No secrets required** - Runs locally without HTTP server.

## Quick Test Commands

### Test Backend Proxy Locally

```bash
# From ApplyLens backend
curl -s -X POST http://localhost:8000/ops/diag \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://applylens.app","preset":"app"}' | jq .
```

### Test Shared Service Directly

```bash
export DEVDIAG_JWT="your-jwt-token"

curl -s -X POST https://devdiag.leoklemet.com/diag/run \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $DEVDIAG_JWT" \
  -d '{"url":"https://applylens.app","preset":"app","tenant":"applylens"}' | jq .
```

### Test MCP Stdio Locally

```bash
cd path/to/applylens
python scripts/mcp_probe.py --url https://applylens.app --preset app --pretty
```

## Allowed Targets

Server-side allowlist enforces these patterns:

- `applylens.app` (exact match)
- `.applylens.app` (all subdomains: `*.applylens.app`)
- `api.applylens.app` (exact match)

**Examples:**
- ✅ `https://applylens.app` - Allowed
- ✅ `https://www.applylens.app` - Allowed (subdomain)
- ✅ `https://api.applylens.app` - Allowed
- ❌ `https://evil.com` - Rejected (not in allowlist)

## Tenant Isolation

When using `"tenant": "applylens"` in requests:
- Server enforces ApplyLens-specific allowlist
- Prevents cross-tenant inspection
- Adds tenant label to metrics

**Example Request:**
```json
{
  "url": "https://applylens.app",
  "preset": "app",
  "tenant": "applylens",
  "suppress": ["KNOWN_ISSUE_CODE"]
}
```

## Monitoring

### Grafana Dashboard

Import panel for ApplyLens-specific metrics:

**Query:** `devdiag_http_requests_total{tenant="applylens"}`

**Filters:**
- Status: `{status="200"}` (success) vs `{status=~"5.."}` (errors)
- Preset: `{preset="app"}`

### Alerts

Set up alerts for ApplyLens-specific issues:

```yaml
- alert: ApplyLensDevDiagErrors
  expr: rate(devdiag_http_requests_total{tenant="applylens",status=~"5.."}[5m]) > 0.1
  for: 5m
  labels:
    severity: warning
    project: applylens
  annotations:
    summary: "High error rate on ApplyLens diagnostics"
```

## Troubleshooting

### 422 Validation Error

**Cause:** URL not in allowlist

**Solution:**
1. Check `DEVDIAG_ALLOW_HOSTS` in backend proxy
2. Verify `ALLOW_TARGET_HOSTS` in shared service
3. Ensure URL matches allowed patterns

### 429 Rate Limited

**Cause:** Exceeded 2 requests/second

**Solution:**
- Wait and retry
- Consider caching results
- Contact infra to increase `RATE_LIMIT_RPS` if needed

### 503 Service Busy

**Cause:** MAX_CONCURRENT limit reached

**Solution:**
- Wait for current probes to finish
- Avoid parallel probes in CI
- Contact infra to increase `MAX_CONCURRENT` if needed

## Best Practices

1. **Cache Results** - Don't probe the same URL repeatedly
2. **Use Tenant Field** - Always include `"tenant": "applylens"` for better metrics
3. **Suppress Known Issues** - Use `"suppress": ["CODE1", "CODE2"]` for accepted problems
4. **Policy Gates** - Set `--max-problems` threshold in CI to catch regressions
5. **Trace Correlation** - Use `x-request-id` from responses to search logs
