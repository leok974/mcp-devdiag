# DevDiag Backend Proxy - Quick Setup

Drop-in FastAPI router for proxying DevDiag HTTP calls from your LedgerMind backend.

## 🚀 Quick Setup (5 minutes)

### 1. Copy the proxy file

```bash
# Already done! File location:
# apps/backend/app/routes/devdiag_proxy.py
```

### 2. Install dependencies

```bash
cd apps/backend
pip install -r requirements.txt
```

### 3. Register router

```python
# app/main.py
from app.routes import devdiag_proxy

app = FastAPI()
app.include_router(devdiag_proxy.router, tags=["ops"])
```

### 4. Configure environment

```bash
# .env or deployment config
DEVDIAG_ENABLED=1
DEVDIAG_BASE=https://devdiag-http.example.run.app
DEVDIAG_JWT=                                    # Optional: JWT token for DevDiag
DEVDIAG_TIMEOUT_S=120
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,app.ledger-mind.org
```

### 5. Test locally

```bash
# Start backend
uvicorn app.main:app --reload --port 8000

# Test health
curl http://localhost:8000/ops/diag/health

# Test diagnostics
curl -X POST http://localhost:8000/ops/diag \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://app.ledger-mind.org","preset":"app","tenant":"ledgermind"}'
```

## 🎯 Frontend Integration

### React/TypeScript Example

```typescript
// src/services/devdiag.ts
export interface DiagRequest {
  url: string;
  preset: 'chat' | 'embed' | 'app' | 'full';
  suppress?: string[];
  tenant: string;
}

export interface DiagResponse {
  ok: boolean;
  url: string;
  preset: string;
  result: {
    problems: Array<{code: string; severity: string; message: string}>;
    fixes: Record<string, any>;
    score: number;
  };
}

export async function runDiagnostics(req: DiagRequest): Promise<DiagResponse> {
  const res = await fetch('/ops/diag', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(req),
  });
  
  if (!res.ok) {
    throw new Error(`Diagnostics failed: ${res.statusText}`);
  }
  
  return res.json();
}

export async function checkDevDiagHealth(): Promise<{status: string}> {
  const res = await fetch('/ops/diag/health');
  if (!res.ok) throw new Error('DevDiag health check failed');
  return res.json();
}
```

### Usage in Component

```tsx
// src/components/DiagnosticsPanel.tsx
import {runDiagnostics} from '@/services/devdiag';

function DiagnosticsPanel() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DiagResponse | null>(null);

  const handleRunDiag = async () => {
    setLoading(true);
    try {
      const res = await runDiagnostics({
        url: 'https://app.ledger-mind.org',
        preset: 'app',
        tenant: 'ledgermind',
      });
      setResults(res);
    } catch (err) {
      console.error('Diagnostics failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={handleRunDiag} disabled={loading}>
        {loading ? 'Running...' : 'Run Diagnostics'}
      </button>
      
      {results && (
        <div>
          <h3>Score: {results.result.score}</h3>
          <h4>Problems: {results.result.problems.length}</h4>
          <ul>
            {results.result.problems.map((p, i) => (
              <li key={i}>[{p.severity}] {p.code}: {p.message}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

## 🔒 Security

### Host Allowlist Patterns

```bash
# Root domain (wildcard subdomains)
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org
# ✅ app.ledger-mind.org
# ✅ ledger-mind.org
# ✅ pr-123.ledger-mind.org
# ✅ staging.ledger-mind.org

# Exact hosts
DEVDIAG_ALLOW_HOSTS=app.ledger-mind.org,staging.ledger-mind.org
# ✅ app.ledger-mind.org
# ❌ pr-123.ledger-mind.org

# Mixed (recommended for preview environments)
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,app.ledger-mind.org
```

### Optional: Admin-Only Access

```python
# app/routes/devdiag_proxy.py
from app.routes.auth import admin_required

@router.post("/ops/diag", response_model=DiagResponse)
async def run_diag(
    payload: RunPayload,
    request: Request,
    _: bool = Depends(require_base),
    __: bool = Depends(require_enabled),
    ___: Any = Depends(admin_required),  # ← Uncomment this line
):
    ...
```

## 🧪 Testing

### Unit Tests

```bash
# Run tests
pytest apps/backend/tests/test_devdiag_proxy.py -v

# With coverage
pytest apps/backend/tests/test_devdiag_proxy.py --cov=app.routes.devdiag_proxy
```

### Integration Test

```bash
# 1. Start DevDiag HTTP server (Docker)
docker compose -f docker-compose.devdiag.yml up -d

# 2. Start backend
DEVDIAG_BASE=http://localhost:8080 \
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,example.com \
  uvicorn app.main:app --reload --port 8000

# 3. Test health
curl http://localhost:8000/ops/diag/health

# 4. Test diagnostics
curl -X POST http://localhost:8000/ops/diag \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","preset":"app","tenant":"ledgermind"}' | jq .
```

## 📊 CI Integration

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      - name: Deploy backend
        run: |
          # Your deployment logic...

      - name: Smoke test DevDiag proxy
        env:
          BACKEND_URL: https://api.ledger-mind.org
        run: |
          # Health check
          curl -fsS "$BACKEND_URL/ops/diag/health"
          
          # Run diagnostics
          curl -fsS -X POST "$BACKEND_URL/ops/diag" \
            -H 'Content-Type: application/json' \
            -d '{"url":"https://app.ledger-mind.org","preset":"app","tenant":"ledgermind"}' \
            > diag.json
          
          # Check results
          jq -e '.ok == true' diag.json
          jq -e '(.result.problems | length) < 25' diag.json
```

## 🔧 Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEVDIAG_BASE` | ✅ | - | DevDiag HTTP server URL |
| `DEVDIAG_JWT` | ❌ | empty | JWT token for DevDiag auth |
| `DEVDIAG_TIMEOUT_S` | ❌ | 120 | Request timeout (seconds) |
| `DEVDIAG_ENABLED` | ❌ | 1 | Enable/disable feature (0=404) |
| `DEVDIAG_ALLOW_HOSTS` | ❌ | app.ledger-mind.org | Comma-separated allowlist |

### API Endpoints

#### `GET /ops/diag/health`
Health check (proxies to DevDiag `/healthz`)

**Response**: `{"status": "ok", "timestamp": "..."}`

#### `POST /ops/diag`
Run diagnostics

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
    "fixes": {...},
    "score": 85
  }
}
```

## 📚 Additional Documentation

- **Comprehensive Guide**: [apps/backend/app/routes/README.md](app/routes/README.md)
- **DevDiag HTTP Server**: [apps/devdiag-http/README.md](../../devdiag-http/README.md)
- **Main README**: [README.md](../../../README.md)

## 🐛 Troubleshooting

**502 "DevDiag health check failed"**
- Check `DEVDIAG_BASE` is correct
- Verify DevDiag HTTP server is running
- Test manually: `curl https://devdiag-http.example.run.app/healthz`

**400 "target host not in allowlist"**
- Add host to `DEVDIAG_ALLOW_HOSTS`
- Use root domain pattern (`.ledger-mind.org`) for preview environments

**504 "DevDiag timed out"**
- Increase `DEVDIAG_TIMEOUT_S` (default 120s)
- Check DevDiag server timeout is >= backend timeout

**429 after retries**
- DevDiag rate limit exceeded (default 2 RPS)
- Increase `RATE_LIMIT_RPS` on DevDiag HTTP server
