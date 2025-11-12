#!/usr/bin/env bash
# Example: Compare MCP stdio vs HTTP server approaches

set -e

echo "=== DevDiag Pattern Comparison ==="
echo ""

# --- MCP Stdio (Local/CI) ---
echo "1️⃣  MCP Stdio (Local/CI - No Auth)"
echo "   Use when: dev, IDE, pure-CLI CI"
echo ""

if command -v mcp-devdiag &> /dev/null; then
  echo "   Running: python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app"
  python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty | head -30
  echo "   ✅ Direct CLI access, no HTTP server needed"
else
  echo "   ⚠️  mcp-devdiag not installed (pip install mcp-devdiag)"
fi

echo ""
echo "---"
echo ""

# --- HTTP Server (Production) ---
echo "2️⃣  HTTP Server (Web Apps/Teams - JWT Auth)"
echo "   Use when: production, multi-tenant, need auth/rate limits"
echo ""

if [ -n "$DEVDIAG_URL" ] && [ -n "$DEVDIAG_JWT" ]; then
  echo "   Running: curl -X POST $DEVDIAG_URL/diag/run ..."
  curl -s -X POST "$DEVDIAG_URL/diag/run" \
    -H "Authorization: Bearer $DEVDIAG_JWT" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://www.leoklemet.com","preset":"app"}' | jq '.' | head -30
  echo "   ✅ JWT auth, rate limiting, SSRF protection"
else
  echo "   ⚠️  DEVDIAG_URL and DEVDIAG_JWT not set"
  echo "   Example: export DEVDIAG_URL=https://devdiag-http.example.run.app"
  echo "            export DEVDIAG_JWT=eyJhbG..."
fi

echo ""
echo "=== Recommendation ==="
echo "   • Local dev / IDE:       Use scripts/mcp_probe.py"
echo "   • CI (pure Python):      Use scripts/mcp_probe.py"
echo "   • Web apps (EvalForge):  Use apps/devdiag-http"
echo "   • Multi-tenant:          Use apps/devdiag-http"
echo ""
