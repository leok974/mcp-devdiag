# mcp-devdiag

[![PyPI version](https://img.shields.io/pypi/v/mcp-devdiag.svg)](https://pypi.org/project/mcp-devdiag/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-devdiag.svg)](https://pypi.org/project/mcp-devdiag/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-31_passing-brightgreen.svg)](#)
[![Release](https://img.shields.io/github/v/release/leok974/mcp-devdiag)](https://github.com/leok974/mcp-devdiag/releases)
[![HTTP Smoke](https://github.com/leok974/mcp-devdiag/actions/workflows/devdiag-http-smoke.yml/badge.svg)](https://github.com/leok974/mcp-devdiag/actions/workflows/devdiag-http-smoke.yml)
[![MCP Quickcheck](https://github.com/leok974/mcp-devdiag/actions/workflows/devdiag-mcp-quickcheck.yml/badge.svg)](https://github.com/leok974/mcp-devdiag/actions/workflows/devdiag-mcp-quickcheck.yml)

Model Context Protocol server for **production-safe autonomous development diagnostics**. Provides tools for reading logs, environment state, CORS configuration, network summaries, and live probing with role-based access control.

**Now includes:** [Standalone HTTP Server](#http-server) for EvalForge and CI integration (FastAPI + JWT + rate limiting).

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
# Latest release
pip install mcp-devdiag

# Pinned version
pip install "mcp-devdiag==0.2.0"

# With optional extras for add-ons
pip install "mcp-devdiag[playwright,export]"  # DOM checks + S3 export

# From GitHub
pip install "mcp-devdiag @ git+https://github.com/leok974/mcp-devdiag.git@v0.2.0"

# From source
pip install -e .
```

### Optional Extras

Install add-ons for enhanced diagnostics:

```bash
# Playwright driver (runtime DOM/console checks - staging only)
pip install "mcp-devdiag[playwright]"
playwright install chromium

# S3 export (redacted incident snapshots)
pip install "mcp-devdiag[export]"

# All add-ons
pip install "mcp-devdiag[playwright,export]"
```

See [`docs/ADDONS.md`](docs/ADDONS.md) for complete add-ons documentation.

## Quick Start

**Consumer quickstart** (copy/paste):

```bash
# Install
pip install mcp-devdiag==0.2.0

# Run MCP server
mcp-devdiag --stdio
# Or: python -m mcp_devdiag --stdio
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

**Minimal config** (`devdiag.yaml`):
```yaml
mode: dev
tenant: my-app
rbac:
  provider: jwt
  jwks_url: "https://auth.example.com/.well-known/jwks.json"
allow_probes:
  - "GET https://api.example.com/**"
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

### Migration (0.1.x → 0.2.0)

If upgrading from v0.1.x:

**Required changes to `devdiag.yaml`:**
- Add `rbac.jwks_url: "https://auth.example.com/.well-known/jwks.json"`
- Add `allow_probes:` with explicit URL patterns you permit
- Add `diag:` block (optional, for presets/overrides)

**Optional new features to adopt:**
- New endpoints: `/mcp/diag/status_plus` (score + fixes), `/mcp/diag/quickcheck` (CI HTTP-only)
- Import `dashboards/devdiag.json` into Grafana for instant monitoring
- Enable `.github/workflows/devdiag-quickcheck.yml` for PR validation
- Use `/mcp/diag/schema/probe_result` for TypeScript type generation

**Breaking changes:** None. `get_status` remains backward-compatible; `status_plus` adds new fields.

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

## HTTP Server

**Standalone FastAPI wrapper** for calling DevDiag from EvalForge web app and CI pipelines. Includes JWT auth (JWKS), rate limiting, and SSRF protection.

### Quick Start

```bash
# Local development (no auth)
cd apps/devdiag-http
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# Test
curl -s http://127.0.0.1:8080/healthz
curl -s -X POST "http://127.0.0.1:8080/diag/run" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.leoklemet.com","preset":"app"}' | jq .
```

### Docker Compose

```bash
docker compose -f docker-compose.devdiag.yml up -d --build
curl -s http://127.0.0.1:8080/healthz
```

### Configuration

Environment variables:
- `JWKS_URL`: JWKS endpoint for JWT validation (empty = auth disabled for local dev)
- `JWT_AUD`: JWT audience claim (default: `mcp-devdiag`)
- `RATE_LIMIT_RPS`: Requests per second limit (default: 2.0)
- `ALLOW_PRIVATE_IP`: Allow private/loopback IPs (default: 0, set 1 for local testing)
- `ALLOWED_ORIGINS`: CORS origins (comma-separated)
- `ALLOW_TARGET_HOSTS`: Server-side allowlist for target URLs (supports `.domain.com`, exact hosts, `pr-*.domain.com` globs)
- `DEVDIAG_CLI`: CLI binary name (default: `mcp-devdiag`)
- `DEVDIAG_TIMEOUT_S`: CLI timeout (default: 180s)
- `MAX_CONCURRENT`: Max concurrent runs (default: 2)

### API Endpoints

**`POST /diag/run`** - Run diagnostics on a URL

Request:
```json
{
  "url": "https://example.com",
  "preset": "app",
  "suppress": ["CSP_FRAME_ANCESTORS"],
  "extra_args": ["--verbose"]
}
```

Response:
```json
{
  "ok": true,
  "url": "https://example.com",
  "preset": "app",
  "result": {"problems": [], "fixes": {}, "evidence": {}}
}
```

**`GET /healthz`** - Health check (also supports HEAD)  
**`GET /selfcheck`** - Verify CLI availability (useful for debugging 502 errors)  
**`GET /ready`** - Readiness probe (CLI + allowlist + JWKS checks, use for K8s)  
**`GET /metrics`** - Prometheus-compatible metrics  
**`GET /probes`** - List available presets

### Deployment

**Cloud Run:**
```bash
gcloud run deploy devdiag-http \
  --image ghcr.io/leok974/mcp-devdiag/devdiag-http:latest \
  --set-env-vars JWKS_URL=https://YOUR-IDP/.well-known/jwks.json \
  --set-env-vars JWT_AUD=mcp-devdiag \
  --set-env-vars ALLOWED_ORIGINS=https://evalforge.app \
  --set-env-vars ALLOW_TARGET_HOSTS=.ledger-mind.org
```

**Fly.io / Render:** See `apps/devdiag-http/README.md` for full deployment guides.

### EvalForge Integration

**Option 1: Direct Frontend Calls**

```typescript
const response = await fetch('http://127.0.0.1:8080/diag/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${jwt}`,
  },
  body: JSON.stringify({url: 'https://example.com', preset: 'app'}),
});
const data = await response.json();
```

**Option 2: Backend Proxy (Recommended)**

Hides JWT from frontend, adds host allowlist validation, and provides retry logic.

```python
# apps/backend/app/routes/devdiag_proxy.py
from app.routes import devdiag_proxy

app.include_router(devdiag_proxy.router, tags=["ops"])
```

```bash
# Environment
DEVDIAG_BASE=https://devdiag-http.example.run.app
DEVDIAG_JWT=
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,app.ledger-mind.org
```

```typescript
// Frontend calls backend proxy (no JWT needed)
const res = await fetch('/ops/diag', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({url: 'https://app.ledger-mind.org', preset: 'app'}),
});
```

Full documentation:
- **HTTP Server**: [apps/devdiag-http/README.md](apps/devdiag-http/README.md)
- **Backend Proxy**: [apps/backend/app/routes/README.md](apps/backend/app/routes/README.md)

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

## Add-ons

### Playwright Driver (Staging Only)

Enable runtime DOM inspection and console log capture:

```yaml
# devdiag.yaml
diag:
  browser_enabled: true  # Enable Playwright driver
```

```bash
# Install Playwright
pip install playwright
playwright install chromium

# Use in probes
curl -s -X POST "$BASE/mcp/diag/bundle" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://app.example.com","driver":"playwright","preset":"full"}' | jq
```

**Note**: Only enable in dev/staging. Production should use HTTP-only driver.

### Suppressions

Ignore known/intentional issues in diagnostics:

```yaml
# devdiag.yaml
diag:
  suppress:
    - code: "PORTAL_ROOT_MISSING"
      reason: "App uses native toasts; no portal needed"
    - code: "FRAMEWORK_VERSION_MISMATCH"
      reason: "Deliberate canary test in staging"
```

Suppressed problems are filtered from bundle results but logged for audit.

### S3 Export

Export redacted diagnostic bundles for incident analysis:

```yaml
# devdiag.yaml
export:
  s3_bucket: "mcp-devdiag-artifacts"
  region: "us-east-1"
```

```bash
# Export snapshot (operator role required)
pip install boto3

curl -s -X POST "$BASE/mcp/devdiag/export_snapshot" \
  -H "Authorization: Bearer $OPERATOR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"problems":["CSP_MISSING"],"score":5,"evidence":{}}' | jq
```

Exports are automatically redacted (no headers, bodies, or auth tokens) and encrypted with AES256-SSE.

### Closed-Loop Learning

DevDiag includes **closed-loop learning** to automatically learn which fixes work in which environments. When enabled:

- Every diagnostic run is recorded (problems, evidence, environment fingerprint)
- When a problem disappears after a fix, DevDiag credits that fix with success
- Future suggestions rank fixes by **confidence score** (support × environment similarity)

**Configuration** (`devdiag.yaml`):

```yaml
learn:
  enabled: true
  store: "sqlite:///devdiag.db"      # or PostgreSQL connection string
  privacy:
    hash_targets: true                # hash URLs to target_hash (privacy-first)
    keep_evidence_keys: ["csp", "xfo", "framework", "server", "routes"]
  retention_days: 180                 # data retention (default 6 months)
  min_support: 2                      # min fix successes before suggesting
  alpha: 0.6                          # confidence α for support scaling
  beta: 0.7                           # confidence β for similarity weighting
```

**Privacy Guarantees**:

- ✅ **No bodies or secrets stored** - only safe evidence keys (CSP, framework, etc.)
- ✅ **Target URLs hashed** when `hash_targets: true` (default)
- ✅ **No request/response data** - only problem codes and fix recipes
- ✅ **Tenant isolation** - each tenant's learning data is separate
- ✅ **Configurable retention** - auto-purge old data (default 180 days)

**How it works**:

1. **Record**: Every `diag_status_plus()` call records problems + environment
2. **Detect**: If problems disappear on next run, credit the applied fix
3. **Learn**: Build confidence scores based on:
   - **Support** - how many times this fix worked
   - **Similarity** - how similar the current environment is to past successes
4. **Suggest**: Rank fixes by confidence when same problem appears again

**Example usage**:

```python
# status_plus automatically records runs when learning is enabled
result = await diag_status_plus(base_url="https://app.example.com", preset="chat")

# Manually query suggestions for a specific problem
from mcp_devdiag.tools_learn import learn_suggest
suggestions = await learn_suggest(
    problem_code="CSP_INLINE_BLOCKED",
    evidence={"framework": "react@18.3.1", "xfo": "DENY"},
    tenant="my-app"
)
# Returns: [{"fix_code": "FIX_CSP_NONCE", "confidence": 0.85, "support": 12}, ...]
```

**Opt-out**: Set `learn.enabled: false` to disable learning. No data is collected when disabled.

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

## Usage Patterns

### MCP (stdio) for Dev/IDE & Pure-CLI CI

Use **`scripts/mcp_probe.py`** to talk directly to `mcp-devdiag --stdio` without the HTTP server:

```bash
# Run probe via MCP stdio
python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty

# CI usage with policy gate
python scripts/mcp_probe.py --url https://app.example.com --preset app \
  --max-problems 25 > diag.json

# Customize CLI binary and timeout
export MCP_DEV_DIAG_BIN="mcp-devdiag"
export MCP_PROBE_TIMEOUT_S=240
python scripts/mcp_probe.py --url https://example.com --preset full
```

**Environment Variables:**
- `MCP_DEV_DIAG_BIN` - CLI binary name (default: `mcp-devdiag`)
- `MCP_PROBE_TIMEOUT_S` - Timeout in seconds (default: `180`)

**Exit Codes:**
- `0` - Success
- `1` - Error (CLI not found, invalid response)
- `2` - Too many problems (when `--max-problems` threshold exceeded)

**VS Code Task Integration:**

See `.vscode/tasks.json` for quick access via `Tasks: Run Task` menu.

**Full documentation:** [docs/MCP_STDIO.md](docs/MCP_STDIO.md)

### HTTP for Apps/Teams

Use the **HTTP server** (`apps/devdiag-http`) when you need:
- JWT authentication (JWKS)
- Rate limiting (default: 2 RPS)
- SSRF protection
- Host allowlisting
- Multi-tenant isolation
- Backend proxy pattern (hide JWT from frontend)

See [HTTP Server](#http-server) section above.

## Compatibility

| Area                 | Default | Notes                                   |
|----------------------|---------|-----------------------------------------|
| Runtime              | HTTP    | Browser driver optional (Playwright)    |
| Auth                 | JWKS    | RS256; aud = `mcp-devdiag`              |
| Prod capture         | Off     | No bodies ever; headers redacted        |
| Probes               | CSP/DOM | Degrades gracefully in HTTP-only        |
| CI                   | Quick   | `/mcp/diag/quickcheck` or `scripts/mcp_probe.py` |

## Privacy & Data Handling

- ✅ **No request bodies captured** in any mode
- ✅ **Auth headers and cookies** are never persisted; deny-list enforced server-side
- ✅ **Probe allow-list** must explicitly include each URL pattern
- ✅ **SSRF guard** blocks RFC1918 + 127.0.0.0/8 + 169.254.0.0/16 by default
- ✅ **Retention** is configurable; default 7 days logs / 30 days metrics

See `SECURITY.md` for complete security documentation and compliance notes.

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

### Publishing to PyPI

For maintainers releasing new versions:

1. **Configure PyPI credentials** (one-time setup):
   ```bash
   # Create ~/.pypirc (Linux/Mac) or C:\Users\USERNAME\.pypirc (Windows)
   # Get tokens from: https://pypi.org/manage/account/token/
   
   [distutils]
   index-servers =
       pypi
       testpypi
   
   [pypi]
   username = __token__
   password = YOUR_PYPI_API_TOKEN_HERE
   
   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = YOUR_TESTPYPI_API_TOKEN_HERE
   ```

2. **Build and publish**:
   ```bash
   # Build distributions
   python -m build
   
   # Validate packages
   twine check dist/*
   
   # Test upload (recommended first)
   twine upload --repository testpypi dist/mcp_devdiag-X.Y.Z*
   
   # Production upload
   twine upload dist/mcp_devdiag-X.Y.Z*
   ```

3. **Verify installation**:
   ```bash
   pip install mcp-devdiag==X.Y.Z
   mcp-devdiag --help
   ```

## Files Used

- `.tasteos_logs/backend.log` - Backend application logs
- `.tasteos_logs/frontend.log` - Frontend console logs
- `.tasteos_logs/network.jsonl` - Network request telemetry
- `.tasteos_logs/env.json` - Environment configuration snapshot

## Security

### Secret Scanning

This repository uses [Gitleaks](https://github.com/gitleaks/gitleaks) to prevent accidental commits of secrets (API keys, tokens, passwords).

**For Contributors:**

After cloning the repository, run the setup script to install git hooks:

```bash
# Windows (PowerShell)
.\scripts\setup-git-hooks.ps1

# Linux/macOS
./scripts/setup-git-hooks.sh
```

**Manual Installation:**

```bash
# Windows
winget install gitleaks

# macOS
brew install gitleaks

# Linux
curl -sSL https://github.com/gitleaks/gitleaks/releases/download/v8.29.0/gitleaks_8.29.0_linux_x64.tar.gz -o /tmp/gitleaks.tar.gz
tar -xzf /tmp/gitleaks.tar.gz -C /tmp
sudo mv /tmp/gitleaks /usr/local/bin/
```

**Pre-Commit Hook:**

The pre-commit hook automatically scans staged files for secrets before each commit. If secrets are detected:

1. **Remove the secret** and use environment variables instead
2. **Add to `.gitleaksignore`** if it's a false positive
3. **Bypass (NOT RECOMMENDED):** `git commit --no-verify`

**CI/CD:**

GitHub Actions runs Gitleaks on every push and pull request (`.github/workflows/security-scan.yml`).

## License

MIT License - see LICENSE file
