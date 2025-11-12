# DevDiag Backend Proxy

Drop-in FastAPI router for proxying DevDiag HTTP calls from your backend, hiding JWT credentials from frontend.

## Features

- **Host allowlist validation**: Prevents arbitrary URL scanning
- **Retry logic**: 3 attempts with jitter backoff for 429/503/504
- **Trace propagation**: Forwards `x-request-id`, `x-b3-traceid`, `traceparent`
- **Size limits**: Caps responses at 2MB (defense-in-depth)
- **Feature toggle**: `DEVDIAG_ENABLED=0` returns 404
- **Connection pooling**: Reuses HTTP connections (max 10, keepalive 5)

## Environment Variables

```bash
# Required
DEVDIAG_BASE=https://devdiag-http.example.run.app
DEVDIAG_JWT=                          # Optional: JWT for DevDiag HTTP server
DEVDIAG_TIMEOUT_S=120

# Optional
DEVDIAG_ENABLED=1                     # Set to 0 to disable (returns 404)
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,app.ledger-mind.org,pr-*.ledger-mind.org
```

### Host Allowlist Patterns

```bash
# Root domain (allows all subdomains + apex)
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org
# ✅ app.ledger-mind.org
# ✅ ledger-mind.org
# ✅ pr-123.ledger-mind.org
# ❌ evil.com

# Exact hosts (comma-separated)
DEVDIAG_ALLOW_HOSTS=app.ledger-mind.org,staging.ledger-mind.org
# ✅ app.ledger-mind.org
# ❌ pr-123.ledger-mind.org

# Mixed
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,preview.example.com
```

**Best practice**: Use root domains (`.ledger-mind.org`) for dynamic preview environments.

## Integration

### 1. Register Router

```python
# app/main.py
from app.routes import devdiag_proxy

app = FastAPI()
app.include_router(devdiag_proxy.router, tags=["ops"])
```

### 2. Optional: Add Admin Gate

```python
# app/routes/devdiag_proxy.py
from app.routes.auth import admin_required

@router.post("/ops/diag", response_model=DiagResponse)
async def run_diag(
    payload: RunPayload,
    request: Request,
    _: bool = Depends(require_base),
    __: bool = Depends(require_enabled),
    ___: Any = Depends(admin_required),  # ← uncomment this line
):
    ...
```

## API Endpoints

### `GET /ops/diag/health`

Health check (proxies to DevDiag `/healthz`).

**Response**: `{"status": "ok", "timestamp": "..."}`

### `POST /ops/diag`

Run diagnostics.

**Request**:
```json
{
  "url": "https://app.ledger-mind.org",
  "preset": "app",
  "suppress": ["PERF-001"],
  "tenant": "ledgermind"
}
```

**Response**:
```json
{
  "ok": true,
  "url": "https://app.ledger-mind.org",
  "preset": "app",
  "result": {
    "problems": [...],
    "fixes": [...],
    "score": 85
  }
}
```

**Headers**:
- `x-request-id`: Request ID (propagated from DevDiag if available)

**Errors**:
- `400`: Invalid URL or not in allowlist
- `404`: `DEVDIAG_ENABLED=0`
- `502`: DevDiag unreachable or response too large
- `503`: `DEVDIAG_BASE` not configured
- `504`: DevDiag timeout

## CI Integration

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      - name: Deploy backend
        run: |
          # deploy logic...

      - name: Probe homepage (app preset)
        env:
          DEVDIAG_BASE: https://devdiag-http.example.run.app
          DEVDIAG_JWT: ${{ secrets.DEVDIAG_JWT }}
        run: |
          body='{"url":"https://app.ledger-mind.org","preset":"app","tenant":"ledgermind"}'
          hdr=(-H "content-type: application/json")
          [ -n "$DEVDIAG_JWT" ] && hdr+=(-H "authorization: Bearer $DEVDIAG_JWT")
          
          curl -fsS -X POST "$DEVDIAG_BASE/diag/run" "${hdr[@]}" -d "$body" > diag.json
          
          # Add to job summary
          echo "### DevDiag: Top Problem Codes" >> "$GITHUB_STEP_SUMMARY"
          jq -r '.result.problems[]?.code' diag.json \
            | sort | uniq -c | sort -nr | head -20 \
            | sed "s/^/* /" >> "$GITHUB_STEP_SUMMARY"
          
          # Policy gate (fail if >25 problems)
          jq -e '(.result.problems // [] | length) < 25' diag.json
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
smoke_test:
  stage: test
  script:
    - |
      body='{"url":"https://app.ledger-mind.org","preset":"app","tenant":"ledgermind"}'
      hdr="-H content-type:application/json"
      [ -n "$DEVDIAG_JWT" ] && hdr="$hdr -H authorization:Bearer $DEVDIAG_JWT"
      
      curl -fsS -X POST "$DEVDIAG_BASE/diag/run" $hdr -d "$body" > diag.json
      
      echo "## Top problem codes"
      jq -r '.result.problems[]?.code' diag.json | sort | uniq -c | sort -nr | head -20
      
      # Fail if >25 problems
      jq -e '(.result.problems // [] | length) < 25' diag.json
  variables:
    DEVDIAG_BASE: https://devdiag-http.example.run.app
```

## Testing

### Local Development

```bash
# Start backend (adjust port/command)
uvicorn app.main:app --reload --port 8000

# Test health
curl http://localhost:8000/ops/diag/health

# Test diagnostics
curl -X POST http://localhost:8000/ops/diag \
  -H 'content-type: application/json' \
  -d '{"url":"https://app.ledger-mind.org","preset":"app","tenant":"ledgermind"}'
```

### Frontend Integration

```typescript
// TypeScript example
async function runDiag(url: string): Promise<DiagResponse> {
  const res = await fetch('/ops/diag', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({url, preset: 'app', tenant: 'ledgermind'}),
  });
  if (!res.ok) throw new Error(`Diag failed: ${res.statusText}`);
  return res.json();
}
```

```python
# Python example
import httpx

async def run_diag(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://backend.example.com/ops/diag",
            json={"url": url, "preset": "app", "tenant": "ledgermind"},
        )
        r.raise_for_status()
        return r.json()
```

## Security Notes

1. **Host allowlist**: Always configure `DEVDIAG_ALLOW_HOSTS` to prevent scanning arbitrary URLs
2. **JWT hiding**: Frontend never sees `DEVDIAG_JWT` (stored in backend env only)
3. **Feature toggle**: Use `DEVDIAG_ENABLED=0` to disable without removing code
4. **Rate limiting**: DevDiag HTTP server has built-in rate limiting (2 RPS default)
5. **Admin gate**: Uncomment `admin_required` dependency if needed

## Troubleshooting

**502 "DevDiag health check failed"**
- Check `DEVDIAG_BASE` is correct and reachable
- Verify DevDiag HTTP server is running
- Check network/firewall rules

**400 "target host not in allowlist"**
- Add host to `DEVDIAG_ALLOW_HOSTS`
- Use root domain pattern (`.example.com`) for preview environments

**504 "DevDiag timed out"**
- Increase `DEVDIAG_TIMEOUT_S` (default 120s)
- Check DevDiag HTTP server `DEVDIAG_TIMEOUT_S` is >= backend timeout
- Simplify preset (use `chat` instead of `full`)

**429 after retries**
- DevDiag rate limit exceeded (default 2 RPS)
- Increase `RATE_LIMIT_RPS` on DevDiag HTTP server
- Add delay between calls

## Dependencies

```txt
# requirements.txt
fastapi>=0.100.0
httpx>=0.24.0
pydantic>=2.0.0
```
