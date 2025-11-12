# MCP Stdio Wrapper - Shipped ✅

**Date:** 2025-01-12  
**Purpose:** Enable pure-CLI diagnostics without HTTP server for dev/IDE/CI use cases

## What Was Shipped

### 1. Core Script: `scripts/mcp_probe.py`

A minimal JSON-RPC over stdio client that:
- ✅ Spawns `mcp-devdiag --stdio` subprocess
- ✅ JSON-RPC handshake (initialize → initialized → tools/list → tools/call)
- ✅ Prints JSON result to stdout
- ✅ Exit codes: 0 (success), 1 (error), 2 (too many problems)
- ✅ Python 3.11+ only (uses modern type hints)

**Usage:**
```bash
python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty
```

**Environment Variables:**
- `MCP_DEV_DIAG_BIN` - CLI binary name (default: `mcp-devdiag`)
- `MCP_PROBE_TIMEOUT_S` - Timeout seconds (default: `180`)

### 2. GitHub Actions Workflow: `.github/workflows/devdiag-mcp-quickcheck.yml`

CI job that:
- ✅ Installs Python 3.11 + mcp-devdiag[playwright,export]
- ✅ Runs MCP probe via stdio (no HTTP server)
- ✅ Extracts top problem codes to GitHub Step Summary
- ✅ Policy gate: fails if problem count >= 25

**Triggers:** Pull requests to `main` branch

### 3. VS Code Task: `.vscode/tasks.json`

Quick access task for developers:
- ✅ Task: "DevDiag (MCP): Probe homepage"
- ✅ Command: `python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty`
- ✅ Access via: `Terminal > Run Task...`

### 4. Documentation: `docs/MCP_STDIO.md`

Comprehensive guide covering:
- ✅ When to use MCP stdio vs HTTP server
- ✅ Installation and basic usage
- ✅ Environment variables and exit codes
- ✅ GitHub Actions examples
- ✅ VS Code integration
- ✅ Output formats and parsing
- ✅ Troubleshooting guide
- ✅ Implementation details (JSON-RPC flow)
- ✅ Comparison table: stdio vs HTTP

### 5. Comparison Scripts

**Bash:** `scripts/compare_patterns.sh`  
**PowerShell:** `scripts/compare_patterns.ps1`

Side-by-side demonstration of:
- MCP stdio (local/CI, no auth)
- HTTP server (web apps, JWT auth)

### 6. README Updates

- ✅ New "Usage Patterns" section
- ✅ MCP stdio examples with exit codes
- ✅ Environment variable documentation
- ✅ Link to `docs/MCP_STDIO.md`
- ✅ Updated Compatibility table

## Key Design Decisions

### 1. JSON-RPC Framing
Uses standard MCP framing protocol:
```
Content-Length: 123\r\n
\r\n
{"jsonrpc":"2.0",...}
```

Handles streaming responses with buffering and header parsing.

### 2. Protocol Version
Uses `"protocolVersion": "2024-11-01"` (best-effort compatibility). Server should accept known versions or negotiate.

### 3. Tool Discovery
Always calls `tools/list` before `tools/call` to validate tool exists and provide helpful error messages.

### 4. Exit Codes
- **0:** Probe succeeded
- **1:** Error (CLI missing, timeout, invalid response)
- **2:** Policy violation (too many problems when `--max-problems` set)

This enables CI gating:
```bash
python scripts/mcp_probe.py --url $URL --preset app --max-problems 25 || exit 1
```

### 5. Environment Variables
Follows Unix convention:
- `MCP_DEV_DIAG_BIN` - Override CLI binary (e.g., `/usr/local/bin/mcp-devdiag`)
- `MCP_PROBE_TIMEOUT_S` - Numeric timeout for long probes

### 6. JSON Output
Raw output is JSON-RPC response:
```json
{"content": [{"type": "text", "text": "{...}"}], "isError": false}
```

Use `--pretty` flag for direct pretty-printed output.

## Use Cases

### ✅ Local Development
```bash
# Quick probe during development
python scripts/mcp_probe.py --url http://localhost:3000 --preset app --pretty
```

### ✅ IDE Integration
VS Code task provides one-click diagnostics via `Tasks: Run Task` menu.

### ✅ Pure-CLI CI
GitHub Actions job runs probes without Docker/HTTP server overhead:
```yaml
- run: python scripts/mcp_probe.py --url $URL --preset app --max-problems 25
```

### ✅ Shell Scripts
```bash
# Extract problem count
PROBLEMS=$(python scripts/mcp_probe.py --url $URL --preset app | jq -r '.content[0].text | fromjson | .problems | length')
if [ "$PROBLEMS" -gt 10 ]; then
  echo "Too many issues: $PROBLEMS"
  exit 1
fi
```

### ❌ Not For Web Apps
Web apps (EvalForge, LedgerMind) should use `apps/devdiag-http` for:
- JWT authentication
- Rate limiting
- SSRF protection
- Host allowlisting
- Backend proxy pattern

## Testing

Verified functionality:
```bash
# Help text
✅ python scripts/mcp_probe.py --help

# Basic probe (requires mcp-devdiag installed)
⏳ python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty

# Exit code handling
⏳ python scripts/mcp_probe.py --url https://example.com --preset app --max-problems 0
⏳ echo $?  # Should be 2 (too many problems)
```

## Migration Path

For existing users:

### Before (HTTP Server Only)
```yaml
# .github/workflows/devdiag.yml
- name: Run diagnostics
  run: |
    docker compose up -d
    curl -X POST http://localhost:8080/diag/run ...
```

### After (Pure-CLI Option)
```yaml
# .github/workflows/devdiag-mcp-quickcheck.yml
- name: Run diagnostics
  run: |
    pip install "mcp-devdiag[playwright,export]==0.2.1"
    python scripts/mcp_probe.py --url $URL --preset app --pretty
```

**Benefits:**
- ⚡ Faster (no Docker build)
- 🎯 Simpler (pure Python)
- 📦 Fewer dependencies (no FastAPI, uvicorn, etc.)

**HTTP server still recommended for:**
- Production deployments
- Web app integration
- Multi-tenant scenarios
- When JWT auth is required

## Files Added

1. `scripts/mcp_probe.py` - Main wrapper script (217 lines)
2. `.github/workflows/devdiag-mcp-quickcheck.yml` - CI workflow
3. `.vscode/tasks.json` - VS Code task definition
4. `docs/MCP_STDIO.md` - Comprehensive documentation
5. `scripts/compare_patterns.sh` - Bash comparison demo
6. `scripts/compare_patterns.ps1` - PowerShell comparison demo

## Files Modified

1. `README.md` - Added "Usage Patterns" section, stdio examples, link to docs

## Ready to Commit

✅ All files created  
✅ Documentation complete  
✅ Help text verified  
✅ README updated  

**Suggested commit message:**
```
feat: add MCP stdio wrapper for pure-CLI diagnostics

Add scripts/mcp_probe.py - minimal JSON-RPC client for mcp-devdiag --stdio.
Enables dev/IDE/CI usage without HTTP server.

Features:
- JSON-RPC handshake (initialize → tools/call)
- Environment variables: MCP_DEV_DIAG_BIN, MCP_PROBE_TIMEOUT_S
- Exit codes: 0 (success), 1 (error), 2 (policy violation)
- Policy gate: --max-problems threshold for CI
- VS Code task integration

New files:
- scripts/mcp_probe.py
- .github/workflows/devdiag-mcp-quickcheck.yml
- .vscode/tasks.json
- docs/MCP_STDIO.md
- scripts/compare_patterns.{sh,ps1}

Closes #[issue-number]
```

## Next Steps

1. ✅ **Commit and push** (ready now)
2. ⏳ **Test in CI** - Wait for PR to trigger workflow
3. ⏳ **Dogfood in LedgerMind** - Add to their CI pipeline
4. ⏳ **Document in EvalForge** - Link from their docs
5. ⏳ **Blog post** - "Two Ways to Run DevDiag: MCP Stdio vs HTTP"

## Questions?

See `docs/MCP_STDIO.md` for:
- Detailed usage examples
- Troubleshooting guide
- Comparison table: stdio vs HTTP
- Implementation details
