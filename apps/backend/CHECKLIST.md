# DevDiag Backend Proxy - Integration Checklist

## ✅ Pre-Integration

- [ ] DevDiag HTTP server is deployed and accessible
  - URL: `https://devdiag-http.YOUR-DOMAIN.run.app`
  - Test: `curl https://devdiag-http.YOUR-DOMAIN.run.app/healthz`
- [ ] JWT token configured (if using auth)
- [ ] Host allowlist defined (e.g., `.ledger-mind.org`)

## ✅ Backend Setup

### 1. Copy Files
- [ ] Copy `apps/backend/app/routes/devdiag_proxy.py` to your backend
- [ ] Copy `apps/backend/app/routes/README.md` (optional - documentation)

### 2. Install Dependencies
```bash
cd YOUR_BACKEND
pip install fastapi httpx pydantic uvicorn
```

- [ ] Dependencies installed
- [ ] Requirements added to `requirements.txt` or `pyproject.toml`

### 3. Register Router
```python
# app/main.py
from app.routes import devdiag_proxy

app.include_router(devdiag_proxy.router, tags=["ops"])
```

- [ ] Router imported
- [ ] Router registered with FastAPI app

### 4. Configure Environment

**Development (`.env.dev`)**
```bash
DEVDIAG_ENABLED=1
DEVDIAG_BASE=http://localhost:8080
DEVDIAG_JWT=
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,localhost,127.0.0.1
```

**Production (`.env.prod`)**
```bash
DEVDIAG_ENABLED=1
DEVDIAG_BASE=https://devdiag-http.YOUR-DOMAIN.run.app
DEVDIAG_JWT=your-jwt-token
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org
```

- [ ] `DEVDIAG_BASE` configured
- [ ] `DEVDIAG_JWT` configured (if needed)
- [ ] `DEVDIAG_ALLOW_HOSTS` configured
- [ ] Environment variables loaded in backend

### 5. (Optional) Add Admin Gate
```python
# app/routes/devdiag_proxy.py
from app.routes.auth import admin_required

@router.post("/ops/diag", response_model=DiagResponse)
async def run_diag(
    ...
    ___: Any = Depends(admin_required),  # ← Uncomment
):
```

- [ ] Admin dependency imported (if needed)
- [ ] Admin gate uncommented (if needed)

## ✅ Testing

### Local Testing

**1. Start DevDiag HTTP server (Docker)**
```bash
docker compose -f docker-compose.devdiag.yml up -d
```
- [ ] DevDiag HTTP server running on localhost:8080

**2. Start backend**
```bash
uvicorn app.main:app --reload --port 8000
```
- [ ] Backend running on localhost:8000

**3. Test health endpoint**
```bash
curl http://localhost:8000/ops/diag/health
```
Expected: `{"status": "ok", "timestamp": "..."}`
- [ ] Health check returns 200

**4. Test diagnostics endpoint**
```bash
curl -X POST http://localhost:8000/ops/diag \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","preset":"app","tenant":"ledgermind"}'
```
Expected: `{"ok": true, "url": "...", "preset": "app", "result": {...}}`
- [ ] Diagnostics return 200
- [ ] Response contains problems/fixes/score

**5. Test host allowlist**
```bash
# Should fail (not in allowlist)
curl -X POST http://localhost:8000/ops/diag \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://evil.com","preset":"app","tenant":"ledgermind"}'
```
Expected: `422` with "not in allowlist"
- [ ] Allowlist validation works

### Unit Tests

```bash
cd YOUR_BACKEND
pytest apps/backend/tests/test_devdiag_proxy.py -v
```

- [ ] All tests pass
- [ ] Coverage > 90%

## ✅ Frontend Integration

### 1. Create Service Module

**TypeScript (`src/services/devdiag.ts`)**
```typescript
export interface DiagRequest {
  url: string;
  preset: 'chat' | 'embed' | 'app' | 'full';
  suppress?: string[];
  tenant: string;
}

export async function runDiagnostics(req: DiagRequest) {
  const res = await fetch('/ops/diag', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Diagnostics failed: ${res.statusText}`);
  return res.json();
}
```

- [ ] Service module created
- [ ] TypeScript types defined

### 2. Test Frontend Call

```typescript
const result = await runDiagnostics({
  url: 'https://app.ledger-mind.org',
  preset: 'app',
  tenant: 'ledgermind',
});
console.log('Score:', result.result.score);
console.log('Problems:', result.result.problems.length);
```

- [ ] Frontend can call backend proxy
- [ ] Response is correctly typed
- [ ] No CORS errors

## ✅ CI/CD Integration

### 1. Copy Workflow
```bash
cp .github/workflows/devdiag-ci-example.yml YOUR_REPO/.github/workflows/devdiag.yml
```

- [ ] Workflow copied
- [ ] Workflow customized (URLs, thresholds)

### 2. Configure Secrets
```bash
gh secret set DEVDIAG_JWT --body "your-jwt-token"
```

- [ ] `DEVDIAG_JWT` secret set (if using auth)

### 3. Test Workflow

**Manual trigger:**
```bash
gh workflow run devdiag.yml \
  -f target_url=https://app.ledger-mind.org \
  -f preset=app
```

- [ ] Workflow runs successfully
- [ ] Summary shows top problem codes
- [ ] Policy gate works (fails if >25 problems)
- [ ] Artifact uploaded

### 4. Add to Deployment Pipeline

```yaml
jobs:
  deploy:
    steps:
      - name: Deploy
        run: # your deploy command

      - name: Smoke test with DevDiag
        run: |
          curl -fsS "$BACKEND_URL/ops/diag/health"
          # ... diagnostics call
```

- [ ] Smoke test added to deployment workflow
- [ ] Runs after deployment
- [ ] Fails deployment if too many problems

## ✅ Production Deployment

### 1. Environment Configuration
- [ ] `DEVDIAG_BASE` points to production DevDiag HTTP server
- [ ] `DEVDIAG_JWT` configured (if using auth)
- [ ] `DEVDIAG_ALLOW_HOSTS` includes all production domains
- [ ] `DEVDIAG_TIMEOUT_S` appropriate (120s default)
- [ ] `DEVDIAG_ENABLED=1` in production

### 2. Security Checks
- [ ] JWT token is secret (not in code)
- [ ] Host allowlist is restrictive (not `*`)
- [ ] Feature can be disabled (`DEVDIAG_ENABLED=0`)
- [ ] Admin gate enabled (if required)
- [ ] CORS configured correctly

### 3. Monitoring
- [ ] Health endpoint monitored (`/ops/diag/health`)
- [ ] Errors tracked (502/503/504)
- [ ] Latency tracked (p50, p95, p99)
- [ ] Rate limiting working (DevDiag side)

### 4. Deployment Smoke Test
```bash
# After deployment
curl -fsS https://api.ledger-mind.org/ops/diag/health

curl -fsS -X POST https://api.ledger-mind.org/ops/diag \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://app.ledger-mind.org","preset":"app","tenant":"ledgermind"}'
```

- [ ] Health check returns 200
- [ ] Diagnostics return 200
- [ ] Response time < 30s
- [ ] No 429 errors (rate limiting OK)

## ✅ Documentation

- [ ] Internal docs updated (how to use diagnostics)
- [ ] Frontend team informed (new endpoint available)
- [ ] DevOps team informed (new dependency: DevDiag HTTP)
- [ ] Runbook created (troubleshooting 502/503/504)

## ✅ Post-Integration

### 1. Monitor for 24h
- [ ] No 5xx errors
- [ ] No 429 errors (rate limiting OK)
- [ ] Response times acceptable
- [ ] CPU/memory usage normal

### 2. Gradual Rollout (if applicable)
- [ ] Enable for 10% of users
- [ ] Enable for 50% of users
- [ ] Enable for 100% of users

### 3. Feedback Loop
- [ ] Collect user feedback on diagnostics quality
- [ ] Tune `DEVDIAG_TIMEOUT_S` if needed
- [ ] Tune rate limits if needed
- [ ] Add new hosts to allowlist as needed

## 🎉 Success Criteria

✅ Backend proxy returns 200 for health check  
✅ Backend proxy returns 200 for diagnostics  
✅ Host allowlist blocks unauthorized URLs  
✅ Frontend can call backend proxy without JWT  
✅ CI workflow runs and uploads results  
✅ Production deployment stable for 24h  
✅ No 5xx errors in production  
✅ Response times < 30s  

## 🐛 Troubleshooting Reference

| Error | Cause | Fix |
|-------|-------|-----|
| 502 "DevDiag health check failed" | DevDiag unreachable | Check `DEVDIAG_BASE`, verify server running |
| 400 "not in allowlist" | URL not allowed | Add to `DEVDIAG_ALLOW_HOSTS` |
| 503 "base URL not configured" | `DEVDIAG_BASE` empty | Set environment variable |
| 504 "timed out" | DevDiag slow | Increase `DEVDIAG_TIMEOUT_S` |
| 404 "Not found" | `DEVDIAG_ENABLED=0` | Set to 1 or remove endpoint |
| 429 after retries | Rate limit exceeded | Increase `RATE_LIMIT_RPS` on DevDiag |

## 📚 Documentation Links

- **Setup Guide**: `apps/backend/SETUP.md`
- **API Reference**: `apps/backend/app/routes/README.md`
- **Implementation Details**: `apps/backend/IMPLEMENTATION.md`
- **DevDiag HTTP Server**: `apps/devdiag-http/README.md`
