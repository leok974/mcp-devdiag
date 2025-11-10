# Import DevDiag alert rules to Grafana (PowerShell)
# Requires: $env:GRAFANA_URL, $env:GRAFANA_API_KEY

param(
    [string]$GrafanaUrl = $env:GRAFANA_URL,
    [string]$ApiKey = $env:GRAFANA_API_KEY,
    [string]$AlertsDir = "deployments\grafana\alerts"
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

$FolderUid = "devdiag-alerts"
$FolderTitle = "DevDiag Alerts"

Write-Host "→ Ensuring alert folder '$FolderTitle' exists…" -ForegroundColor Cyan

$headers = @{
    "Authorization" = "Bearer $ApiKey"
    "Content-Type" = "application/json"
}

# Check if folder exists
$folderExists = $false
try {
    $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/folders/$FolderUid" `
        -Method Get -Headers $headers -ErrorAction SilentlyContinue
    $folderExists = $true
    Write-Host "✓ Folder exists" -ForegroundColor Green
} catch {
    Write-Host "• Creating folder" -ForegroundColor Yellow
    
    $folderPayload = @{
        uid = $FolderUid
        title = $FolderTitle
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/folders" `
            -Method Post -Headers $headers -Body $folderPayload
        Write-Host "  Created folder UID: $($response.uid)" -ForegroundColor Green
    } catch {
        Write-Warning "Failed to create folder: $_"
    }
}

Write-Host ""
Write-Host "→ Importing alert rules from $AlertsDir..." -ForegroundColor Cyan

# Get all JSON files in alerts directory
$alertFiles = Get-ChildItem -Path $AlertsDir -Filter "*.json" -ErrorAction SilentlyContinue

if (-not $alertFiles) {
    Write-Warning "No alert files found in $AlertsDir"
    exit 0
}

foreach ($alertFile in $alertFiles) {
    $alertName = $alertFile.BaseName
    Write-Host "  • Importing: $alertName" -ForegroundColor White
    
    try {
        # Read alert JSON
        $alertData = Get-Content -Path $alertFile.FullName -Raw | ConvertFrom-Json
        
        # Wrap in alert rule group payload
        $payload = @{
            name = $alertName
            interval = "1m"
            rules = @($alertData)
        } | ConvertTo-Json -Depth 20
        
        # POST to Grafana
        $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/v1/provisioning/alert-rules" `
            -Method Post `
            -Headers (@{
                "Authorization" = "Bearer $ApiKey"
                "Content-Type" = "application/json"
                "X-Disable-Provenance" = "true"
            }) `
            -Body $payload -ErrorAction SilentlyContinue
        
        Write-Host "    ✓ Imported UID: $($response.uid)" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 409) {
            Write-Host "    ⚠️  Alert already exists" -ForegroundColor Yellow
        } else {
            Write-Warning "    Failed: $_"
        }
    }
}

Write-Host ""
Write-Host "✓ Alert import complete" -ForegroundColor Green
Write-Host "  View at: $GrafanaUrl/alerting/list" -ForegroundColor Cyan
