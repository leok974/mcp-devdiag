# MCP Stdio Wrapper (mcp_probe.py)

A minimal JSON-RPC client that talks directly to `mcp-devdiag --stdio` without requiring the HTTP server. Perfect for local development, IDE integration, and pure-CLI CI pipelines.

## Why Use This?

**Use `scripts/mcp_probe.py` when:**
- ✅ Running diagnostics locally (dev environment)
- ✅ IDE/Editor integration (VS Code tasks, shell scripts)
- ✅ CI pipelines where you control the environment
- ✅ No need for JWT auth, rate limiting, or multi-tenancy
- ✅ Minimal dependencies (just Python 3.11+)

**Use `apps/devdiag-http` when:**
- ✅ Web app integration (EvalForge, LedgerMind)
- ✅ Multi-tenant environments
- ✅ Need JWT authentication (JWKS)
- ✅ Rate limiting and SSRF protection required
- ✅ Backend proxy pattern (hide secrets from frontend)

## Installation

No installation needed - just ensure `mcp-devdiag` CLI is installed:

```bash
# Install mcp-devdiag
pip install "mcp-devdiag[playwright,export]==0.2.1"

# Verify CLI works
mcp-devdiag --help
```

## Usage

### Basic Probe

```bash
# Simple probe with pretty output
python scripts/mcp_probe.py \
  --url https://www.leoklemet.com \
  --preset app \
  --pretty
```

### CI Policy Gate

```bash
# Fail build if too many problems found
python scripts/mcp_probe.py \
  --url https://app.example.com \
  --preset app \
  --max-problems 25 \
  > diag.json

# Check exit code
echo $?  # 0 = success, 1 = error, 2 = too many problems
```

### Suppress Known Issues

```bash
# Ignore specific problem codes
python scripts/mcp_probe.py \
  --url https://staging.example.com \
  --preset full \
  --suppress CSP_FRAME_ANCESTORS PORTAL_ROOT_MISSING \
  --pretty
```

### Custom Timeout

```bash
# Increase timeout for slow sites
python scripts/mcp_probe.py \
  --url https://slow-site.example.com \
  --preset full \
  --timeout 300 \
  --pretty
```

## Environment Variables

Configure behavior via environment variables:

```bash
# Custom CLI binary path
export MCP_DEV_DIAG_BIN="/usr/local/bin/mcp-devdiag"

# Custom timeout (default: 180s)
export MCP_PROBE_TIMEOUT_S=240

# Run probe
python scripts/mcp_probe.py --url https://example.com --preset app
```

## Exit Codes

- **0** - Success (probe completed successfully)
- **1** - Error (CLI not found, timeout, invalid JSON-RPC response)
- **2** - Too many problems (when `--max-problems` threshold exceeded)

## GitHub Actions Example

```yaml
name: DevDiag Quickcheck (MCP over stdio)
on:
  pull_request:
    branches: [ "main" ]
jobs:
  mcp-probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      
      - name: Install mcp server deps
        run: |
          python -m pip install --upgrade pip
          pip install "mcp-devdiag[playwright,export]==0.2.1" jq
      
      - name: Run MCP probe
        run: |
          python scripts/mcp_probe.py \
            --url https://www.leoklemet.com \
            --preset app \
            --pretty > diag.json
          
          echo "### Top problem codes" >> $GITHUB_STEP_SUMMARY
          jq -r '.problems[]?.code' diag.json | sort | uniq -c | sort -nr | head -20 | sed 's/^/* /' >> $GITHUB_STEP_SUMMARY || true
      
      - name: Policy gate (adjust threshold)
        run: |
          jq -e '(.problems // [] | length) < 25' diag.json
```

## VS Code Task Integration

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "DevDiag (MCP): Probe homepage",
      "type": "shell",
      "command": "python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty",
      "problemMatcher": []
    },
    {
      "label": "DevDiag (MCP): Probe with policy",
      "type": "shell",
      "command": "python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --max-problems 10",
      "problemMatcher": []
    }
  ]
}
```

Run via: `Terminal > Run Task... > DevDiag (MCP): Probe homepage`

## Output Format

### Success Response

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"url\":\"https://example.com\",\"preset\":\"app\",\"problems\":[],\"fixes\":{},\"evidence\":{}}"
    }
  ],
  "isError": false
}
```

Extract the inner JSON:
```bash
python scripts/mcp_probe.py --url https://example.com --preset app | jq -r '.content[0].text' | jq .
```

Or use `--pretty` for direct pretty-printed output:
```bash
python scripts/mcp_probe.py --url https://example.com --preset app --pretty
```

### Error Response

```json
{
  "ok": false,
  "error": "tool 'probe' not found; available: ['probe', 'tail_logs']"
}
```

## Advanced Usage

### Call Different Tool

```bash
# Call a different MCP tool (default is "probe")
python scripts/mcp_probe.py \
  --url https://example.com \
  --preset app \
  --tool tail_logs \
  --pretty
```

### Parse Results in Shell

```bash
# Extract problem count
PROBLEM_COUNT=$(python scripts/mcp_probe.py --url https://example.com --preset app | jq -r '.content[0].text | fromjson | .problems | length')

if [ "$PROBLEM_COUNT" -gt 10 ]; then
  echo "Too many problems: $PROBLEM_COUNT"
  exit 1
fi
```

### CI Artifact Upload

```yaml
- name: Run probe
  run: |
    python scripts/mcp_probe.py \
      --url https://staging.example.com \
      --preset full \
      --pretty > diag.json

- name: Upload diagnostics
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: devdiag-results
    path: diag.json
```

## Troubleshooting

### "DevDiag CLI 'mcp-devdiag' not found"

```bash
# Ensure CLI is installed
pip install mcp-devdiag

# Or specify custom binary path
export MCP_DEV_DIAG_BIN="/path/to/mcp-devdiag"
python scripts/mcp_probe.py --url https://example.com --preset app
```

### "timeout waiting for response"

```bash
# Increase timeout
python scripts/mcp_probe.py \
  --url https://slow-site.example.com \
  --preset full \
  --timeout 300
```

### "tool 'probe' not found"

Check available tools:
```bash
# List tools via MCP
mcp-devdiag --stdio
# Send: {"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}
```

## Implementation Details

### JSON-RPC Flow

1. **Start subprocess**: `mcp-devdiag --stdio`
2. **Initialize handshake**:
   ```json
   {"jsonrpc":"2.0","id":"<uuid>","method":"initialize","params":{
     "protocolVersion":"2024-11-01",
     "clientInfo":{"name":"mcp-probe","version":"0.1.0"},
     "capabilities":{"tools":{"listChanged":true}}
   }}
   ```
3. **Notify initialized**:
   ```json
   {"jsonrpc":"2.0","method":"initialized","params":{}}
   ```
4. **List tools**:
   ```json
   {"jsonrpc":"2.0","id":"<uuid>","method":"tools/list","params":{}}
   ```
5. **Call tool**:
   ```json
   {"jsonrpc":"2.0","id":"<uuid>","method":"tools/call","params":{
     "name":"probe",
     "arguments":{"url":"https://example.com","preset":"app"}
   }}
   ```

### Framing Protocol

MCP uses HTTP-like framing over stdio:

```
Content-Length: 123\r\n
\r\n
{"jsonrpc":"2.0",...}
```

The wrapper handles this automatically.

## Comparison: MCP Stdio vs HTTP Server

| Feature                | mcp_probe.py (stdio)  | devdiag-http (HTTP)  |
|------------------------|-----------------------|----------------------|
| **Authentication**     | None                  | JWT (JWKS)           |
| **Rate Limiting**      | None                  | 2 RPS (configurable) |
| **SSRF Protection**    | None                  | Yes (RFC1918 blocked)|
| **Host Allowlist**     | None                  | Yes (ALLOW_TARGET_HOSTS) |
| **Multi-Tenancy**      | No                    | Yes                  |
| **Deployment**         | Local only            | Cloud Run, K8s, Fly  |
| **Dependencies**       | Python 3.11+          | FastAPI, uvicorn     |
| **Use Case**           | Dev, IDE, pure-CLI CI | Web apps, teams      |
| **Backend Proxy**      | N/A                   | Yes (hide JWT)       |

## Contributing

When modifying `mcp_probe.py`:

1. **Preserve exit codes** - CI depends on them
2. **Maintain JSON output** - parseable by `jq`
3. **Test timeout handling** - don't hang on slow probes
4. **Update help text** - keep `--help` accurate

## License

MIT License (same as parent project)
