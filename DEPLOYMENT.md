# DevDiag Deployment Guide

Complete deployment and rollout plan for production-safe DevDiag.

## 0. Push & Create PR

```bash
git push -u origin feat/devdiag-prod-mode
```

Open PR at: https://github.com/leok974/mcp-devdiag/pull/new/feat/devdiag-prod-mode

See `.github/pull_request_template.md` for PR body template.

---

## 1. Configure Production Posture

### Staging Environment

Copy configuration template:
```bash
cp configs/staging.devdiag.yaml devdiag.yaml
```

**Key Settings:**
```yaml
mode: staging
sampling:
  frontend_events: 0.05   # 5%
  network_spans: 0.05     # 5%
  backend_logs: "rate:10/sec"

allow_probes:
  - "GET https://staging.api.example.com/healthz"
  - "GET https://staging.api.example.com/api/ready"
  - "GET https://staging.api.example.com/api/status"
  - "POST https://staging.api.example.com/api/debug/**"
```

### Production Environment

Copy configuration template:
```bash
cp configs/prod.devdiag.yaml devdiag.yaml
```

**Key Settings:**
```yaml
mode: prod:observe
sampling:
  frontend_events: 0.02   # 2%
  network_spans: 0.02     # 2%
  backend_logs: "rate:5/sec"

allow_probes:
  - "GET https://api.example.com/healthz"
  - "GET https://api.example.com/api/ready"
  - "HEAD https://cdn.example.com/**"

redaction:
  headers_deny: [authorization, cookie, set-cookie, x-api-key]
```

---

## 2. Secrets & RBAC Setup

### Issue JWT Tokens

**Reader Token** (for most users):
```json
{
  "aud": "mcp-devdiag",
  "role": "reader",
  "sub": "user@example.com",
  "exp": 1735689600
}
```

**Operator Token** (for SRE/DevOps):
```json
{
  "aud": "mcp-devdiag",
  "role": "operator",
  "sub": "sre@example.com",
  "exp": 1735689600
}
```

### Environment Variables

```bash
# Prometheus integration (optional)
export PROM_URL=http://prometheus:9090

# Frontend capture kill-switch (optional)
export VITE_CAPTURE_DISABLED=0  # Set to 1 to disable
```

### Future: JWKS Validation

**Next PR:** Add JWKS URL + signature verification to replace stub JWT parser.

```yaml
# Future devdiag.yaml configuration
rbac:
  provider: jwks
  jwks_url: https://auth.example.com/.well-known/jwks.json
  issuer: https://auth.example.com
  audience: mcp-devdiag
```

---

## 3. Smoke Tests (Staging First)

### Set Environment Variables

```bash
export DEVDIAG_HOST=https://staging.example.com
export READER_TOKEN="<your-reader-jwt>"
export OPERATOR_TOKEN="<your-operator-jwt>"
```

### Run Automated Tests

```bash
chmod +x testing/smoke-tests.sh
./testing/smoke-tests.sh
```

### Manual Tests

#### Auth Sanity
```bash
curl -s -X POST https://staging.example.com/mcp/devdiag/get_request_diagnostics \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://staging.api.example.com/healthz",
    "method": "GET"
  }' | jq
```

**Expected:**
- HTTP 200
- `status`, `latency_ms`, `headers` fields
- CORS keys if present

#### Deny Non-Allowlisted
```bash
curl -s -X POST https://staging.example.com/mcp/devdiag/get_request_diagnostics \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/blocked",
    "method": "GET"
  }' -o /dev/null -w "%{http_code}\n"
```

**Expected:** HTTP 403

#### Metrics Hook
```bash
curl -s "https://staging.example.com/mcp/devdiag/get_metrics?window=15m" \
  -H "Authorization: Bearer $READER_TOKEN" | jq '.status?, .rates?, .latency_ms?'
```

**Expected:**
- `status: "ok"`
- `rates` with `requests_per_sec`, `errors_per_sec`
- `latency_ms` with `p50`, `p90`, `p99`

(Returns stub/adapter output if `PROM_URL` not set)

#### Policy Guard (CI)
```bash
pytest -q tests/test_devdiag_policy.py
```

**Expected:**
- 3 tests passed
- Asserts no bodies in prod
- Sampling ≤5%
- Redaction configured

---

## 4. Production Rollout (Canary)

### Phase 1: Deploy with Minimal Sampling

1. **Deploy Configuration:**
   ```bash
   kubectl create configmap devdiag-config --from-file=devdiag.yaml=configs/prod.devdiag.yaml
   ```

2. **Deploy Application:**
   ```yaml
   # kubernetes/deployment.yaml
   env:
     - name: DEVDIAG_CONFIG
       value: /etc/devdiag/devdiag.yaml
     - name: PROM_URL
       value: http://prometheus:9090
   volumeMounts:
     - name: devdiag-config
       mountPath: /etc/devdiag
   ```

3. **Enable Frontend Capture:**
   ```typescript
   // In your frontend app initialization
   import { initDevCapture } from '@/lib/devCapture';
   
   initDevCapture({
     samplingRate: 0.02,  // 2%
     endpoint: '/api/telemetry',
     redactParams: ['token', 'key', 'code', 'session']
   });
   ```

### Phase 2: Validate Canary

Monitor for 1-2 hours:

**Key Metrics:**
```promql
# Probe success rate (target: ≥99%)
sum(rate(devdiag_probe_success_total[5m])) / sum(rate(devdiag_probe_total[5m]))

# Sampling overhead (target: <0.5% CPU)
rate(container_cpu_usage_seconds_total{app="devdiag"}[5m])

# 5xx error rate (target: <1%)
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
```

**Dashboard Checklist:**
- [ ] Probe success rate ≥99%
- [ ] p90 latency for `/healthz` <300ms
- [ ] 5xx rate <1%
- [ ] CPU overhead <0.5%
- [ ] Frontend events volume acceptable (2% sampling)

### Phase 3: Gradual Rollout

1. **10% traffic** → Monitor for 2 hours
2. **50% traffic** → Monitor for 1 hour
3. **100% traffic** → Full deployment

**Rollback Trigger:**
- Probe success rate <97% sustained
- p90 latency >500ms sustained
- 5xx rate >2% sustained
- CPU overhead >1%

---

## 5. Incident Elevation (Manual)

When debugging production issues, operators can temporarily raise sampling:

### Elevate Mode
```bash
curl -s -X POST https://api.example.com/mcp/devdiag/set_mode \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "prod:incident",
    "ttl_seconds": 600
  }' | jq
```

**Auto-reverts after 10 minutes.**

### Increase Sampling (Bounded)
```bash
curl -s -X POST https://api.example.com/mcp/devdiag/set_sampling \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "frontend_events": 0.05,
    "network_spans": 0.05
  }' | jq
```

**Note:** Sampling is bounded to ≤10% to prevent overload.

### Export Snapshot
```bash
curl -s -X POST https://api.example.com/mcp/devdiag/export_snapshot \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include": ["logs", "metrics", "env"]}' \
  --output incident-$(date +%Y%m%d-%H%M%S).tar.gz
```

---

## 6. Backout Procedure

If DevDiag causes production issues:

### Step 1: Revert to Observe Mode
```bash
curl -s -X POST https://api.example.com/mcp/devdiag/set_mode \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "prod:observe"}' | jq
```

### Step 2: Reduce Sampling
```bash
curl -s -X POST https://api.example.com/mcp/devdiag/set_sampling \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "frontend_events": 0.01,
    "network_spans": 0.01
  }' | jq
```

### Step 3: Disable Frontend Capture
```bash
# Set environment variable
kubectl set env deployment/frontend VITE_CAPTURE_DISABLED=1

# Rollout restart
kubectl rollout restart deployment/frontend
```

---

## SLO Monitoring

### Service Level Objectives

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Probe Success Rate | ≥99% | <97% for 5 minutes |
| Health Endpoint p90 | <300ms | >500ms for 5 minutes |
| 5xx Error Rate | <1% | >2% sustained |
| Sampling Overhead | <0.5% CPU | >1% CPU |

### Prometheus Alerts

```yaml
# alerts/devdiag.yaml
groups:
  - name: devdiag
    interval: 30s
    rules:
      - alert: DevDiagProbeFailureRate
        expr: |
          sum(rate(devdiag_probe_success_total[5m])) / sum(rate(devdiag_probe_total[5m])) < 0.97
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DevDiag probe success rate below 97%"
          
      - alert: DevDiagHighLatency
        expr: |
          histogram_quantile(0.90, rate(http_request_duration_seconds_bucket{endpoint="/healthz"}[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DevDiag health endpoint p90 latency >500ms"
          
      - alert: DevDiagHighCPU
        expr: |
          rate(container_cpu_usage_seconds_total{app="devdiag"}[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DevDiag CPU overhead >1%"
```

---

## Post-Deployment Checklist

- [ ] Configuration deployed to staging and production
- [ ] JWT tokens issued for readers and operators
- [ ] Smoke tests passing in staging
- [ ] Canary deployment validated (1-2 hours)
- [ ] Gradual rollout completed (10% → 50% → 100%)
- [ ] Prometheus metrics integrated (optional)
- [ ] Alerts configured for SLO violations
- [ ] Runbook shared with on-call team
- [ ] Backout procedure tested in staging
- [ ] Documentation updated in wiki/confluence

---

## Support

- **Operations Runbook:** See `RUNBOOK.md`
- **Smoke Tests:** Run `testing/smoke-tests.sh`
- **Configuration Examples:** See `configs/` directory
- **Issues:** https://github.com/leok974/mcp-devdiag/issues
- **Maintainer:** @leok974
