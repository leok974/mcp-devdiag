# MCP Stdio Quick Reference

## 🚀 One-Liners (Copy/Paste)

### Basic Probe
```bash
python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty
```

### CI Policy Gate
```bash
python scripts/mcp_probe.py --url $URL --preset app --max-problems 25
```

### Suppress Known Issues
```bash
python scripts/mcp_probe.py --url $URL --preset app --suppress CSP_FRAME_ANCESTORS PORTAL_ROOT_MISSING --pretty
```

### Custom Timeout (Slow Sites)
```bash
python scripts/mcp_probe.py --url $URL --preset full --timeout 300
```

## 🔧 Environment Variables

```bash
export MCP_DEV_DIAG_BIN="mcp-devdiag"     # CLI binary name
export MCP_PROBE_TIMEOUT_S=180            # Timeout (seconds)
```

## 📤 Exit Codes

- **0** - Success
- **1** - Error (CLI missing, timeout, invalid response)
- **2** - Too many problems (policy gate)

## 🎯 Presets

- `chat` - Chat widget embedding
- `embed` - Generic iframe embedding
- `app` - Full app diagnostics (CSP, CORS, headers)
- `full` - All checks (app + browser runtime)

## 📊 Parse Results

### Extract Problem Count
```bash
PROBLEMS=$(python scripts/mcp_probe.py --url $URL --preset app | jq -r '.content[0].text | fromjson | .problems | length')
```

### List Problem Codes
```bash
python scripts/mcp_probe.py --url $URL --preset app --pretty | jq -r '.problems[]?.code'
```

### Filter by Severity
```bash
python scripts/mcp_probe.py --url $URL --preset app --pretty | jq '.problems[] | select(.severity == "error")'
```

## 🐙 GitHub Actions

```yaml
- name: Install deps
  run: pip install "mcp-devdiag[playwright,export]==0.2.1" jq

- name: Run probe
  run: python scripts/mcp_probe.py --url $URL --preset app --pretty > diag.json

- name: Policy gate
  run: jq -e '(.problems // [] | length) < 25' diag.json
```

## 🆚 When to Use What

| Use Case                  | Tool                        |
|---------------------------|-----------------------------|
| Local dev                 | `scripts/mcp_probe.py`      |
| IDE integration           | `scripts/mcp_probe.py`      |
| Pure-CLI CI               | `scripts/mcp_probe.py`      |
| Web app (EvalForge)       | `apps/devdiag-http`         |
| Multi-tenant              | `apps/devdiag-http`         |
| Need JWT auth             | `apps/devdiag-http`         |
| Rate limiting required    | `apps/devdiag-http`         |

## 📚 Documentation

- **Full Guide:** [docs/MCP_STDIO.md](../docs/MCP_STDIO.md)
- **HTTP Server:** [apps/devdiag-http/README.md](../apps/devdiag-http/README.md)
- **Main README:** [README.md](../README.md)

## 🔍 VS Code Task

`Terminal > Run Task... > DevDiag (MCP): Probe homepage`

## 🛟 Troubleshooting

### CLI Not Found
```bash
pip install mcp-devdiag
# Or set custom path:
export MCP_DEV_DIAG_BIN="/usr/local/bin/mcp-devdiag"
```

### Timeout
```bash
python scripts/mcp_probe.py --url $URL --preset app --timeout 300
```

### Invalid Tool
```bash
# Check available tools:
python scripts/mcp_probe.py --help
# Use custom tool:
python scripts/mcp_probe.py --url $URL --tool my_tool
```

---

**Quick Help:** `python scripts/mcp_probe.py --help`
