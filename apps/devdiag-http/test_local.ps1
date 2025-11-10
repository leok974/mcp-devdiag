# Comprehensive smoke test for devdiag-http server (PowerShell)
# Usage: .\test_local.ps1 [base_url]

param(
    [string]$BaseUrl = "http://127.0.0.1:8080"
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 DevDiag HTTP Server Smoke Test" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health check (GET)
Write-Host "1️⃣ Testing GET /healthz..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "$BaseUrl/healthz" -Method Get
$health | ConvertTo-Json
if ($health.ok -eq $true) {
    Write-Host "✅ Health check passed" -ForegroundColor Green
} else {
    Write-Host "❌ Health check failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: Health check (HEAD)
Write-Host "2️⃣ Testing HEAD /healthz..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/healthz" -Method Head
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ HEAD /healthz passed" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ HEAD /healthz failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 3: Metrics endpoint
Write-Host "3️⃣ Testing GET /metrics..." -ForegroundColor Yellow
$metrics = Invoke-RestMethod -Uri "$BaseUrl/metrics" -Method Get
if ($metrics -match "devdiag_http_up 1") {
    Write-Host "✅ Metrics endpoint passed" -ForegroundColor Green
    Write-Host ($metrics -split "`n" | Select-Object -First 10)
} else {
    Write-Host "❌ Metrics endpoint failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 4: Probe presets
Write-Host "4️⃣ Testing GET /probes..." -ForegroundColor Yellow
$presets = Invoke-RestMethod -Uri "$BaseUrl/probes" -Method Get
$presets | ConvertTo-Json
if ($presets.presets.Count -gt 0) {
    Write-Host "✅ Probes endpoint passed" -ForegroundColor Green
} else {
    Write-Host "❌ Probes endpoint failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 5: Diagnostic run (example.com)
Write-Host "5️⃣ Testing POST /diag/run (example.com)..." -ForegroundColor Yellow
$body = @{
    url = "https://example.com"
    preset = "app"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "$BaseUrl/diag/run" -Method Post -Body $body -ContentType "application/json"
Write-Host "ok: $($result.ok)" -ForegroundColor Cyan
if ($result.ok -eq $true) {
    Write-Host "✅ Diagnostic run passed" -ForegroundColor Green
} else {
    Write-Host "❌ Diagnostic run failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 6: Diagnostic run with suppress
Write-Host "6️⃣ Testing POST /diag/run with suppress codes..." -ForegroundColor Yellow
$bodySuppress = @{
    url = "https://example.com"
    preset = "app"
    suppress = @("CSP_FRAME_ANCESTORS")
} | ConvertTo-Json

$resultSuppress = Invoke-RestMethod -Uri "$BaseUrl/diag/run" -Method Post -Body $bodySuppress -ContentType "application/json"
if ($resultSuppress.ok -eq $true) {
    Write-Host "✅ Diagnostic run with suppress passed" -ForegroundColor Green
} else {
    Write-Host "❌ Diagnostic run with suppress failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "🎉 All smoke tests passed!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  ✅ Health check (GET + HEAD)"
Write-Host "  ✅ Metrics endpoint"
Write-Host "  ✅ Probes list"
Write-Host "  ✅ Diagnostic run"
Write-Host "  ✅ Suppress codes"
