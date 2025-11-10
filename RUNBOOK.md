# DevDiag Operations Runbook

## Quick Reference

### Roles & Capabilities

#### Reader Role
- `get_status()` - Comprehensive diagnostics snapshot
- `get_network_summary()` - Aggregated network metrics
- `get_metrics(window)` - Prometheus-backed rates and latencies
- `get_request_diagnostics(url, method)` - Live probe (allowlist-only)

#### Operator Role
- All reader capabilities, plus:
- `set_mode(mode, ttl_seconds)` - Change operating mode
- `set_sampling(...)` - Adjust sampling rates (bounded)
- `export_snapshot()` - Bundle logs for incident analysis
- `compare_envs(a, b)` - Diff environment configurations

---

## Common Operations

### 1. Probe Health Endpoint

**As Reader:**
```bash
curl -s -X POST https://<host>/mcp/devdiag/get_request_diagnostics \
  -H "Authorization: Bearer <READER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/healthz",
    "method": "GET"
  }' | jq
```

**Expected Response:**
```json
{
  "status": 200,
  "latency_ms": 45,
  "headers": {
    "content-type": "application/json",
    "x-request-id": "abc123"
  },
  "cors": {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, POST"
  }
}
```

**Note:** Only URLs matching `allow_probes` in `devdiag.yaml` will succeed. Others return 403.

---

### 2. Get Metrics

**As Reader:**
```bash
curl -s "https://<host>/mcp/devdiag/get_metrics?window=15m" \
  -H "Authorization: Bearer <READER_TOKEN>" | jq
```

**Expected Response:**
```json
{
  "status": "ok",
  "window": "15m",
  "rates": {
    "requests_per_sec": 1250.3,
    "errors_per_sec": 12.1
  },
  "latency_ms": {
    "p50": 85,
    "p90": 210,
    "p99": 450
  }
}
```

**Note:** Requires `PROM_URL` environment variable. Returns stub data otherwise.

---

### 3. Elevate for Incident (Temporary)

**As Operator:**
```bash
# Raise to incident mode for 10 minutes (auto-reverts)
curl -s -X POST https://<host>/mcp/devdiag/set_mode \
  -H "Authorization: Bearer <OPERATOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "prod:incident",
    "ttl_seconds": 600
  }' | jq
```

**Follow-up: Increase Sampling (bounded to ≤10%)**
```bash
curl -s -X POST https://<host>/mcp/devdiag/set_sampling \
  -H "Authorization: Bearer <OPERATOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "frontend_events": 0.05,
    "network_spans": 0.05
  }' | jq
```

**Auto-Revert:** After TTL expires, mode automatically reverts to `prod:observe` and sampling to configured defaults.

---

### 4. Export Snapshot for Analysis

**As Operator:**
```bash
curl -s -X POST https://<host>/mcp/devdiag/export_snapshot \
  -H "Authorization: Bearer <OPERATOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"include": ["logs", "metrics", "env"]}' \
  --output incident-$(date +%Y%m%d-%H%M%S).tar.gz
```

Contains:
- Backend/frontend logs (sampled)
- Network telemetry (sampled)
- Environment configuration
- Current metrics snapshot

---

## Incident Response

### Scenario: Elevated Error Rate

1. **Check Metrics:**
   ```bash
   curl -s "https://<host>/mcp/devdiag/get_metrics?window=5m" \
     -H "Authorization: Bearer <READER_TOKEN>" | jq '.rates.errors_per_sec'
   ```

2. **Probe Failing Endpoint:**
   ```bash
   # Must be in allow_probes list
   curl -s -X POST https://<host>/mcp/devdiag/get_request_diagnostics \
     -H "Authorization: Bearer <READER_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://api.example.com/healthz","method":"GET"}' | jq
   ```

3. **Elevate if Needed (Operator):**
   ```bash
   curl -s -X POST https://<host>/mcp/devdiag/set_mode \
     -H "Authorization: Bearer <OPERATOR_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"mode":"prod:incident","ttl_seconds":600}' | jq
   ```

4. **Export Logs for Analysis:**
   ```bash
   curl -s -X POST https://<host>/mcp/devdiag/export_snapshot \
     -H "Authorization: Bearer <OPERATOR_TOKEN>" \
     --output incident-export.tar.gz
   ```

---

## SLO Monitoring

### Key Indicators

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Probe Success Rate | ≥99% | <97% for 5m |
| Health Endpoint p90 | <300ms | >500ms for 5m |
| 5xx Error Rate | <1% | >2% sustained |
| Sampling Overhead | <0.5% CPU | >1% CPU |

### Queries (Prometheus)

**Probe Success Rate:**
```promql
sum(rate(devdiag_probe_success_total[5m])) / sum(rate(devdiag_probe_total[5m]))
```

**Health Endpoint p90:**
```promql
histogram_quantile(0.90, rate(http_request_duration_seconds_bucket{endpoint="/healthz"}[5m]))
```

**5xx Rate:**
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
```

---

## Backout Procedure

If DevDiag causes issues:

### 1. Revert to Observe Mode
```bash
curl -s -X POST https://<host>/mcp/devdiag/set_mode \
  -H "Authorization: Bearer <OPERATOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"prod:observe"}' | jq
```

### 2. Reduce Sampling to Minimum
```bash
curl -s -X POST https://<host>/mcp/devdiag/set_sampling \
  -H "Authorization: Bearer <OPERATOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"frontend_events":0.01,"network_spans":0.01}' | jq
```

### 3. Disable Frontend Capture (App Deployment)
Set environment variable:
```bash
VITE_CAPTURE_DISABLED=1
```

Redeploy frontend to disable telemetry capture.

---

## Troubleshooting

### 403 Forbidden on Probe
**Cause:** URL not in `allow_probes` list or insufficient role.

**Fix:**
1. Verify URL matches allowlist pattern in `devdiag.yaml`
2. Check JWT role (`reader` has probe access, but URL must be allowed)

### No Metrics Data
**Cause:** `PROM_URL` environment variable not set.

**Fix:**
```bash
export PROM_URL=http://prometheus:9090
# Restart DevDiag server
```

### JWT Validation Fails
**Cause:** Token expired or invalid signature.

**Fix:**
1. Check token expiration: `jwt decode <TOKEN>`
2. Verify `aud` claim is `"mcp-devdiag"`
3. Ensure `role` claim is `"reader"` or `"operator"`

---

## Configuration Files

### Staging
**Location:** `configs/staging.devdiag.yaml`

**Key Settings:**
- Mode: `staging`
- Sampling: 5% frontend/network, 10 logs/sec
- Relaxed probe allowlist

### Production
**Location:** `configs/prod.devdiag.yaml`

**Key Settings:**
- Mode: `prod:observe`
- Sampling: 2% frontend/network, 5 logs/sec
- Strict probe allowlist, comprehensive redaction

---

## Security Notes

1. **JWT Validation:** Current implementation uses lightweight parsing. **Deploy with JWKS validation** for production.
2. **Audit Logging:** All operator actions should be logged to OTLP/S3.
3. **Rate Limiting:** Consider adding rate limits to probe endpoints.
4. **Secrets Management:** Store JWT signing keys in vault (HashiCorp Vault, AWS Secrets Manager).

---

## Support Contacts

- **On-call Engineering:** [Your PagerDuty/OpsGenie link]
- **Security Team:** [Security contact]
- **DevDiag Maintainer:** @leok974
