#!/bin/bash
# =====================================================
# Docker Configuration Backup Script for Joe's Stack
# =====================================================
# Creates a timestamped .tar.gz archive of all
# container configuration data under:
#   /home/joe/compose-stack/services
# Stored in:
#   /if/backups/compose/
# Logs to:
#   /home/joe/compose-stack/logs/backup.log
# =====================================================

BACKUP_SRC="/home/joe/compose-stack/services"
BACKUP_DEST="/if/backups/compose"
LOGFILE="/home/joe/compose-stack/logs/backup.log"
DATESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
ARCHIVE_NAME="compose-backup-${DATESTAMP}.tar.gz"

echo "=== Backup started at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOGFILE"

# Verify source exists
if [ ! -d "$BACKUP_SRC" ]; then
  echo "[ERROR] Backup source directory not found: $BACKUP_SRC" >> "$LOGFILE"
  exit 1
fi

# Create archive
echo "[INFO] Creating archive: $ARCHIVE_NAME" >> "$LOGFILE"
tar -czf "${BACKUP_DEST}/${ARCHIVE_NAME}" -C "$BACKUP_SRC" . >> "$LOGFILE" 2>&1

# Keep only the last 14 days of backups
echo "[INFO] Removing backups older than 14 days..." >> "$LOGFILE"
find "$BACKUP_DEST" -type f -name "compose-backup-*.tar.gz" -mtime +14 -delete

echo "[SUCCESS] Backup completed at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOGFILE"
echo "------------------------------------------------------------" >> "$LOGFILE"
