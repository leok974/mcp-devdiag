# Example: Compare MCP stdio vs HTTP server approaches

Write-Host "=== DevDiag Pattern Comparison ===" -ForegroundColor Cyan
Write-Host ""

# --- MCP Stdio (Local/CI) ---
Write-Host "1️⃣  MCP Stdio (Local/CI - No Auth)" -ForegroundColor Green
Write-Host "   Use when: dev, IDE, pure-CLI CI"
Write-Host ""

if (Get-Command mcp-devdiag -ErrorAction SilentlyContinue) {
  Write-Host "   Running: python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app"
  python scripts/mcp_probe.py --url https://www.leoklemet.com --preset app --pretty | Select-Object -First 30
  Write-Host "   ✅ Direct CLI access, no HTTP server needed" -ForegroundColor Green
} else {
  Write-Host "   ⚠️  mcp-devdiag not installed (pip install mcp-devdiag)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "---"
Write-Host ""

# --- HTTP Server (Production) ---
Write-Host "2️⃣  HTTP Server (Web Apps/Teams - JWT Auth)" -ForegroundColor Green
Write-Host "   Use when: production, multi-tenant, need auth/rate limits"
Write-Host ""

if ($env:DEVDIAG_URL -and $env:DEVDIAG_JWT) {
  Write-Host "   Running: curl -X POST $env:DEVDIAG_URL/diag/run ..."
  $body = @{
    url = "https://www.leoklemet.com"
    preset = "app"
  } | ConvertTo-Json
  
  $response = Invoke-RestMethod -Uri "$env:DEVDIAG_URL/diag/run" `
    -Method Post `
    -Headers @{ "Authorization" = "Bearer $env:DEVDIAG_JWT"; "Content-Type" = "application/json" } `
    -Body $body
  
  $response | ConvertTo-Json -Depth 10 | Select-Object -First 30
  Write-Host "   ✅ JWT auth, rate limiting, SSRF protection" -ForegroundColor Green
} else {
  Write-Host "   ⚠️  DEVDIAG_URL and DEVDIAG_JWT not set" -ForegroundColor Yellow
  Write-Host "   Example: `$env:DEVDIAG_URL = 'https://devdiag-http.example.run.app'"
  Write-Host "            `$env:DEVDIAG_JWT = 'eyJhbG...'"
}

Write-Host ""
Write-Host "=== Recommendation ===" -ForegroundColor Cyan
Write-Host "   • Local dev / IDE:       Use scripts/mcp_probe.py"
Write-Host "   • CI (pure Python):      Use scripts/mcp_probe.py"
Write-Host "   • Web apps (EvalForge):  Use apps/devdiag-http"
Write-Host "   • Multi-tenant:          Use apps/devdiag-http"
Write-Host ""
