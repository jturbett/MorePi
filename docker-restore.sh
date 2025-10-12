#!/bin/bash
# =====================================================
# Docker Configuration Restore Script for Joe's Stack
# =====================================================
# Restores a selected backup archive from:
#   /if/backups/compose/
# to:
#   /home/joe/compose-stack/services/
# Logs to:
#   /home/joe/compose-stack/logs/restore.log
# Usage:
#   ./docker-restore.sh                → interactive mode
#   ./docker-restore.sh <backup_name>  → restore specific file
# =====================================================

BACKUP_DIR="/if/backups/compose"
RESTORE_DIR="/home/joe/compose-stack/services"
LOGFILE="/home/joe/compose-stack/logs/restore.log"
DATESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== Restore started at $DATESTAMP ===" >> "$LOGFILE"

# Check for backup directory
if [ ! -d "$BACKUP_DIR" ]; then
  echo "[ERROR] Backup directory not found: $BACKUP_DIR" | tee -a "$LOGFILE"
  exit 1
fi

# Select backup
if [ -z "$1" ]; then
  echo "Available backups:"
  ls -1t "$BACKUP_DIR"/compose-backup-*.tar.gz 2>/dev/null | nl
  echo
  read -p "Enter the number of the backup to restore: " CHOICE

  FILE=$(ls -1t "$BACKUP_DIR"/compose-backup-*.tar.gz 2>/dev/null | sed -n "${CHOICE}p")
else
  FILE="$BACKUP_DIR/$1"
fi

if [ ! -f "$FILE" ]; then
  echo "[ERROR] Backup file not found: $FILE" | tee -a "$LOGFILE"
  exit 1
fi

echo "[INFO] Selected backup: $FILE" | tee -a "$LOGFILE"
echo "[INFO] Stopping Docker containers..." | tee -a "$LOGFILE"
docker-compose -f /home/joe/compose-stack/docker-compose.yaml down >> "$LOGFILE" 2>&1

echo "[INFO] Cleaning old configs in $RESTORE_DIR..." | tee -a "$LOGFILE"
rm -rf "${RESTORE_DIR:?}"/*

echo "[INFO] Extracting archive..." | tee -a "$LOGFILE"
tar -xzf "$FILE" -C "$RESTORE_DIR" >> "$LOGFILE" 2>&1

echo "[INFO] Restoring ownership..." | tee -a "$LOGFILE"
chown -R joe:joe "$RESTORE_DIR"

echo "[INFO] Starting containers..." | tee -a "$LOGFILE"
docker-compose -f /home/joe/compose-stack/docker-compose.yaml up -d >> "$LOGFILE" 2>&1

echo "[SUCCESS] Restore completed successfully at $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOGFILE"
echo "------------------------------------------------------------" >> "$LOGFILE"
