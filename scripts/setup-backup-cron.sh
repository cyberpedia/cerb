#!/bin/bash
# Setup script for database backup cron job

CRON_SCHEDULE="${1:-0 2 * * *}"  # Default: 2 AM daily
SCRIPT_PATH="/opt/cerberus/scripts/backup-cron.sh"
CRON_COMMENT="# Cerberus DB Backup"

echo "Setting up Cerberus database backup cron job..."
echo "Schedule: $CRON_SCHEDULE"

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: Backup script not found at $SCRIPT_PATH"
    exit 1
fi

# Make scripts executable
chmod +x "$SCRIPT_PATH"
chmod +x "$(dirname "$SCRIPT_PATH")/backup_db.py"

# Create log directory
mkdir -p /var/log/cerberus

# Remove existing cron job if present
(crontab -l 2>/dev/null | grep -v "$CRON_COMMENT" | grep -v "backup-cron.sh") | crontab -

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $SCRIPT_PATH $CRON_COMMENT") | crontab -

echo "Cron job installed successfully!"
echo ""
echo "Current crontab:"
crontab -l | grep -A1 -B1 cerberus
echo ""
echo "To verify backup works, run: $SCRIPT_PATH"
echo "To change schedule, edit crontab: crontab -e"
