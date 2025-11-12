# DevDiag HTTP Server

Standalone FastAPI wrapper for DevDiag with JWT auth, rate limiting, and SSRF protection.

## Quick Start

### Local Development (no auth)

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
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

## Configuration

Environment variables:

- `JWKS_URL`: JWKS endpoint for JWT validation (empty = auth disabled)
- `JWT_AUD`: JWT audience claim to verify (default: `mcp-devdiag`)
- `RATE_LIMIT_RPS`: Requests per second limit (default: 2.0)
- `ALLOW_PRIVATE_IP`: Allow private/loopback IPs (default: 0, set 1 for local testing)
- `ALLOWED_ORIGINS`: CORS origins (comma-separated, default: `http://127.0.0.1:19010,http://localhost:19010`)
- `ALLOW_TARGET_HOSTS`: Server-side allowlist for target URLs (comma-separated, supports exact, `.domain.com`, and `pr-*.domain.com` patterns)
- `DEVDIAG_CLI`: CLI binary name (default: `mcp-devdiag`)
- `DEVDIAG_TIMEOUT_S`: CLI timeout in seconds (default: 180)
- `MAX_CONCURRENT`: Maximum concurrent diagnostic runs (default: 2)

### Target Host Allowlist

`ALLOW_TARGET_HOSTS` provides server-side validation to prevent arbitrary URL scanning:

```bash
# Exact host match
ALLOW_TARGET_HOSTS=app.ledger-mind.org

# Subdomain wildcard (leading dot allows subdomains + apex)
ALLOW_TARGET_HOSTS=.ledger-mind.org
# ✅ app.ledger-mind.org
# ✅ ledger-mind.org  
# ✅ staging.ledger-mind.org

# Glob patterns (pr-*.example.com)
ALLOW_TARGET_HOSTS=pr-*.ledger-mind.org

# Mixed
ALLOW_TARGET_HOSTS=.ledger-mind.org,app.example.com,pr-*.example.com
```

**Best practice**: Use `.ledger-mind.org` for dynamic preview environments.

## API Endpoints

### `GET /healthz`
Health check endpoint (also supports HEAD).

**Response:**
```json
{"ok": true, "service": "devdiag-http", "version": "0.1.0"}
```

### `HEAD /healthz`
Lightweight health check (no body).

### `GET /selfcheck`
Quick diagnostics for ops: confirms CLI presence and prints version.

**Response (success):**
```json
{"ok": true, "cli": "mcp-devdiag", "version": "0.2.1"}
```

**Response (CLI not found):**
```json
{"ok": false, "cli": "mcp-devdiag", "message": "CLI not found in PATH"}
```

**Use case**: If you see 502 errors from `/diag/run`, check `/selfcheck` to verify the CLI is installed and accessible.

### `GET /ready`
Readiness probe combining CLI availability + allowlist + JWKS checks. Use for K8s readinessProbe or load balancer health checks.

**Response (ready):**
```json
{"ok": true}
```

**Response (not ready):**
```json
{"ok": false, "reason": "cli_missing", "cli": "mcp-devdiag"}
{"ok": false, "reason": "allowlist_empty"}
{"ok": false, "reason": "jwks_unreachable", "error": "..."}
```

**Kubernetes readinessProbe example:**
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

### `GET /metrics`
Prometheus-compatible metrics endpoint.

**Response (text/plain):**
```
# HELP devdiag_http_up 1 if server is healthy
# TYPE devdiag_http_up gauge
devdiag_http_up 1
# HELP devdiag_http_rate_limit_rps configured RPS
# TYPE devdiag_http_rate_limit_rps gauge
devdiag_http_rate_limit_rps 2.0
```

### `GET /probes`
List available probe presets.

**Response:**
```json
{
  "presets": ["chat", "embed", "app", "full"],
  "notes": "Probes are selected by preset inside DevDiag; pass suppress codes to mute known issues."
}
```

### `POST /diag/run`
Run diagnostics on a URL.

**Request:**
```json
{
  "url": "https://example.com",
  "preset": "app",
  "suppress": ["CSP_FRAME_ANCESTORS"],
  "extra_args": ["--verbose"]
}
```

**Response:**
```json
{
  "ok": true,
  "url": "https://example.com",
  "preset": "app",
  "result": {
    "problems": [],
    "fixes": {},
    "evidence": {}
  }
}
```

**Headers (when JWT enabled):**
```
Authorization: Bearer <JWT_TOKEN>
```

## Security

### JWT Authentication
When `JWKS_URL` is set, all `/diag/run` requests require a valid JWT:

1. Server fetches JWKS from configured URL (cached 5min)
2. Validates JWT signature using JWKS public keys
3. Verifies `aud` claim matches `JWT_AUD`
4. Returns 401 for invalid/missing tokens

### SSRF Protection
By default (`ALLOW_PRIVATE_IP=0`), the server blocks requests to:
- Private IP ranges (RFC 1918)
- Loopback addresses (127.0.0.0/8, ::1)
- Link-local addresses
- Reserved ranges

Set `ALLOW_PRIVATE_IP=1` only for local development/testing.

### Rate Limiting
Simple token bucket: 2 RPS per process by default. Adjust `RATE_LIMIT_RPS` as needed.

### CORS
Restrict `ALLOWED_ORIGINS` in production to your EvalForge web origin only.

## Deployment

### Cloud Run
```bash
gcloud run deploy devdiag-http \
  --image ghcr.io/leok974/mcp-devdiag/devdiag-http:latest \
  --region us-central1 --platform managed --allow-unauthenticated \
  --cpu 1 --memory 512Mi --min-instances 0 --max-instances 3 \
  --set-env-vars JWKS_URL=https://YOUR-IDP/.well-known/jwks.json \
  --set-env-vars JWT_AUD=mcp-devdiag \
  --set-env-vars ALLOW_PRIVATE_IP=0 \
  --set-env-vars RATE_LIMIT_RPS=2 \
  --set-env-vars MAX_CONCURRENT=2 \
  --set-env-vars ALLOWED_ORIGINS=https://evalforge.app
```

### Fly.io
```toml
# fly.toml
app = "devdiag-http"

[build]
  image = "ghcr.io/leok974/mcp-devdiag/devdiag-http:latest"

[env]
  JWT_AUD = "mcp-devdiag"
  RATE_LIMIT_RPS = "2"
  ALLOW_PRIVATE_IP = "0"
  ALLOWED_ORIGINS = "https://evalforge.app"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

## EvalForge Integration

### Option 1: Direct Frontend Call
Frontend calls DevDiag HTTP server directly (requires CORS + JWT handling):

```typescript
const response = await fetch('http://127.0.0.1:8080/diag/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${jwt}`, // omit in local dev if JWKS_URL unset
  },
  body: JSON.stringify({
    url: 'https://example.com',
    preset: 'app',
    suppress: ['CSP_FRAME_ANCESTORS'],
  }),
});

const data = await response.json();
console.log(data.result);
```

### Option 2: Backend Proxy (Recommended)
Backend hides JWT tokens from frontend. Use the provided proxy:

**Backend** (`apps/api/routes/devdiag_proxy.py`):
```python
# See examples/evalforge-backend-proxy.py
from .routes import devdiag_proxy
app.include_router(devdiag_proxy.router, prefix="/api")

# Set environment variables:
# DEVDIAG_BASE=http://devdiag-http:8080
# DEVDIAG_JWT=<your-jwt>
```

**Frontend**:
```typescript
// No JWT needed - backend handles it
const response = await fetch('/api/ops/diag', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({url: 'https://example.com', preset: 'app'}),
});
const data = await response.json();
console.log(data.problems, data.fixes);
```

## CI Integration

### GitHub Actions
```yaml
- name: Run DevDiag
  run: |
    curl -sf -X POST "${{ secrets.DEVDIAG_BASE }}/diag/run" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${{ secrets.DEVDIAG_JWT }}" \
      -d '{"url":"https://staging.example.com","preset":"full"}' | jq .
```

## Performance

- Cold start: ~2-5s (includes Playwright browser launch)
- Warm request: ~1-3s per URL
- Timeout: 180s (configurable in `run_devdiag_cli`)

## Observability

Current endpoints:
- `/healthz` - Health check

Future:
- `/metrics` - Prometheus metrics
- Structured logging (JSON)
- OpenTelemetry tracing

## Testing

### Local Smoke Tests

**PowerShell:**
```powershell
.\test_local.ps1
# Or with custom URL:
.\test_local.ps1 http://127.0.0.1:8080
```

**Bash:**
```bash
./test_smoke.sh
# Or with custom URL:
./test_smoke.sh http://127.0.0.1:8080
```

### Docker Smoke Test
```bash
# Start container
docker compose -f docker-compose.devdiag.yml up -d --build

# Run tests
curl -s http://127.0.0.1:8080/healthz | jq .
curl -s http://127.0.0.1:8080/metrics
curl -s -X POST http://127.0.0.1:8080/diag/run \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com","preset":"app"}' | jq .

# Cleanup
docker compose -f docker-compose.devdiag.yml down
```

## Development

### Build Docker Image
```bash
docker build -t devdiag-http:dev apps/devdiag-http/
docker run -p 8080:8080 -e ALLOW_PRIVATE_IP=1 devdiag-http:dev
```

### Optimize Image Size
If you don't need Playwright, remove browser dependencies from Dockerfile and change requirements.txt:
```txt
mcp-devdiag[export]==0.2.1  # no [playwright]
```

Image size: ~800MB with Playwright, ~200MB without.
