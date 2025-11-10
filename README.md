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

## Configuration

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

### VS Code Integration

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

### Available Tools

#### Reader Role

- `get_status()` - Comprehensive diagnostics snapshot
- `get_network_summary()` - Aggregated network metrics
- `get_metrics(window)` - Prometheus-backed rates and latencies
- `get_request_diagnostics(url, method)` - Live probe (allowlist-only)

#### Operator Role

- `set_mode(mode, ttl_seconds)` - Change operating mode
- `export_snapshot()` - Bundle logs for incident analysis
- `compare_envs(a, b)` - Diff environment configurations

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
