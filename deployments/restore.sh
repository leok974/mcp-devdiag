#!/bin/bash
# PostgreSQL Restore Script for DevDiag
# Restores from pg_dump custom format backup

# Configuration
DB_HOST="${DEVDIAG_PG_HOST:-localhost}"
DB_PORT="${DEVDIAG_PG_PORT:-5432}"
DB_NAME="${DEVDIAG_PG_DB:-devdiag}"
DB_USER="${DEVDIAG_PG_USER:-devdiag}"
BACKUP_DIR="${DEVDIAG_BACKUP_DIR:-/var/backups/devdiag}"

# Check if backup file is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <backup_file.dump>"
  echo ""
  echo "Available backups in ${BACKUP_DIR}:"
  ls -lh "${BACKUP_DIR}"/devdiag_*.dump 2>/dev/null || echo "No backups found"
  exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

echo "WARNING: This will overwrite the current database!"
echo "Database: ${DB_NAME} on ${DB_HOST}:${DB_PORT}"
echo "Backup file: ${BACKUP_FILE}"
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

echo "Starting restore from ${BACKUP_FILE}..."

# Drop existing schema (use with caution!)
# Uncomment if you want to start fresh
# PGPASSWORD="$DEVDIAG_PG_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
#   -c "DROP SCHEMA IF EXISTS devdiag CASCADE;"

# Restore from backup
# -c: clean (drop existing objects)
# -1: restore in single transaction
PGPASSWORD="$DEVDIAG_PG_PASS" pg_restore \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -c \
  -1 \
  --verbose \
  "$BACKUP_FILE"

if [ $? -eq 0 ]; then
  echo "Restore completed successfully"
  
  # Run ANALYZE to update statistics
  PGPASSWORD="$DEVDIAG_PG_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -c "ANALYZE devdiag.diag_run; ANALYZE devdiag.fix_outcome;"
  
  echo "Database statistics updated"
  exit 0
else
  echo "Restore failed with exit code $?"
  exit 1
fi
