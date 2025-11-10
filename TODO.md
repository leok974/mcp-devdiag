# Future Enhancements

## Nice-to-Have Features

These are optional enhancements that can be added incrementally as needed.

### 1. OpenAPI Documentation

**Status**: Not implemented  
**Effort**: Small (1-2 hours)

Add OpenAPI/Swagger doclets for MCP routes to enable client reflection:

```python
# mcp_devdiag/server.py
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(
    title="DevDiag MCP Server",
    description="Production-safe autonomous diagnostics",
    version="0.2.0",
)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="DevDiag API Docs"
    )
```

**Benefits**: Auto-generated client SDKs, interactive API explorer

---

### 2. Optional Playwright Driver

**Status**: Partially implemented (runtime checks only)  
**Effort**: Medium (4-6 hours)

Add feature flag to explicitly enable browser drivers:

```yaml
# devdiag.yaml
diag:
  browser_enabled: false  # Default: false for prod safety
```

```python
# mcp_devdiag/probes/adapters.py
def get_driver(driver: str | None, config: dict):
    if driver == "playwright":
        if not config.get("diag", {}).get("browser_enabled"):
            raise ValueError("Browser driver disabled (set diag.browser_enabled=true)")
    # ... existing logic
```

**Benefits**: Explicit opt-in for DOM/JS-heavy probes

---

### 3. Problem Suppression Map

**Status**: Not implemented  
**Effort**: Small (2-3 hours)

Allow suppressing known/accepted issues:

```yaml
# devdiag.yaml
diag:
  suppress:
    - code: "PORTAL_ROOT_MISSING"
      reason: "This app uses native toasts (not React portals)"
      expires: "2025-12-31"  # Optional expiry date
    - code: "OVERLAY_VIEWPORT_COVER"
      reason: "Modal overlays are intentional"
```

```python
# mcp_devdiag/probes/bundle.py
def filter_suppressed(problems: list[str], config: dict) -> list[str]:
    suppress = config.get("diag", {}).get("suppress", [])
    suppressed_codes = {s["code"] for s in suppress}
    return [p for p in problems if p not in suppressed_codes]
```

**Benefits**: Reduce noise from known issues, track technical debt

---

### 4. Snapshot Export to S3

**Status**: Stub only in `export_snapshot()`  
**Effort**: Medium (4-6 hours)

Upload redacted diagnostic bundles to S3 for incident analysis:

```python
# mcp_devdiag/tools_devdiag.py
import boto3
from datetime import datetime

@app.tool()
async def export_snapshot(base_url: str, auth_header: str | None = None):
    authorize("export_snapshot", auth_header)
    
    # Collect full bundle
    bundle = await diag_status_plus(base_url, preset="full")
    
    # Upload to S3
    s3 = boto3.client("s3")
    bucket = CONFIG.shipping.get("s3_bucket")
    key = f"{CONFIG.tenant}/{datetime.utcnow().isoformat()}/snapshot.json"
    
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(bundle),
        ContentType="application/json"
    )
    
    return {"ok": True, "s3_uri": f"s3://{bucket}/{key}"}
```

**Benefits**: Durable incident artifacts, compliance audit trail

---

### 5. Webhook Notifications

**Status**: Not implemented  
**Effort**: Small (2-3 hours)

Send alerts when critical problems detected:

```yaml
# devdiag.yaml
notifications:
  webhooks:
    - url: "https://slack.example.com/webhook"
      on_severity: ["critical", "error"]
      on_codes: ["IFRAME_FRAME_ANCESTORS_BLOCKED"]
```

```python
# mcp_devdiag/probes/bundle.py
async def notify_webhooks(result: dict, config: dict):
    webhooks = config.get("notifications", {}).get("webhooks", [])
    for hook in webhooks:
        if result["severity"] in hook.get("on_severity", []):
            await httpx.AsyncClient().post(hook["url"], json=result)
```

**Benefits**: Real-time incident awareness, automated alerting

---

### 6. Multi-Tenant Rate Limits (Customizable)

**Status**: Fixed limits only (30/min, burst 5)  
**Effort**: Small (1-2 hours)

Allow per-tenant rate limit configuration:

```yaml
# devdiag.yaml
rate_limits:
  default:
    rate: 0.5  # 30/min
    burst: 5
  tenants:
    premium-tenant:
      rate: 2.0  # 120/min
      burst: 20
```

```python
# mcp_devdiag/limits.py
def get_bucket_for_tenant(tenant: str) -> TokenBucket:
    limits = CONFIG.rate_limits.get("tenants", {}).get(tenant)
    if not limits:
        limits = CONFIG.rate_limits.get("default", {"rate": 0.5, "burst": 5})
    return TokenBucket(rate=limits["rate"], burst=limits["burst"])
```

**Benefits**: Tiered service levels, prevent overload

---

### 7. Probe Result Caching

**Status**: Not implemented  
**Effort**: Small (2-3 hours)

Cache probe results to reduce duplicate work:

```python
# mcp_devdiag/cache.py
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cache_key(url: str, probe: str) -> str:
    return hashlib.sha256(f"{url}:{probe}".encode()).hexdigest()

# In probe modules:
cache_ttl = 300  # 5 minutes
cached = get_from_cache(cache_key(url, "csp_headers"))
if cached and not_expired(cached, cache_ttl):
    return cached
```

**Benefits**: Faster responses, reduced load on target apps

---

### 8. Grafana JSON API Data Source

**Status**: Not implemented  
**Effort**: Medium (4-6 hours)

Implement Grafana JSON API protocol for direct integration:

```python
# mcp_devdiag/grafana.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/search")
async def search():
    return ["status_plus", "probe_csp_headers", "metrics"]

@app.post("/query")
async def query(request: dict):
    target = request["targets"][0]["target"]
    if target == "status_plus":
        result = await diag_status_plus(request["base_url"])
        return format_for_grafana(result)
```

**Benefits**: Native Grafana dashboards, no custom data source needed

---

### 9. Historical Trend Tracking

**Status**: Not implemented  
**Effort**: Large (8-12 hours)

Store probe results over time for trending:

```python
# Store in TimescaleDB/InfluxDB
async def record_probe_result(url: str, probe: str, result: dict):
    await db.execute(
        "INSERT INTO probe_history (ts, url, probe, severity, score, problems) VALUES ($1, $2, $3, $4, $5, $6)",
        datetime.utcnow(), url, probe, result["severity"], result.get("score"), result["problems"]
    )

# Query trends
@app.tool()
async def get_probe_trends(url: str, probe: str, window: str = "7d"):
    return await db.fetch(
        "SELECT ts, severity, score FROM probe_history WHERE url=$1 AND probe=$2 AND ts > NOW() - $3",
        url, probe, window
    )
```

**Benefits**: Regression detection, historical analysis

---

### 10. CLI Tool (mcp-devdiag-cli)

**Status**: Not implemented  
**Effort**: Medium (4-6 hours)

Standalone CLI for common operations:

```bash
# Install
pip install mcp-devdiag[cli]

# Usage
mcp-devdiag quickcheck https://app.example.com/chat/
mcp-devdiag status-plus https://app.example.com --preset full
mcp-devdiag remediate IFRAME_FRAME_ANCESTORS_BLOCKED CSP_INLINE_BLOCKED
```

```python
# mcp_devdiag/cli.py
import click

@click.group()
def cli():
    pass

@cli.command()
@click.argument("url")
def quickcheck(url):
    result = requests.post(f"{DEVDIAG_URL}/mcp/diag/quickcheck", json={"url": url})
    click.echo(result.json())
```

**Benefits**: Easier integration, CI/CD scripting

---

## Prioritization

**High Value, Low Effort**:
1. Problem suppression map
2. OpenAPI documentation
3. Multi-tenant rate limits

**High Value, Medium Effort**:
4. Snapshot export to S3
5. Grafana JSON API
6. Optional Playwright flag

**Future Consideration**:
7. Webhook notifications
8. Historical trend tracking
9. Probe result caching
10. CLI tool

---

## Contributing

Want to implement one of these? Open an issue on GitHub with:
- Feature name from this list
- Proposed implementation approach
- Estimated timeline

We'll review and provide guidance!
