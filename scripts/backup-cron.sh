#!/bin/bash
# Cron job wrapper for database backup script
# Add to crontab: 0 2 * * * /opt/cerberus/scripts/backup-cron.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="/opt/cerberus/.env"
LOG_FILE="/var/log/cerberus/backup-cron.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Run backup with logging
{
    echo "=== Backup started at $(date) ==="
    
    # Check if backup script exists
    if [ ! -f "$SCRIPT_DIR/backup_db.py" ]; then
        echo "ERROR: backup_db.py not found"
        exit 1
    fi
    
    # Run backup
    python3 "$SCRIPT_DIR/backup_db.py" 2>&1
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "=== Backup completed successfully at $(date) ==="
    else
        echo "=== Backup FAILED at $(date) with exit code $EXIT_CODE ==="
        # Send alert (configure as needed)
        # echo "Backup failed on $(hostname)" | mail -s "Cerberus Backup Alert" admin@ctf.com
    fi
    
    echo ""
} >> "$LOG_FILE" 2>&1

exit $EXIT_CODE
