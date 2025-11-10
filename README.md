# mcp-devdiag

Model Context Protocol server for **production-safe autonomous development diagnostics**. Provides tools for reading logs, environment state, CORS configuration, network summaries, and live probing with role-based access control.

## Features

- 🔒 **Production-Safe**: Sampling, redaction, and allowlist-based probing
- 🎯 **Role-Based Access Control (RBAC)**: Reader and Operator roles with JWT auth
- 📊 **Metrics Integration**: Prometheus/OTLP adapter for rates and latencies
- 🔍 **Smart Probing**: Allow-listed URL diagnostics with header redaction
- 📈 **Adaptive Sampling**: Configurable rates for dev, staging, and production
- 🛡️ **Security First**: No request/response bodies in prod, sensitive header filtering

## Scope

### Supported Environments

- **Development**: Full logging, no sampling (100%), unrestricted access
- **Staging**: Medium sampling (5-10%), read-only for most users
- **Production**: Minimal sampling (1-5%), strict allowlists, audit logging

### Operating Modes

- `dev` - Full access, no restrictions
- `prod:observe` - Read-only metrics and logs with sampling
- `prod:incident` - Temporary elevated access with TTL auto-revert

## Installation

```bash
# From GitHub
pip install "mcp-devdiag @ git+https://github.com/leok974/mcp-devdiag.git@v0.1.0"

# From source
pip install -e .
```

## Quick Start

**Install:**
```bash
pip install mcp-devdiag
```

**Run:**
```bash
mcp-devdiag --stdio
```

**Configure VS Code** (`settings.json`):
```json
{
  "mcpServers": {
    "mcp-devdiag": {
      "command": "mcp-devdiag",
      "args": ["--stdio"]
    }
  }
}
```

### 60-Second Smoke Test (Copy/Paste)

```bash
# Set once
BASE="$DEVDIAG_URL"                 # e.g. https://diag.example.com
JWT="$DEVDIAG_READER_JWT"           # reader token (JWKS-backed)
APP="https://app.example.com"       # target app base

# 1) HTTP-only quickcheck (CI safe)
curl -s -X POST "$BASE/mcp/diag/quickcheck" \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d "{\"url\":\"$APP/chat/\"}" | jq

# 2) Full status with score + fixes
curl -s -G "$BASE/mcp/diag/status_plus" \
  --data-urlencode "base_url=$APP" \
  -H "Authorization: Bearer $JWT" | jq

# 3) Probe schema (for client typing)
curl -s "$BASE/mcp/diag/schema/probe_result" \
  -H "Authorization: Bearer $JWT" | jq
```

## Configuration

### Minimal devdiag.yaml Skeleton (Any Project)

```yaml
mode: prod:observe
tenant: default
allow_probes:
  - "GET https://app.example.com/healthz"
  - "GET https://app.example.com/api/ready"
  - "HEAD https://cdn.example.com/**"
sampling:
  frontend_events: 0.02
  network_spans: 0.02
retention:
  logs_ttl_days: 7
  metrics_ttl_days: 30
rbac:
  provider: jwt
  jwks_url: "https://auth.example.com/.well-known/jwks.json"
  roles:
    - name: reader
      can: [get_status, get_network_summary, get_metrics, get_request_diagnostics]
    - name: operator
      can: ["*"]
redaction:
  headers_deny: [authorization, cookie, set-cookie, x-api-key]
diag:
  portal_roots: ["#__PORTAL_ROOT__", "#toast-root", "#__NEXT_PORTAL__"]
  overlay_min_width_pct: 0.85
  overlay_min_height_pct: 0.50
  handshake: { message_types: ["chat:ready","embed:ready"], timeout_ms: 3000 }
  csp:
    must_include:
      - directive: "frame-ancestors"
        any_of: ["'self'", "https://*.example.com"]
    forbidden_xfo: ["DENY"]
```

### Full Configuration Example

Create `devdiag.yaml` in your project root:

```yaml
mode: prod:observe
tenant: yourapp
allow_probes:
  - "GET https://api.yourapp.com/healthz"
  - "HEAD https://cdn.yourapp.com/**"
sampling:
  frontend_events: 0.02  # 2%
  network_spans: 0.02    # 2%
  backend_logs: "rate:5/sec"
retention:
  logs_ttl_days: 7
  metrics_ttl_days: 30
rbac:
  provider: jwt
  roles:
    - name: reader
      can: [get_status, get_network_summary, get_metrics]
    - name: operator
      can: ["*"]
redaction:
  headers_deny: [authorization, cookie, set-cookie, x-api-key]
  path_params_regex: ["^/users/\\d+", "^/tokens/[^/]+"]
  query_keys_deny: [token, key, code]
```

## Usage

### Run MCP Server

```bash
mcp-devdiag --stdio
```

### VS Code / Copilot Integration

Add to your `.vscode/settings.json`:

```json
{
  "mcpServers": {
    "mcp-devdiag": {
      "command": "mcp-devdiag",
      "args": ["--stdio"]
    }
  }
}
```

**Copilot Prompts**:
- "Run mcp.devdiag.status_plus for https://app.example.com and print fixes."
- "Quickcheck the chat path and propose nginx/header patches for any CSP problems."
- "Get the probe schema and generate TypeScript types for ProbeResult."

### Available Tools

#### Reader Role

- `get_status()` - Comprehensive diagnostics snapshot
- `get_network_summary()` - Aggregated network metrics
- `get_metrics(window)` - Prometheus-backed rates and latencies
- `get_request_diagnostics(url, method)` - Live probe (allowlist-only)
- `diag_status_plus(base_url, preset)` - Admin-grade status with scoring
- `diag_quickcheck(url)` - Fast HTTP-only CSP/embedding check (CI-safe)
- `diag_bundle(url, driver, preset)` - Multi-probe diagnostic bundle
- `diag_probe_csp_headers(url)` - CSP and iframe compatibility check
- `diag_remediation(problems)` - Get fixes for problem codes

#### Operator Role

- `set_mode(mode, ttl_seconds)` - Change operating mode
- `export_snapshot()` - Bundle logs for incident analysis
- `compare_envs(a, b)` - Diff environment configurations

### HTTP API Examples

#### One-Shot Smoke Test (Copy/Paste)

```bash
# Set once
BASE="$DEVDIAG_URL"        # e.g., https://diag.example.com
JWT="$DEVDIAG_READER_JWT"  # reader token
APP="https://app.example.com"

# HTTP-only quickcheck (CI-safe)
curl -s -X POST "$BASE/mcp/diag/quickcheck" \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d "{\"url\":\"$APP/chat/\"}" | jq

# Status + scoring + fix recipes
curl -s -G "$BASE/mcp/diag/status_plus" \
  --data-urlencode "base_url=$APP" \
  -H "Authorization: Bearer $JWT" | jq

# ProbeResult schema (client integration)
curl -s "$BASE/mcp/diag/schema/probe_result" \
  -H "Authorization: Bearer $JWT" | jq
```

If `ok:false` and `score>0`, you'll get `fixes{code:[steps...]}` ready to surface in UIs.

#### Targeted CSP check (CI use)

```bash
# CSP headers validation for chat embedding
curl -s -X POST "$HOST/mcp/diag/probe_csp_headers" \
  -H "Authorization: Bearer $READER" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://app.example.com/chat/"}' | jq
```

#### Bundle with preset

```bash
# Full diagnostic bundle with "app" preset
curl -s -X POST "$HOST/mcp/diag/bundle" \
  -H "Authorization: Bearer $READER" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://app.example.com", "preset":"app"}' | jq
```

## Limitations

### Production Constraints

1. **No Request/Response Bodies**: Body capture is disabled by design in `prod:*` modes
2. **Sampling Only**: High-volume endpoints sampled at ≤5% to minimize overhead
3. **Allowlist Probing**: Only pre-approved URLs can be probed via `get_request_diagnostics`
4. **Header Redaction**: Sensitive headers (auth, cookies) automatically filtered
5. **Rate Limits**: Backend log tailing limited to 5 lines/second

### Privacy & Security

- **JWT Validation**: Currently uses lightweight JWT parsing; deploy with full JWKS validation
- **Audit Logging**: All operator actions logged to OTLP/S3
- **TTL Auto-Revert**: Incident mode automatically reverts after configured TTL

## Operations

### RBAC Roles

- **Reader**: Read-only access to metrics, logs, and summaries (default for all users)
- **Operator**: Can change modes, export snapshots, and compare environments

### Incident Mode

Temporarily elevate logging/sampling for active incidents:

```python
set_mode("prod:incident", ttl_seconds=3600)  # Auto-revert after 1 hour
```

### Metrics Integration

Set `PROM_URL` environment variable:

```bash
export PROM_URL=http://prometheus:9090
mcp-devdiag --stdio
```

#### Grafana Quick Panels

Paste these into a Grafana dashboard:

**Stat Panel**: HTTP 5xx Rate
- Query: `sum(rate(http_requests_total{code=~"5.."}[5m]))`
- Unit: req/s
- Thresholds: red > 0.5

**Stat Panel**: HTTP 4xx Rate
- Query: `sum(rate(http_requests_total{code=~"4.."}[5m]))`
- Unit: req/s
- Thresholds: warn > 2.0

**Gauge**: Probe Success
- Query: `avg(probe_success{job=~"blackbox.*"})`
- Min: 0, Max: 1
- Thresholds: red < 0.98

**Bar Gauge**: Top Error Buckets
- Data Source: DevDiag JSON API
- Endpoint: `/mcp/diag/status_plus?base_url=...`
- Map `.problems[]` counts

**Tip**: Expose DevDiag as a Grafana JSON API data source and query `status_plus` directly.

#### Grafana JSON-API Datasource

Configure as a Grafana datasource:

**Query URL**:
```
https://<diag-host>/mcp/diag/status_plus?base_url=${__url.params:app}
```

**Headers**:
```
Authorization: Bearer ${secret:DEVDIAG_READER_JWT}
```

**Panel Paths**:
- Problems: `$.problems`
- Score: `$.score`
- Fixes: `$.fixes`
- Severity: `$.severity`

## Client SDKs

### TypeScript

Generate types from JSON schema:
```bash
npx quicktype -s schema -o src/types/devdiag.ts mcp_devdiag/schemas/probe_result.json
```

Or use the ready-made SDK:
```typescript
// Install dependencies first: npm install zod
// See docs/examples/devdiag.ts
import { statusPlus, quickcheck } from './devdiag';

const client = { baseUrl: "https://diag.example.com", jwt: process.env.DEVDIAG_JWT! };
const result = await statusPlus(client, "https://app.example.com", "full");
```

### Python

```python
# See docs/examples/devdiag_client.py
from devdiag_client import DevDiagClient

client = DevDiagClient(base_url=os.environ["DEVDIAG_URL"], jwt=os.environ["DEVDIAG_JWT"])
result = client.status_plus("https://app.example.com", preset="full")
```

Copy SDK files from `docs/examples/` to your project.

## Deployment

### Docker Compose

```bash
# See deployments/docker-compose.yml
docker-compose up -d
```

### Kubernetes

```bash
# See deployments/kubernetes.yaml
kubectl apply -f deployments/kubernetes.yaml
```

**Health Checks**:
- Liveness: `GET /healthz` (port 8000, delay 10s, period 10s)
- Readiness: `GET /ready` (port 8000, delay 5s, period 5s)

## Prebuilt Assets

### Grafana Dashboard

Import `dashboards/devdiag.json` for instant monitoring with:
- HTTP 5xx rate (threshold: 0.5 req/s)
- Probe success rate (threshold: 95%)
- Top probe problems
- Response latency p90 (threshold: 300ms/500ms)

### Postman Collection

Import `postman/devdiag.postman_collection.json` for quick testing:
- Set `DEVDIAG_JWT` environment variable
- Configure `BASE_URL` and `TARGET_URL`
- Includes: quickcheck, status_plus, remediation, bundle, schema, individual probes

## Suggested Next Steps (Optional)

Future enhancements to consider:

1. **OpenAPI summaries** on routes for tool reflection
2. **Playwright driver** behind `diag.browser_enabled=true` for runtime DOM checks
3. **Suppressions** in `devdiag.yaml`:
   ```yaml
   suppress:
     - code: "PORTAL_ROOT_MISSING"
       reason: "Native toasts; no portal needed"
   ```

See `TODO.md` for full roadmap with effort estimates.

## Development

```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
pip install -r requirements-dev.txt

# Run tests
pytest

# Run policy tests
pytest tests/test_devdiag_policy.py -v

# Lint
ruff check .
ruff format .

# Type check
mypy mcp_devdiag
```

## Files Used

- `.tasteos_logs/backend.log` - Backend application logs
- `.tasteos_logs/frontend.log` - Frontend console logs
- `.tasteos_logs/network.jsonl` - Network request telemetry
- `.tasteos_logs/env.json` - Environment configuration snapshot

## License

MIT License - see LICENSE file
