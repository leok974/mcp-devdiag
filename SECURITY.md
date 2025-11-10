# Security Policy

## Production Security Checklist

This document outlines the security features implemented in mcp-devdiag for production deployments.

### ✅ 1. JWKS JWT Verification

**Status**: Implemented  
**Location**: `mcp_devdiag/security_jwks.py`, `mcp_devdiag/security.py`

- Real JWT verification using JWKS endpoint (python-jose)
- JWKSCache with 10-minute TTL to minimize endpoint hits
- Audience validation (`aud=mcp-devdiag`)
- Falls back to lightweight decode in dev mode when `jwks_url` not configured

**Configuration** (`devdiag.yaml`):
```yaml
rbac:
  provider: jwt
  jwks_url: "https://auth.example.com/.well-known/jwks.json"
```

**Usage**:
```python
from mcp_devdiag.security import authorize
claims = await authorize("get_status", auth_header, jwks_url=CONFIG.rbac.get("jwks_url"))
```

---

### ✅ 2. URL Allowlist Enforcement

**Status**: Implemented  
**Location**: `mcp_devdiag/tools_diag.py` (`_assert_allowed()`)

- Every diagnostic endpoint validates URLs against allowlist
- Pattern matching with wildcards (`**`)
- Raises `ValueError` if URL not in allowlist

**Configuration** (`devdiag.yaml`):
```yaml
allow_probes:
  - "GET https://api.yourapp.com/healthz"
  - "HEAD https://cdn.yourapp.com/**"
```

**Enforcement**: All probe endpoints call `_assert_allowed(url)` before execution

---

### ✅ 3. HTTP-Only Mode (CI Default)

**Status**: Implemented  
**Location**: `mcp_devdiag/probes/adapters.py`, `tools_diag.py`

- `diag_quickcheck()` forces HTTP-only driver (no JavaScript runtime)
- Default driver is `http` for all endpoints unless specified
- Playwright driver requires explicit opt-in and runtime checks

**Safety**: No DOM access, no console capture, headers/CSP only

---

### ✅ 4. Rate Limiting (Per-Tenant)

**Status**: Implemented  
**Location**: `mcp_devdiag/limits.py`

- Token bucket algorithm (default: 30 req/min, burst 5)
- Per-tenant, per-operation keys (`tenant:operation`)
- Raises `HTTPException(429)` when limit exceeded

**Integration**: 
```python
from mcp_devdiag.limits import guard
guard(CONFIG.tenant, "diag_bundle")  # Before expensive operations
```

**Applied to**: `diag_bundle`, `diag_quickcheck`, `diag_status_plus`

---

### ✅ 5. Incident TTL Auto-Revert

**Status**: Implemented  
**Location**: `mcp_devdiag/incident.py`

- Temporary mode/sampling elevation with automatic revert
- Async timer cancels previous elevations
- State tracking for TTL countdown

**Usage**:
```python
from mcp_devdiag.incident import elevate, remaining
await elevate(set_mode_fn, set_sampling_fn, ttl_s=3600, saved_snapshot)
remaining_seconds = remaining()  # Check countdown
```

**Safety**: Prevents forgotten high-fidelity modes from persisting

---

### ✅ 6. Header/Body Redaction

**Status**: Implemented  
**Location**: `mcp_devdiag/config.py`

- Headers deny-list enforced in all HTTP operations
- No request/response bodies captured in `prod:*` modes
- Query parameter filtering by key

**Configuration** (`devdiag.yaml`):
```yaml
redaction:
  headers_deny: [authorization, cookie, set-cookie, x-api-key]
  path_params_regex: ["^/users/\\d+", "^/tokens/[^/]+"]
  query_keys_deny: [token, key, code]
```

---

## Deployment Recommendations

### Minimum Security Configuration

For production deployments, ensure:

1. ✅ **JWKS URL configured** - Never use lightweight decode in prod
2. ✅ **Allowlist enforced** - Whitelist only necessary probe URLs
3. ✅ **HTTP-only default** - Avoid Playwright/browser drivers unless required
4. ✅ **Rate limits active** - Prevent abuse from single tenant
5. ✅ **Incident TTL wired** - Auto-revert after incidents
6. ✅ **Headers deny-listed** - Block sensitive headers from logs

### Optional Enhancements

- **Audit logging**: Log all operator actions to OTLP/S3
- **IP allowlisting**: Restrict MCP server access by source IP
- **Mutual TLS**: Require client certificates for JWKS endpoint
- **Secrets rotation**: Rotate JWT signing keys regularly

---

## Service Level Objectives (SLOs)

Production deployments should monitor these SLOs:

**Probe Success Rate** (5-minute window):
- **Target**: ≥ 99% success rate
- **Alert**: < 95% over 15 minutes
- **Query**: `sum(rate(http_requests_total{endpoint=~"diag_.*", status=~"2.."}[5m])) / sum(rate(http_requests_total{endpoint=~"diag_.*"}[5m]))`

**Response Latency** (5-minute window):
- **Target**: p90 < 300ms
- **Alert**: p90 > 500ms over 10 minutes
- **Query**: `histogram_quantile(0.90, rate(http_request_duration_seconds_bucket{endpoint=~"diag_.*"}[5m]))`

**HTTP 5xx Rate** (5-minute window):
- **Target**: < 0.5 req/s
- **Alert**: ≥ 1.0 req/s over 5 minutes
- **Query**: `sum(rate(http_requests_total{status=~"5.."}[5m]))`

**JWT Verification Failures** (5-minute window):
- **Target**: 0 failures
- **Alert**: ≥ 5 failures over 5 minutes
- **Query**: `sum(rate(jwt_verify_errors_total[5m]))`

---

## Vulnerability Reporting

To report security vulnerabilities, please email: **security@example.com**

Do not open public issues for security concerns.

---

## Compliance Notes

- **PCI DSS**: Headers redaction prevents card data leakage
- **GDPR**: Path/query param redaction protects user identifiers
- **SOC 2**: Audit logging and RBAC support access control requirements
- **HIPAA**: No PHI in logs with proper redaction configuration

---

## Version History

- **v0.2.0** (2025-11-10): Added JWKS verification, rate limiting, incident TTL, schema endpoint
- **v0.1.0** (2025-11-09): Initial production-safe release with RBAC and sampling
