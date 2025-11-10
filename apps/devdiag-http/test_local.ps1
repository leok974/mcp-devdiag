# Quick local smoke test for devdiag-http server (PowerShell)
# Run after: pip install -r requirements.txt && uvicorn main:app --reload --port 8080

$ErrorActionPreference = "Stop"
$BASE = "http://127.0.0.1:8080"

Write-Host "🔍 Testing DevDiag HTTP Server..." -ForegroundColor Cyan
Write-Host ""

Write-Host "1️⃣ Health check..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "$BASE/healthz" -Method Get
$health | ConvertTo-Json
Write-Host "✅ Health check passed" -ForegroundColor Green
Write-Host ""

Write-Host "2️⃣ Probe presets..." -ForegroundColor Yellow
$presets = Invoke-RestMethod -Uri "$BASE/probes" -Method Get
$presets | ConvertTo-Json
Write-Host "✅ Presets check passed" -ForegroundColor Green
Write-Host ""

Write-Host "3️⃣ Full diagnostic run..." -ForegroundColor Yellow
$body = @{
    url = "https://www.leoklemet.com"
    preset = "app"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "$BASE/diag/run" -Method Post -Body $body -ContentType "application/json"
Write-Host "ok: $($result.ok)" -ForegroundColor Cyan
Write-Host "✅ Diagnostic run passed" -ForegroundColor Green
Write-Host ""

Write-Host "🎉 All tests passed! Server is working correctly." -ForegroundColor Green
