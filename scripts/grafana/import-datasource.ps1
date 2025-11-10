# Import DevDiag PostgreSQL datasource to Grafana (PowerShell)
# Requires: $env:GRAFANA_URL, $env:GRAFANA_API_KEY, $env:DEVDIAG_PG_* variables

param(
    [string]$GrafanaUrl = $env:GRAFANA_URL,
    [string]$ApiKey = $env:GRAFANA_API_KEY,
    [string]$PgHost = $env:DEVDIAG_PG_HOST,
    [string]$PgUser = $env:DEVDIAG_PG_USER,
    [string]$PgPass = $env:DEVDIAG_PG_PASS,
    [string]$PgDb = $env:DEVDIAG_PG_DB
)

# Validate required parameters
$required = @{
    'GRAFANA_URL' = $GrafanaUrl
    'GRAFANA_API_KEY' = $ApiKey
    'DEVDIAG_PG_HOST' = $PgHost
    'DEVDIAG_PG_USER' = $PgUser
    'DEVDIAG_PG_PASS' = $PgPass
    'DEVDIAG_PG_DB' = $PgDb
}

foreach ($param in $required.GetEnumerator()) {
    if ([string]::IsNullOrEmpty($param.Value)) {
        Write-Error "Missing required environment variable: $($param.Key)"
        exit 1
    }
}

$DatasourceName = "DevDiag Postgres"
$DatasourceUid = "devdiag-postgres"

Write-Host "→ Ensuring datasource '$DatasourceName' (uid=$DatasourceUid) exists…" -ForegroundColor Cyan

# Check if datasource exists
$headers = @{
    "Authorization" = "Bearer $ApiKey"
    "Content-Type" = "application/json"
}

$exists = $false
try {
    $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/datasources/uid/$DatasourceUid" `
        -Method Get -Headers $headers -ErrorAction SilentlyContinue
    $exists = $true
} catch {
    $exists = $false
}

# Prepare datasource payload
$payload = @{
    name = $DatasourceName
    type = "postgres"
    uid = $DatasourceUid
    access = "proxy"
    url = $PgHost
    user = $PgUser
    secureJsonData = @{
        password = $PgPass
    }
    jsonData = @{
        database = $PgDb
        sslmode = "disable"
        postgresVersion = 1600
        timescaledb = $false
    }
    isDefault = $false
} | ConvertTo-Json -Depth 10

try {
    if ($exists) {
        Write-Host "✓ Found — updating datasource" -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/datasources/uid/$DatasourceUid" `
            -Method Put -Headers $headers -Body $payload
        Write-Host $response.message -ForegroundColor Green
    } else {
        Write-Host "• Not found — creating datasource" -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "$GrafanaUrl/api/datasources" `
            -Method Post -Headers $headers -Body $payload
        Write-Host $response.message -ForegroundColor Green
    }
    Write-Host "✓ Datasource ready." -ForegroundColor Green
} catch {
    Write-Error "Failed to import datasource: $_"
    exit 1
}
