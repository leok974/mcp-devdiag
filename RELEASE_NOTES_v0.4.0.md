# v0.4.0 — Server-Side Allowlist, MCP Stdio Wrapper, Pro Tooling

**Release Date:** January 12, 2025  
**Full Changelog:** https://github.com/leok974/mcp-devdiag/compare/v0.3.1...v0.4.0

---

## 🎯 Highlights

This release brings **production-grade security**, **pure-CLI diagnostics**, and **comprehensive deployment tooling** for teams running DevDiag in production environments.

### ✨ New: MCP Stdio Wrapper

Pure-CLI diagnostics without the HTTP server. Perfect for local dev, IDE integration, and CI pipelines:

```bash
python scripts/mcp_probe.py --url https://example.com --preset app --pretty
```

**Features:**
- 🚀 No HTTP server needed
- ✅ Exit codes for CI policy gates (0/1/2)
- 🎯 VS Code task integration
- ⚙️ Environment variables: `MCP_DEV_DIAG_BIN`, `MCP_PROBE_TIMEOUT_S`

**Use Cases:**
- Local development
- IDE/Editor integration
- Pure-CLI CI pipelines
- No need for JWT auth or rate limiting

### 🔒 Enhanced: Server-Side Security

Defense-in-depth security for the HTTP server:

**ALLOW_TARGET_HOSTS** - Server-side URL allowlist:
```bash
ALLOW_TARGET_HOSTS=.ledger-mind.org,app.ledger-mind.org,pr-*.example.com
```

Supports:
- Exact hosts: `app.example.com`
- Subdomain wildcards: `.example.com`
- Glob patterns: `pr-*.example.com`

**New Endpoints:**
- `GET /selfcheck` - CLI availability + version (debug 502 errors)
- `GET /ready` - Readiness probe for K8s (CLI + allowlist + JWKS checks)

### 🔄 New: Backend Proxy

Drop-in FastAPI router for web apps (EvalForge, LedgerMind, ApplyLens):

```python
from app.routes import devdiag_proxy
app.include_router(devdiag_proxy.router, tags=["ops"])
```

**Features:**
- Host allowlist validation (defense-in-depth)
- Retry logic with jitter backoff (3 attempts)
- Trace header propagation (`x-request-id`, `x-b3-*`, `traceparent`)
- Response size limits (2MB cap)
- Connection pooling
- Hides JWT from frontend

### 🚀 Production Tooling

**CI/CD:**
- GitHub Actions smoke tests (`devdiag-http-smoke.yml`)
- GitHub Actions MCP quickcheck (`devdiag-mcp-quickcheck.yml`)
- Makefile helpers (8 new targets)

**Deployment:**
- K8s manifests (Deployment, Service, Ingress, HPA)
- Prometheus integration (ServiceMonitor, PrometheusRule)
- Alert rules (DevDiagDown, HighErrorRate, ConcurrencyLimit)

**Documentation:**
- MCP stdio guide (`docs/MCP_STDIO.md`)
- K8s deployment guide (`apps/devdiag-http/K8S.md`)
- Prometheus setup (`apps/devdiag-http/PROMETHEUS.md`)
- Troubleshooting guide (`apps/devdiag-http/TROUBLESHOOTING.md`)
- Backend proxy guides (`apps/backend/SETUP.md`, `IMPLEMENTATION.md`)

---

## 📦 What's Changed

### New Features

#### MCP Stdio Wrapper (`scripts/mcp_probe.py`)
- JSON-RPC client for `mcp-devdiag --stdio`
- Exit codes: 0 (success), 1 (error), 2 (policy violation)
- Policy gate support: `--max-problems` threshold
- VS Code task integration (`.vscode/tasks.json`)
- Comprehensive documentation (`docs/MCP_STDIO.md`)
- Quick reference card (`scripts/MCP_PROBE_QUICKREF.md`)
- Comparison scripts (Bash + PowerShell)

#### HTTP Server Security (`apps/devdiag-http`)
- `ALLOW_TARGET_HOSTS`: Server-side URL allowlist with pattern matching
- `GET /selfcheck`: Returns CLI availability and version
- `GET /ready`: Comprehensive readiness probe (CLI + allowlist + JWKS)
- python-dotenv integration for reliable env loading
- Docker Compose `env_file` support

#### Backend Proxy (`apps/backend/`)
- Full FastAPI router implementation
- Host allowlist validation (`DEVDIAG_ALLOW_HOSTS`)
- Retry logic with exponential backoff + jitter
- Trace header propagation for distributed tracing
- Response size limits (2MB cap)
- Connection pooling (10 max connections, 5 keepalive)
- Comprehensive test suite (15+ tests)

#### CI/CD & Deployment
- GitHub Actions workflow: `devdiag-http-smoke.yml`
- GitHub Actions workflow: `devdiag-mcp-quickcheck.yml`
- Makefile targets: `devdiag-up`, `devdiag-down`, `devdiag-selfcheck`, `devdiag-ready`, `devdiag-probe`, `devdiag-logs`, `devdiag-test`, `devdiag-clean`
- K8s deployment manifests (HPA, probes, resource limits)
- Prometheus ServiceMonitor + PrometheusRule
- Alert rules with thresholds

#### Documentation
- `docs/MCP_STDIO.md` - Comprehensive MCP stdio guide
- `apps/devdiag-http/K8S.md` - Kubernetes deployment guide
- `apps/devdiag-http/PROMETHEUS.md` - Monitoring setup
- `apps/devdiag-http/TROUBLESHOOTING.md` - Diagnostic guide
- `apps/backend/SETUP.md` - Backend proxy setup
- `apps/backend/IMPLEMENTATION.md` - Implementation details
- `apps/backend/CHECKLIST.md` - Deployment checklist
- `scripts/MCP_PROBE_QUICKREF.md` - Quick reference
- Updated README with usage patterns

### Files Added (27)
- `scripts/mcp_probe.py`
- `.github/workflows/devdiag-mcp-quickcheck.yml`
- `.github/workflows/devdiag-http-smoke.yml`
- `.github/workflows/devdiag-ci-example.yml`
- `.vscode/tasks.json`
- `docs/MCP_STDIO.md`
- `scripts/MCP_PROBE_QUICKREF.md`
- `scripts/compare_patterns.sh`
- `scripts/compare_patterns.ps1`
- `apps/backend/` (full directory structure - 9 files)
- `apps/devdiag-http/K8S.md`
- `apps/devdiag-http/PROMETHEUS.md`
- `apps/devdiag-http/TROUBLESHOOTING.md`
- `apps/devdiag-http/.env.example`
- `.env.devdiag`
- `READY-TO-MERGE.md`
- `MCP_STDIO_SHIPPED.md`

### Files Modified (8)
- `README.md` - Added usage patterns, MCP stdio examples
- `Makefile` - Added 8 devdiag-* targets
- `apps/devdiag-http/main.py` - Added allowlist, /selfcheck, /ready
- `apps/devdiag-http/README.md` - Updated with new features
- `apps/devdiag-http/requirements.txt` - Added python-dotenv
- `apps/devdiag-http/test_smoke.sh` - Added /selfcheck test
- `apps/devdiag-http/examples/evalforge-backend-proxy.py` - Updated
- `docker-compose.devdiag.yml` - Added env_file support

---

## 🔧 Breaking Changes

**None** - All changes are backward compatible.

---

## 📋 Migration Notes

### Recommended: Add Server-Side Allowlist

For production deployments, add `ALLOW_TARGET_HOSTS` to your environment:

```bash
# Cloud Run / Kubernetes / Docker
ALLOW_TARGET_HOSTS=.ledger-mind.org,app.ledger-mind.org,applylens.app,.applylens.app
```

**Supported patterns:**
- Exact: `app.example.com`
- Subdomain: `.example.com` (matches `*.example.com`)
- Glob: `pr-*.example.com` (matches `pr-123.example.com`)

### Optional: Update Kubernetes Probes

Use `/ready` for readinessProbe (more comprehensive than `/healthz`):

```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Optional: Migrate CI to MCP Stdio

For faster CI builds, use `scripts/mcp_probe.py` instead of Docker:

**Before (HTTP):**
```yaml
- run: docker compose up -d
- run: curl $DEVDIAG_URL/diag/run ...
```

**After (MCP stdio):**
```yaml
- run: pip install "mcp-devdiag[playwright,export]==0.2.1"
- run: python scripts/mcp_probe.py --url $URL --preset app
```

Benefits:
- ⚡ Faster (no Docker build)
- 🎯 Simpler (pure Python)
- 📦 Fewer dependencies

---

## 🚀 Quick Start

### MCP Stdio (Local/CI)

```bash
# Install
pip install "mcp-devdiag[playwright,export]==0.2.1"

# Run probe
python scripts/mcp_probe.py --url https://example.com --preset app --pretty

# CI policy gate
python scripts/mcp_probe.py --url https://example.com --preset app --max-problems 25
```

### HTTP Server (Production)

```bash
# Local
docker compose -f docker-compose.devdiag.yml up -d --build
curl http://127.0.0.1:8080/ready | jq .

# Production
export ALLOW_TARGET_HOSTS=.example.com
export JWKS_URL=https://auth.example.com/.well-known/jwks.json
uvicorn main:app --host 0.0.0.0 --port 8080
```

### Backend Proxy (EvalForge/LedgerMind)

```python
# apps/backend/app/routes/__init__.py
from . import devdiag_proxy

# apps/backend/app/main.py
app.include_router(devdiag_proxy.router, tags=["ops"])
```

```bash
# Environment
DEVDIAG_BASE=https://devdiag-http.example.run.app
DEVDIAG_JWT=your-jwt-token
DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,applylens.app
```

---

## 📊 Stats

- **Files Changed:** 35 (27 new, 8 modified)
- **Lines Added:** 4,215
- **Documentation Pages:** 10+
- **Test Coverage:** Backend proxy (15+ tests), HTTP smoke tests (7 checks)
- **Deployment Guides:** K8s, Docker, Cloud Run, Fly.io, Render

---

## 🙏 Contributors

- **Leo Klemet** (@leok974)

---

## 📚 Documentation

- **MCP Stdio Guide:** [docs/MCP_STDIO.md](https://github.com/leok974/mcp-devdiag/blob/main/docs/MCP_STDIO.md)
- **HTTP Server:** [apps/devdiag-http/README.md](https://github.com/leok974/mcp-devdiag/blob/main/apps/devdiag-http/README.md)
- **Backend Proxy:** [apps/backend/SETUP.md](https://github.com/leok974/mcp-devdiag/blob/main/apps/backend/SETUP.md)
- **K8s Deployment:** [apps/devdiag-http/K8S.md](https://github.com/leok974/mcp-devdiag/blob/main/apps/devdiag-http/K8S.md)
- **Prometheus:** [apps/devdiag-http/PROMETHEUS.md](https://github.com/leok974/mcp-devdiag/blob/main/apps/devdiag-http/PROMETHEUS.md)
- **Troubleshooting:** [apps/devdiag-http/TROUBLESHOOTING.md](https://github.com/leok974/mcp-devdiag/blob/main/apps/devdiag-http/TROUBLESHOOTING.md)

---

## 🔗 Links

- **PyPI:** https://pypi.org/project/mcp-devdiag/
- **GitHub:** https://github.com/leok974/mcp-devdiag
- **Issues:** https://github.com/leok974/mcp-devdiag/issues
- **Changelog:** https://github.com/leok974/mcp-devdiag/compare/v0.3.1...v0.4.0

---

**Install:** `pip install "mcp-devdiag[playwright,export]==0.2.1"`  
**Next Release:** v0.5.0 (planned: OpenAPI summaries, additional proxy examples)
