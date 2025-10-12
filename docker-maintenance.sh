#!/bin/bash
# =====================================================
# Docker Maintenance Script for Joe's Compose Stack
# =====================================================
# This script updates, refreshes, and cleans the system
# Run manually or automatically via cron
# =====================================================

COMPOSE_DIR="/home/joe/compose-stack"
LOGFILE="$COMPOSE_DIR/logs/maintenance.log"
DATESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== Docker Maintenance Started at $DATESTAMP ===" >> "$LOGFILE"

cd "$COMPOSE_DIR" || {
    echo "[ERROR] Cannot access $COMPOSE_DIR" >> "$LOGFILE"
    exit 1
}

# Pull the latest container images
echo "[INFO] Pulling latest images..." >> "$LOGFILE"
docker-compose pull >> "$LOGFILE" 2>&1

# Recreate containers and remove any orphans
echo "[INFO] Recreating containers and cleaning orphans..." >> "$LOGFILE"
docker-compose up -d --remove-orphans >> "$LOGFILE" 2>&1

# Cleanup old images, stopped containers, and unused volumes/networks
echo "[INFO] Running docker system prune..." >> "$LOGFILE"
docker system prune -af >> "$LOGFILE" 2>&1

echo "[SUCCESS] Docker maintenance completed at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOGFILE"
echo "------------------------------------------------------------" >> "$LOGFILE"

