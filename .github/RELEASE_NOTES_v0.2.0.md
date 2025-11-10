## DevDiag v0.2.0 — Production-ready diagnostics for any project

**Highlights**
- RBAC with JWKS (RS256), per-tenant rate limits, incident TTL auto-revert
- Vendor-neutral probes (CSP/iframe, inline CSP, overlays, handshake, framework mismatch)
- Standard **ProbeResult** schema + severity scoring and **fix recipes**
- Prometheus metrics adapter + **Grafana dashboard JSON**
- **SSRF guard** (private IP ranges), prod policy tests & runbooks
- TypeScript + Python SDKs; Docker Compose + Kubernetes manifests
- CI **quickcheck** workflow (HTTP-only, browser-free)

**What's new**
- Endpoints: `/mcp/diag/status_plus`, `/mcp/diag/quickcheck`, `/mcp/diag/schema/probe_result`
- Security: `rbac.jwks_url` (audience `mcp-devdiag`), allow-list, header deny-list, no bodies ever
- Ops: scoring, presets (`chat|embed|app|full`), URL allow-list, SSRF block
- Assets: `dashboards/devdiag.json`, `postman/devdiag.postman_collection.json`
- Docs: SECURITY.md, RUNBOOK.md, RELEASE.md, 60-sec smoke in README
- Add-ons: Playwright driver, suppressions, S3 export

**Install**
```bash
pip install "mcp-devdiag==0.2.0"
```

**60-sec smoke**
```bash
BASE="https://diag.example.com"
JWT="REDACTED"
APP="https://app.example.com"

curl -s -X POST "$BASE/mcp/diag/quickcheck" \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d "{\"url\":\"$APP/chat/\"}" | jq

curl -s -G "$BASE/mcp/diag/status_plus" \
  --data-urlencode "base_url=$APP" \
  -H "Authorization: Bearer $JWT" | jq
```

**Breaking changes**

None. `get_status` is backward-compatible; `status_plus` adds score+fixes.

**Upgrading from 0.1.x**

Add to `devdiag.yaml`:
- `rbac.jwks_url` and `allow_probes` (required)
- Optional: wire CI quickcheck and import Grafana dashboard JSON

**Changelog**

See [CHANGELOG.md](CHANGELOG.md) in the repo for full details.

**Test coverage:** 31 tests passing

**Documentation:**
- [README.md](README.md) - Getting started, configuration, examples
- [SECURITY.md](SECURITY.md) - Security checklist, SLOs, compliance
- [RUNBOOK.md](RUNBOOK.md) - Operations guide, incident response
- [RELEASE.md](RELEASE.md) - Release process automation

**Assets:**
- `dashboards/devdiag.json` - Grafana dashboard (4 panels)
- `postman/devdiag.postman_collection.json` - API collection
- `docs/examples/devdiag.ts` - TypeScript SDK with Zod
- `docs/examples/devdiag_client.py` - Python client
- `deployments/docker-compose.yml` - Docker deployment
- `deployments/kubernetes.yaml` - K8s manifests
