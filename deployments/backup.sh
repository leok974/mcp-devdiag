#!/bin/bash
# PostgreSQL Backup Script for DevDiag
# Creates compressed backup using pg_dump custom format

# Configuration
DB_HOST="${DEVDIAG_PG_HOST:-localhost}"
DB_PORT="${DEVDIAG_PG_PORT:-5432}"
DB_NAME="${DEVDIAG_PG_DB:-devdiag}"
DB_USER="${DEVDIAG_PG_USER:-devdiag}"
BACKUP_DIR="${DEVDIAG_BACKUP_DIR:-/var/backups/devdiag}"
RETENTION_DAYS="${DEVDIAG_BACKUP_RETENTION:-30}"

# Generate filename with timestamp
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="${BACKUP_DIR}/devdiag_${TIMESTAMP}.dump"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting backup to ${BACKUP_FILE}" >> "$LOG_FILE"

# Run pg_dump with custom format (-Fc)
# Custom format is compressed and allows selective restore
PGPASSWORD="$DEVDIAG_PG_PASS" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -Fc \
  -f "$BACKUP_FILE" \
  --verbose \
  2>> "$LOG_FILE"

if [ $? -eq 0 ]; then
  # Get backup file size
  BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed successfully (${BACKUP_SIZE})" >> "$LOG_FILE"
  
  # Delete old backups (older than RETENTION_DAYS)
  find "$BACKUP_DIR" -name "devdiag_*.dump" -mtime +${RETENTION_DAYS} -delete
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Cleaned up backups older than ${RETENTION_DAYS} days" >> "$LOG_FILE"
  
  exit 0
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup failed with exit code $?" >> "$LOG_FILE"
  exit 1
fi
