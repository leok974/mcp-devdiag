# Infrastructure Deployment Guide

This directory contains the shared DevDiag HTTP service deployment for all projects (ApplyLens, LedgerMind, Portfolio).

## Architecture

**Single Service, Multiple Tenants:**
- One DevDiag HTTP container on `infra_net`
- Exposed via Cloudflare Tunnel at `devdiag.leoklemet.com`
- Per-tenant allowlist + rate limits enforced server-side
- Each project uses a lightweight backend proxy

**Benefits:**
- 🔒 Single point of auth/rate limiting/allowlisting
- 📊 Centralized observability (one `/metrics` endpoint)
- 🚀 Simpler ops (one service to monitor/update)
- 💰 Lower resource usage (shared Playwright pool)

## Deployment

### 1. Create Infrastructure Network (One-Time)

```bash
docker network create infra_net
```

### 2. Configure Environment

Copy the example env file and customize:

```bash
cp .env.devdiag.infra.example .env.devdiag.infra
# Edit .env.devdiag.infra with your JWKS_URL and JWT_AUD
```

**Required Changes:**
- `JWKS_URL` - Your auth provider's JWKS endpoint
- `JWT_AUD` - Expected JWT audience claim
- Update `TENANT_ALLOW_HOSTS_JSON` with your actual domains

### 3. Deploy the Service

```bash
# From mcp-devdiag/infra/ directory
docker compose -f docker-compose.devdiag.yml up -d --pull always
```

**Check Status:**
```bash
docker compose -f docker-compose.devdiag.yml ps
docker compose -f docker-compose.devdiag.yml logs -f devdiag-http
```

### 4. Verify Endpoints

```bash
# Health check
curl -s http://127.0.0.1:8080/healthz | jq .

# CLI check
curl -s http://127.0.0.1:8080/selfcheck | jq .

# Readiness
curl -s http://127.0.0.1:8080/ready | jq .
```

## Cloudflare Tunnel Configuration

Add a hostname mapping in your existing Named Tunnel:

**Hostname:** `devdiag.leoklemet.com`  
**Service URL:** `http://devdiag-http:8080`  
**Network:** `infra_net`

Your tunnel config should include:

```yaml
ingress:
  - hostname: devdiag.leoklemet.com
    service: http://devdiag-http:8080
  # ... other hostnames ...
  - service: http_status:404
```

**Verify External Access:**
```bash
curl -s https://devdiag.leoklemet.com/healthz | jq .
```

## Per-Project Configuration

### ApplyLens Backend (.env)

```bash
DEVDIAG_BASE=https://devdiag.leoklemet.com
DEVDIAG_ENABLED=1
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=applylens.app,.applylens.app,api.applylens.app
DEVDIAG_JWT=<service-account-JWT>
```

### LedgerMind Backend (.env)

```bash
DEVDIAG_BASE=https://devdiag.leoklemet.com
DEVDIAG_ENABLED=1
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,app.ledger-mind.org,api.ledger-mind.org
DEVDIAG_JWT=<service-account-JWT>
```

### Portfolio Backend (.env)

```bash
DEVDIAG_BASE=https://devdiag.leoklemet.com
DEVDIAG_ENABLED=1
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=.leoklemet.com,www.leoklemet.com
DEVDIAG_JWT=<service-account-JWT>
```

**Note:** Each project keeps its own backend proxy with local allowlist for defense-in-depth.

## CI Configuration

### HTTP Path (Shared Service)

```yaml
name: DevDiag Quickcheck (HTTP)
on: { pull_request: { branches: ["main"] } }
jobs:
  devdiag:
    runs-on: ubuntu-latest
    env:
      DEVDIAG_BASE: https://devdiag.leoklemet.com
      DEVDIAG_JWT: ${{ secrets.DEVDIAG_JWT }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Health & selfcheck
        run: |
          curl -fsS "$DEVDIAG_BASE/healthz" | jq .
          curl -fsS "$DEVDIAG_BASE/selfcheck" | jq .
      
      - name: Probe site
        run: |
          body='{"url":"https://applylens.app","preset":"app","tenant":"applylens"}'
          hdr=("-H" "content-type: application/json")
          [ -n "$DEVDIAG_JWT" ] && hdr+=("-H" "authorization: Bearer $DEVDIAG_JWT")
          curl -fsS -X POST "$DEVDIAG_BASE/diag/run" "${hdr[@]}" -d "$body" > diag.json
          echo "### Top problem codes" >> $GITHUB_STEP_SUMMARY
          jq -r '.result.problems[]?.code' diag.json | sort | uniq -c | sort -nr | head -20 | sed 's/^/* /' >> $GITHUB_STEP_SUMMARY || true
          jq -e '(.result.problems // [] | length) < 25' diag.json
```

### MCP Stdio Path (Pure CLI)

**No changes needed** - MCP stdio runs locally without port conflicts:

```yaml
name: DevDiag Quickcheck (MCP stdio)
on: { pull_request: { branches: ["main"] } }
jobs:
  mcp-probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: |
          pip install "mcp-devdiag[playwright,export]==0.2.1" jq
          python scripts/mcp_probe.py --url https://applylens.app --preset app --pretty > diag.json
          echo "### Top problem codes" >> $GITHUB_STEP_SUMMARY
          jq -r '.problems[]?.code' diag.json | sort | uniq -c | sort -nr | head -20 | sed 's/^/* /' >> $GITHUB_STEP_SUMMARY || true
          jq -e '(.problems // [] | length) < 25' diag.json
```

## Observability

### Prometheus Scrape Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'devdiag-http'
    scrape_interval: 30s
    static_configs:
      - targets: ['devdiag.leoklemet.com']
    scheme: https
    metrics_path: /metrics
```

### Key Metrics

- `devdiag_http_up` - Service availability (1 = up)
- `devdiag_http_requests_total` - Request counter with labels (status, tenant)
- `devdiag_http_request_duration_seconds` - Latency histogram
- `devdiag_http_rate_limit_rps` - Configured rate limit
- `devdiag_http_max_concurrent` - Concurrency limit
- `devdiag_http_concurrent_requests` - Current concurrent requests

### Grafana Alerts

```yaml
groups:
  - name: devdiag
    interval: 1m
    rules:
      - alert: DevDiagDown
        expr: devdiag_http_up == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "DevDiag HTTP service is down"
          description: "DevDiag has been unavailable for 5+ minutes"
      
      - alert: DevDiagHighErrorRate
        expr: rate(devdiag_http_requests_total{status=~"5.."}[5m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High 5xx error rate on DevDiag"
          description: "{{ $value }} 5xx errors per second"
      
      - alert: DevDiagConcurrencyLimit
        expr: devdiag_http_concurrent_requests >= devdiag_http_max_concurrent
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "DevDiag at concurrency limit"
          description: "Service is rejecting requests due to MAX_CONCURRENT"
```

### Log Correlation

Enable trace headers in your backend proxies to correlate logs:

```python
# Backend proxy automatically propagates:
# - x-request-id
# - x-b3-traceid
# - x-b3-spanid
# - traceparent

# Check proxy responses for x-request-id header
# Use this ID to search logs across services
```

## Security

### Defense-in-Depth Layers

1. **Backend Proxy Allowlist** - First validation (per-project hosts)
2. **Server Global Allowlist** - `ALLOW_TARGET_HOSTS` (all allowed domains)
3. **Server Tenant Allowlist** - `TENANT_ALLOW_HOSTS_JSON` (per-tenant isolation)
4. **JWT Authentication** - JWKS-backed token validation
5. **Rate Limiting** - `RATE_LIMIT_RPS=2` per client
6. **Concurrency Limit** - `MAX_CONCURRENT=2` to protect resources
7. **SSRF Protection** - `ALLOW_PRIVATE_IP=0` blocks RFC1918

### Tenant Isolation

When a request includes `"tenant": "applylens"`:
1. Server checks `TENANT_ALLOW_HOSTS_JSON["applylens"]`
2. URL must match one of that tenant's allowed hosts
3. Prevents cross-tenant inspection

**Example:**
```json
{
  "url": "https://app.ledger-mind.org",
  "tenant": "applylens"  // ❌ Fails - wrong tenant
}
```

## Capacity Planning

**Current Configuration:**
- `MAX_CONCURRENT=2` - Runs up to 2 Playwright probes simultaneously
- `RATE_LIMIT_RPS=2` - Accepts 2 requests per second per client
- `DEVDIAG_TIMEOUT_S=180` - 3-minute timeout per probe

**Expected Load:**
- 3 projects × 2 probes/day = 6 probes/day baseline
- CI: ~10-20 probes/day (PRs + deployments)
- Ad-hoc: ~5-10 probes/day (debugging)
- **Total:** ~20-40 probes/day = well within capacity

**If Load Increases:**
- Increase `MAX_CONCURRENT` to 3-5
- Increase `RATE_LIMIT_RPS` to 5
- Add horizontal scaling (multiple containers + load balancer)

## Maintenance

### Update Service

```bash
# Pull latest image
docker compose -f docker-compose.devdiag.yml pull

# Restart with new image
docker compose -f docker-compose.devdiag.yml up -d

# Verify
curl -s https://devdiag.leoklemet.com/selfcheck | jq .
```

### View Logs

```bash
# Real-time
docker compose -f docker-compose.devdiag.yml logs -f devdiag-http

# Last 100 lines
docker compose -f docker-compose.devdiag.yml logs --tail=100 devdiag-http
```

### Restart Service

```bash
docker compose -f docker-compose.devdiag.yml restart devdiag-http
```

### Stop Service

```bash
docker compose -f docker-compose.devdiag.yml down
```

## Rollout Checklist

- [ ] Create `infra_net` network
- [ ] Deploy DevDiag HTTP service with `.env.devdiag.infra`
- [ ] Add Cloudflare Tunnel hostname: `devdiag.leoklemet.com → devdiag-http:8080`
- [ ] Enable Prometheus scrape + alerts
- [ ] Update ApplyLens backend proxy envs
- [ ] Update LedgerMind backend proxy envs
- [ ] Update Portfolio backend proxy envs
- [ ] Update ApplyLens CI to use shared base
- [ ] Update LedgerMind CI to use shared base
- [ ] Update Portfolio CI to use shared base
- [ ] Verify external access: `curl https://devdiag.leoklemet.com/healthz`
- [ ] Verify selfcheck: `curl https://devdiag.leoklemet.com/selfcheck`
- [ ] Test each tenant: `POST .../diag/run` with tenant-specific URLs
- [ ] Monitor Prometheus metrics for 24h
- [ ] Set up alerts in Grafana

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose -f docker-compose.devdiag.yml logs devdiag-http

# Verify env file
cat .env.devdiag.infra

# Test network
docker network inspect infra_net
```

### 502 Errors

```bash
# Check /selfcheck
curl -s https://devdiag.leoklemet.com/selfcheck | jq .

# Verify CLI is installed in container
docker compose -f docker-compose.devdiag.yml exec devdiag-http which mcp-devdiag
```

### Allowlist Rejections

Check both global and tenant allowlists:

```bash
# View env
docker compose -f docker-compose.devdiag.yml exec devdiag-http env | grep ALLOW

# Test probe
curl -X POST https://devdiag.leoklemet.com/diag/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_JWT' \
  -d '{"url":"https://applylens.app","preset":"app","tenant":"applylens"}'
```

### Rate Limiting

If getting 429 errors, check rate limit metrics:

```bash
curl -s https://devdiag.leoklemet.com/metrics | grep rate_limit
```

Increase `RATE_LIMIT_RPS` if needed for legitimate traffic.

## Support

For issues or questions:
- GitHub: https://github.com/leok974/mcp-devdiag/issues
- Docs: https://github.com/leok974/mcp-devdiag#readme
