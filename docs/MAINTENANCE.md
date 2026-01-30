# Cerberus CTF Platform - Maintenance Guide

> Day-to-day operations guide for managing the Cerberus CTF Platform in production.

---

## Table of Contents

- [Overview](#overview)
- [Backup Operations](#backup-operations)
- [Restore Operations](#restore-operations)
- [Log Management](#log-management)
- [Database Migrations](#database-migrations)
- [Updates & Upgrades](#updates--upgrades)
- [Monitoring](#monitoring)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

---

## Overview

This guide covers routine maintenance tasks for the Cerberus CTF Platform:

- Database backups and restores
- Log viewing and management
- Application updates
- Health monitoring
- Common administrative tasks

---

## Backup Operations

### Manual Backup

Trigger a manual database backup using the backup script:

```bash
# Run backup script
python scripts/backup_db.py

# Or with full path
cd /opt/cerberus && python scripts/backup_db.py
```

**What it does:**
1. Dumps PostgreSQL database to SQL
2. Compresses with gzip
3. Uploads to S3 (MinIO)
4. Cleans up old backups based on retention policy

### Automated Backups

Set up automated daily backups using cron:

```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /opt/cerberus && /usr/bin/python3 scripts/backup_db.py >> /var/log/cerberus/backup.log 2>&1
```

Or use the provided setup script:

```bash
# Make script executable
chmod +x scripts/setup-backup-cron.sh

# Run setup script
sudo ./scripts/setup-backup-cron.sh
```

### Backup Verification

```bash
# List backups in S3
docker exec cerberus-minio mc ls myminio/cerberus-backups/backups/

# Check backup log
tail -f /var/log/cerberus/backup.log

# Download and verify a backup
docker exec cerberus-minio mc cp myminio/cerberus-backups/backups/cerberus_20240129_020000.sql.gz /tmp/
gunzip -t /tmp/cerberus_20240129_020000.sql.gz
```

### Backup Retention

Default retention is 30 days. Configure via environment variable:

```bash
# In .env file
BACKUP_RETENTION_DAYS=30
```

---

## Restore Operations

### Restore from Backup

To restore the database from a `.sql.gz` backup file:

#### Option 1: Restore from Local File

```bash
# Navigate to project directory
cd /opt/cerberus

# Stop the backend to prevent writes
docker-compose stop backend

# Copy backup file to container
docker cp /path/to/backup/cerberus_20240129_020000.sql.gz cerberus-postgres:/tmp/

# Enter PostgreSQL container
docker exec -it cerberus-postgres bash

# Inside the container:
# 1. Drop existing database
psql -U cerberus -c "DROP DATABASE IF EXISTS cerberus;"

# 2. Create new database
psql -U cerberus -c "CREATE DATABASE cerberus;"

# 3. Decompress and restore
gunzip -c /tmp/cerberus_20240129_020000.sql.gz | psql -U cerberus -d cerberus

# Exit container
exit

# Restart backend
docker-compose start backend
```

#### Option 2: Restore from S3/MinIO

```bash
# Download backup from MinIO
docker exec cerberus-minio mc cp myminio/cerberus-backups/backups/cerberus_20240129_020000.sql.gz /tmp/

# Copy to host
docker cp cerberus-minio:/tmp/cerberus_20240129_020000.sql.gz /tmp/

# Follow Option 1 steps above
```

#### Option 3: Quick Restore Script

```bash
#!/bin/bash
# save as restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup_file.sql.gz>"
    exit 1
fi

echo "Stopping backend..."
docker-compose -f /opt/cerberus/config/docker-compose.yml stop backend

echo "Restoring database..."
docker cp "$BACKUP_FILE" cerberus-postgres:/tmp/restore.sql.gz
docker exec cerberus-postgres bash -c "
    gunzip -c /tmp/restore.sql.gz | psql -U \$POSTGRES_USER -d \$POSTGRES_DB
"

echo "Restarting backend..."
docker-compose -f /opt/cerberus/config/docker-compose.yml start backend

echo "Restore complete!"
```

### Point-in-Time Recovery

If you need to restore to a specific point in time:

```bash
# List available backups
docker exec cerberus-minio mc ls myminio/cerberus-backups/backups/ | sort

# Choose the backup closest to your target time
# Then follow restore steps above
```

---

## Log Management

### View Container Logs

```bash
# View all container logs
docker-compose logs

# View specific container logs
docker logs -f cerberus-backend
docker logs -f cerberus-postgres
docker logs -f cerberus-redis
docker logs -f cerberus-nginx

# View last 100 lines
docker logs --tail 100 cerberus-backend

# View logs with timestamps
docker logs -t cerberus-backend

# View logs since specific time
docker logs --since 2024-01-29T10:00:00 cerberus-backend
```

### Backend Application Logs

```bash
# Real-time backend logs
docker logs -f ctf-backend

# Or using docker-compose
cd /opt/cerberus/config && docker-compose logs -f backend
```

### Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log

# Cerberus-specific logs
sudo tail -f /var/log/nginx/cerberus/access.log
```

### Backup Logs

```bash
# View backup script logs
tail -f /var/log/cerberus/backup.log

# Search for errors
grep ERROR /var/log/cerberus/backup.log
```

### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# Create logrotate config
sudo tee /etc/logrotate.d/cerberus << 'EOF'
/var/log/cerberus/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 cerberus cerberus
    sharedscripts
    postrotate
        /usr/bin/docker kill --signal="USR1" cerberus-nginx 2>/dev/null || true
    endscript
}
EOF

# Test logrotate
sudo logrotate -d /etc/logrotate.d/cerberus
```

---

## Database Migrations

### Check Migration Status

```bash
# View current migration version
docker exec cerberus-backend alembic current

# View migration history
docker exec cerberus-backend alembic history
```

### Run Migrations

```bash
# Upgrade to latest version
docker exec cerberus-backend alembic upgrade head

# Upgrade to specific version
docker exec cerberus-backend alembic upgrade <revision_id>

# Upgrade one step
docker exec cerberus-backend alembic upgrade +1
```

### Create New Migration

```bash
# Auto-generate migration from model changes
docker exec cerberus-backend alembic revision --autogenerate -m "description_of_changes"

# Manual migration
docker exec cerberus-backend alembic revision -m "manual_migration"
```

### Downgrade Migrations

```bash
# Downgrade one step
docker exec cerberus-backend alembic downgrade -1

# Downgrade to specific version
docker exec cerberus-backend alembic downgrade <revision_id>

# Downgrade to base
docker exec cerberus-backend alembic downgrade base
```

**⚠️ Warning:** Downgrading may result in data loss. Always backup before downgrading.

---

## Updates & Upgrades

### Application Update Process

```bash
# 1. Navigate to project directory
cd /opt/cerberus

# 2. Backup database
python scripts/backup_db.py

# 3. Pull latest code
git pull origin main

# 4. Update environment variables if needed
vim .env

# 5. Rebuild and restart containers
cd config
docker-compose down
docker-compose up -d --build

# 6. Run database migrations
docker exec cerberus-backend alembic upgrade head

# 7. Verify deployment
docker-compose ps
curl https://ctf.com/health
```

### Update Specific Services

```bash
# Update only backend
docker-compose up -d --build backend

# Update only nginx
docker-compose up -d --build nginx

# Rolling update (zero downtime)
docker-compose up -d --no-deps --build backend
```

### System Package Updates

```bash
# Update Ubuntu packages
sudo apt-get update
sudo apt-get upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d

# Clean up old images
docker image prune -f
```

---

## Monitoring

### Container Health Checks

```bash
# View container status
docker-compose ps

# Check container health
docker inspect --format='{{.State.Health.Status}}' cerberus-backend

# View health check logs
docker inspect --format='{{json .State.Health}}' cerberus-backend | jq
```

### Resource Monitoring

```bash
# Container resource usage
docker stats

# System resource usage
htop

# Disk usage
df -h
docker system df

# Clean up unused resources
docker system prune -f
docker volume prune -f
```

### Database Monitoring

```bash
# Connect to PostgreSQL
docker exec -it cerberus-postgres psql -U cerberus -d cerberus

# Check active connections
SELECT count(*) FROM pg_stat_activity;

# Check database size
SELECT pg_size_pretty(pg_database_size('cerberus'));

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname='public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Redis Monitoring

```bash
# Connect to Redis
docker exec -it cerberus-redis redis-cli

# Check info
INFO

# Monitor commands
MONITOR

# Check memory usage
INFO memory
```

---

## Common Tasks

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
docker-compose restart postgres

# Force recreate
docker-compose up -d --force-recreate backend
```

### Clear Cache

```bash
# Clear Redis cache
docker exec cerberus-redis redis-cli FLUSHALL

# Restart backend to clear application cache
docker-compose restart backend
```

### Reset Admin Password

```bash
# Access backend container
docker exec -it cerberus-backend bash

# Run Python script to reset password
python -c "
import asyncio
from app.services.auth_service import AuthService
from app.core.database import get_db

async def reset_password():
    async for db in get_db():
        # Replace with actual user ID and new password
        await AuthService.reset_password(db, user_id='admin-uuid', new_password='newpassword')
        print('Password reset successful')

asyncio.run(reset_password())
"
```

### Manage Challenge Instances

```bash
# List running challenge containers
docker ps --filter "label=cerberus.challenge"

# Stop all challenge instances
docker ps --filter "label=cerberus.challenge" -q | xargs docker stop

# Remove all challenge instances
docker ps -a --filter "label=cerberus.challenge" -q | xargs docker rm
```

### Database Maintenance

```bash
# Analyze tables for query optimization
docker exec cerberus-postgres psql -U cerberus -d cerberus -c "ANALYZE;"

# Vacuum database
docker exec cerberus-postgres psql -U cerberus -d cerberus -c "VACUUM FULL;"

# Check for index bloat
docker exec cerberus-postgres psql -U cerberus -d cerberus -c "
SELECT
    schemaname || '.' || tablename AS table_name,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
"

# Reindex all tables
docker exec cerberus-postgres psql -U cerberus -d cerberus -c "REINDEX DATABASE cerberus;"
```

---

## Troubleshooting

### Common Issues

#### Backend Won't Start

```bash
# Check backend logs
docker logs cerberus-backend

# Common causes:
# 1. Database connection failed - check PostgreSQL is running
docker ps | grep postgres

# 2. Environment variables not set - verify .env file
docker exec cerberus-backend env | grep -E "(DATABASE|SECRET)"

# 3. Port already in use - check for conflicting services
sudo netstat -tlnp | grep -E "(8000|5432|6379)"
```

#### Database Connection Issues

```bash
# Test PostgreSQL connection
docker exec -it cerberus-postgres psql -U cerberus -d cerberus

# Check PostgreSQL logs
docker logs cerberus-postgres

# Verify database URL format
# postgresql+asyncpg://user:password@host:port/database
```

#### High Memory Usage

```bash
# Check container memory usage
docker stats --no-stream

# PostgreSQL memory tuning
docker exec cerberus-postgres psql -U cerberus -d cerberus -c "SHOW work_mem;"

# Restart containers with memory limits
docker-compose restart

# Clean up Docker resources
docker system prune -af
docker volume prune -f
```

#### Nginx 502 Bad Gateway

```bash
# Check backend is running
docker ps | grep backend

# Test backend health
curl http://localhost:8000/health

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Verify Nginx configuration
sudo nginx -t
```

#### WebSocket Connection Failed

```bash
# Check WebSocket endpoint
curl -i http://localhost:8000/ws

# Verify WebSocket is enabled in Nginx
# Check nginx.conf for ws location block

# Test with websocat (if available)
websocat ws://localhost:8000/ws
```

### Emergency Procedures

#### Full System Reset (Destructive)

```bash
# WARNING: This will delete ALL data
cd /opt/cerberus/config

# Stop all containers
docker-compose down -v

# Remove all volumes
docker volume rm $(docker volume ls -q)

# Rebuild and start fresh
docker-compose up -d

# Re-run migrations
docker exec cerberus-backend alembic upgrade head
```

#### Emergency Database Restore

```bash
# Quick restore from latest backup
BACKUP=$(docker exec cerberus-minio mc ls myminio/cerberus-backups/backups/ | tail -1 | awk '{print $5}')
docker exec cerberus-minio mc cp myminio/cerberus-backups/backups/$BACKUP /tmp/

# Copy to host
docker cp cerberus-minio:/tmp/$BACKUP /tmp/

# Restore (see Restore Operations section)
```

#### Stop All Challenge Instances (Emergency)

```bash
# Force stop all running challenges
docker ps --filter "label=cerberus.challenge" -q | xargs docker stop -t 0

# Remove all challenge containers
docker ps -a --filter "label=cerberus.challenge" -q | xargs docker rm -v

# Clean up challenge networks
docker network prune -f
```

### Getting Help

If you encounter issues not covered here:

1. Check application logs: `docker logs cerberus-backend`
2. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Search existing issues: [GitHub Issues](https://github.com/your-org/cerberus/issues)
4. Create a new issue with:
   - Error messages
   - Steps to reproduce
   - Environment details (`docker-compose ps`)

---

## Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| View all logs | `docker-compose logs -f` |
| Restart backend | `docker-compose restart backend` |
| Run migrations | `docker exec cerberus-backend alembic upgrade head` |
| Create backup | `python scripts/backup_db.py` |
| Check status | `docker-compose ps` |
| View resources | `docker stats` |
| SSH to backend | `docker exec -it cerberus-backend bash` |
| SSH to database | `docker exec -it cerberus-postgres psql -U cerberus` |
| View API docs | Open http://localhost:8000/docs |

### Service Ports

| Service | Port | Container |
|---------|------|-----------|
| Frontend | 3000 | Next.js (dev) |
| Backend API | 8000 | FastAPI |
| PostgreSQL | 5432 | postgres |
| Redis | 6379 | redis |
| MinIO S3 | 9000 | minio |
| MinIO Console | 9001 | minio |

---

<p align="center">
  Keep your CTF platform running smoothly! 🛡️
</p>
