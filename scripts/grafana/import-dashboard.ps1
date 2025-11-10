# Import DevDiag Analytics dashboard to Grafana (PowerShell)
# Requires: $env:GRAFANA_URL, $env:GRAFANA_API_KEY variables

param(
    [string]$GrafanaUrl = $env:GRAFANA_URL,
    [string]$ApiKey = $env:GRAFANA_API_KEY,
    [string]$DashboardPath = "deployments\grafana\dashboards\devdiag-analytics.json"
)

# Validate required parameters
if ([string]::IsNullOrEmpty($GrafanaUrl)) {
    Write-Error "Missing required environment variable: GRAFANA_URL"
    exit 1
}

if ([string]::IsNullOrEmpty($ApiKey)) {
    Write-Error "Missing required environment variable: GRAFANA_API_KEY"
    exit 1
}

# Check if dashboard file exists
if (-not (Test-Path $DashboardPath)) {
    Write-Error "Dashboard JSON not found: $DashboardPath"
    exit 1
}

Write-Host "→ Importing dashboard from $DashboardPath" -ForegroundColor Cyan

# Read dashboard JSON
$dashboardContent = Get-Content -Path $DashboardPath -Raw | ConvertFrom-Json

# Prepare import payload
$importPayload = @{
    dashboard = $dashboardContent.dashboard
    folderId = 0
    overwrite = $true
} | ConvertTo-Json -Depth 100

$headers = @{
    "Authorization" = "Bearer $ApiKey"
    "Content-Type" = "application/json"
}

try {
    $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/dashboards/db" `
        -Method Post -Headers $headers -Body $importPayload
    
    Write-Host "✓ $($response.status): $($response.slug)" -ForegroundColor Green
    Write-Host "  Dashboard URL: $GrafanaUrl/d/$($response.uid)" -ForegroundColor Cyan
} catch {
    Write-Error "Failed to import dashboard: $_"
    if ($_.ErrorDetails.Message) {
        Write-Error "Details: $($_.ErrorDetails.Message)"
    }
    exit 1
}
