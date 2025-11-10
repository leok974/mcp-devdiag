#!/bin/bash
# Daily retention cleanup cron job for DevDiag PostgreSQL
# Add to crontab: 0 2 * * * /path/to/retention-cleanup.sh

# Configuration
DB_HOST="${DEVDIAG_PG_HOST:-localhost}"
DB_PORT="${DEVDIAG_PG_PORT:-5432}"
DB_NAME="${DEVDIAG_PG_DB:-devdiag}"
DB_USER="${DEVDIAG_PG_USER:-devdiag}"
LOG_FILE="/var/log/devdiag-retention.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting retention cleanup" >> "$LOG_FILE"

# Run the retention SQL script
PGPASSWORD="$DEVDIAG_PG_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  -f "$(dirname "$0")/retention-cleanup.sql" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Cleanup completed successfully" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Cleanup failed with exit code $?" >> "$LOG_FILE"
  exit 1
fi
