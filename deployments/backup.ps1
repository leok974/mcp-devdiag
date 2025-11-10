# Backup Script for DevDiag PostgreSQL (PowerShell)
# Windows-compatible version of backup.sh

# Configuration
$DB_HOST = if ($env:DEVDIAG_PG_HOST) { $env:DEVDIAG_PG_HOST } else { "localhost" }
$DB_PORT = if ($env:DEVDIAG_PG_PORT) { $env:DEVDIAG_PG_PORT } else { "5432" }
$DB_NAME = if ($env:DEVDIAG_PG_DB) { $env:DEVDIAG_PG_DB } else { "devdiag" }
$DB_USER = if ($env:DEVDIAG_PG_USER) { $env:DEVDIAG_PG_USER } else { "devdiag" }
$BACKUP_DIR = if ($env:DEVDIAG_BACKUP_DIR) { $env:DEVDIAG_BACKUP_DIR } else { "D:\backups\devdiag" }
$RETENTION_DAYS = if ($env:DEVDIAG_BACKUP_RETENTION) { [int]$env:DEVDIAG_BACKUP_RETENTION } else { 30 }

# Generate filename with timestamp
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BACKUP_FILE = Join-Path $BACKUP_DIR "devdiag_${TIMESTAMP}.dump"
$LOG_FILE = Join-Path $BACKUP_DIR "backup.log"

# Create backup directory if it doesn't exist
if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR | Out-Null
}

$LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Starting backup to ${BACKUP_FILE}"
Add-Content -Path $LOG_FILE -Value $LogEntry
Write-Host $LogEntry

# Set password environment variable for pg_dump
$env:PGPASSWORD = $env:DEVDIAG_PG_PASS

try {
    # Run pg_dump using Docker container
    docker exec devdiag-postgres pg_dump `
        -h $DB_HOST `
        -p $DB_PORT `
        -U $DB_USER `
        -d $DB_NAME `
        -Fc `
        --verbose `
        2>&1 | Set-Content -Path $BACKUP_FILE -Encoding Byte
    
    if ($LASTEXITCODE -eq 0) {
        $BackupSize = (Get-Item $BACKUP_FILE).Length
        $BackupSizeMB = [math]::Round($BackupSize / 1MB, 2)
        
        $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Backup completed successfully (${BackupSizeMB} MB)"
        Add-Content -Path $LOG_FILE -Value $LogEntry
        Write-Host $LogEntry -ForegroundColor Green
        
        # Delete old backups
        $CutoffDate = (Get-Date).AddDays(-$RETENTION_DAYS)
        Get-ChildItem -Path $BACKUP_DIR -Filter "devdiag_*.dump" | 
            Where-Object { $_.LastWriteTime -lt $CutoffDate } | 
            Remove-Item -Force
        
        $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Cleaned up backups older than ${RETENTION_DAYS} days"
        Add-Content -Path $LOG_FILE -Value $LogEntry
        Write-Host $LogEntry
        
        exit 0
    } else {
        throw "pg_dump failed with exit code $LASTEXITCODE"
    }
} catch {
    $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Backup failed: $_"
    Add-Content -Path $LOG_FILE -Value $LogEntry
    Write-Host $LogEntry -ForegroundColor Red
    exit 1
} finally {
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
