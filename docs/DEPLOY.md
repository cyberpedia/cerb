# Cerberus CTF Platform - Production Deployment Guide

> Complete guide for deploying Cerberus on Ubuntu 24.04 with Docker, Nginx, and SSL/TLS.

---

## Table of Contents

- [Overview](#overview)
- [System Requirements](#system-requirements)
- [Ubuntu 24.04 Setup](#ubuntu-2404-setup)
- [Docker & Docker Compose Installation](#docker--docker-compose-installation)
- [Application Deployment](#application-deployment)
- [Nginx Configuration](#nginx-configuration)
- [SSL/TLS with Certbot](#ssltls-with-certbot)
- [Firewall Configuration](#firewall-configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers deploying Cerberus CTF Platform on a fresh Ubuntu 24.04 server using:

- **Docker Compose** for container orchestration
- **Nginx** as reverse proxy
- **Let's Encrypt** for SSL/TLS certificates
- **UFW** for firewall management

---

## System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 4 cores | 8 cores |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 50 GB SSD | 100 GB SSD |
| **Network** | 100 Mbps | 1 Gbps |

### Required Ports

| Port | Service | Description |
|------|---------|-------------|
| 22 | SSH | Remote access |
| 80 | HTTP | Web traffic (redirects to HTTPS) |
| 443 | HTTPS | Secure web traffic |
| 9000 | MinIO S3 | Object storage API |
| 9001 | MinIO Console | Object storage UI |

---

## Ubuntu 24.04 Setup

### 1. Update System Packages

```bash
# Update package lists
sudo apt-get update

# Upgrade existing packages
sudo apt-get upgrade -y

# Install essential tools
sudo apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ufw \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
```

### 2. Install Python 3.12

```bash
# Python 3.12 is included in Ubuntu 24.04
sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip

# Verify installation
python3.12 --version
```

### 3. Install Node.js 20

```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Install Node.js
sudo apt-get install -y nodejs

# Verify installation
node --version  # Should show v20.x.x
npm --version
```

### 4. Create Application User

```bash
# Create dedicated user for the application
sudo useradd -r -s /bin/false -m -d /opt/cerberus cerberus

# Add current user to cerberus group
sudo usermod -aG cerberus $USER

# Create required directories
sudo mkdir -p /opt/cerberus
sudo mkdir -p /var/log/cerberus
sudo mkdir -p /var/backups/cerberus

# Set ownership
sudo chown -R cerberus:cerberus /opt/cerberus
sudo chown -R cerberus:cerberus /var/log/cerberus
sudo chown -R cerberus:cerberus /var/backups/cerberus
```

---

## Docker & Docker Compose Installation

### 1. Install Docker

```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update and install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
sudo usermod -aG docker cerberus

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker compose version
```

### 2. Install Docker Compose (Standalone)

```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make executable
sudo chmod +x /usr/local/bin/docker-compose

# Create symlink
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installation
docker-compose --version
```

---

## Application Deployment

### 1. Clone Repository

```bash
# Switch to cerberus user
sudo su - cerberus

# Clone repository
cd /opt/cerberus
git clone <repository-url> .
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate a secure secret key
openssl rand -hex 32

# Edit .env with production values
vim .env
```

**Production .env example:**

```bash
# Application
SECRET_KEY=your-generated-secret-key-here
DEBUG=false
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql+asyncpg://cerberus:secure_password@postgres:5432/cerberus

# Production domain
CORS_ORIGINS=https://ctf.com,https://www.ctf.com
```

### 3. Deploy with Docker Compose

```bash
# Navigate to config directory
cd /opt/cerberus/config

# Deploy the entire stack
docker-compose -f docker-compose.yml up -d

# Verify all services are running
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Initialize Database

```bash
# Run database migrations
docker exec cerberus-backend alembic upgrade head

# Create admin user (if applicable)
docker exec -it cerberus-backend python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
"
```

---

## Nginx Configuration

### 1. Install Nginx

```bash
# Exit cerberus user if still logged in
exit

# Install Nginx
sudo apt-get install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Verify installation
nginx -v
```

### 2. Copy Nginx Configuration

```bash
# Backup default configuration
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Copy Cerberus Nginx configuration
sudo cp /opt/cerberus/config/nginx.conf /etc/nginx/nginx.conf

# Test configuration
sudo nginx -t
```

### 3. Create Required Directories

```bash
# Create log directory
sudo mkdir -p /var/log/nginx/cerberus

# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Set permissions
sudo chown -R www-data:www-data /var/log/nginx/cerberus
```

### 4. Restart Nginx

```bash
# Reload Nginx to apply new configuration
sudo systemctl reload nginx

# Or restart if needed
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

---

## SSL/TLS with Certbot

### 1. Install Certbot

```bash
# Install Certbot and Nginx plugin
sudo apt-get install -y certbot python3-certbot-nginx

# Verify installation
certbot --version
```

### 2. Obtain SSL Certificate

```bash
# Obtain certificate for main domain and wildcard
certbot certonly \
    --manual \
    --preferred-challenges=dns \
    --server https://acme-v02.api.letsencrypt.org/directory \
    -d ctf.com \
    -d www.ctf.com \
    -d *.challenges.ctf.com
```

**Note:** For wildcard certificates, you'll need to add DNS TXT records as instructed by Certbot.

### 3. Alternative: HTTP Challenge (Non-Wildcard)

```bash
# For non-wildcard certificates (simpler)
sudo certbot --nginx -d ctf.com -d www.ctf.com

# Auto-renewal is automatically configured
```

### 4. Configure Auto-Renewal

```bash
# Test auto-renewal
sudo certbot renew --dry-run

# Ensure cron job is installed
sudo systemctl status certbot.timer
```

### 5. Update Nginx SSL Paths

After obtaining certificates, ensure [`nginx.conf`](../config/nginx.conf) points to the correct paths:

```nginx
ssl_certificate /etc/letsencrypt/live/ctf.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/ctf.com/privkey.pem;
```

For wildcard challenges:

```nginx
ssl_certificate /etc/letsencrypt/live/challenges.ctf.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/challenges.ctf.com/privkey.pem;
```

### 6. Enable HTTPS Redirect

Uncomment the HTTP to HTTPS redirect in [`nginx.conf`](../config/nginx.conf):

```nginx
server {
    listen 80;
    server_name .ctf.com;
    return 301 https://$host$request_uri;
}
```

Then reload Nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Firewall Configuration

### 1. Configure UFW

```bash
# Reset UFW to default
sudo ufw reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow MinIO (optional - restrict to specific IPs in production)
sudo ufw allow 9000/tcp
sudo ufw allow 9001/tcp

# Enable UFW
sudo ufw enable

# Check status
sudo ufw status verbose
```

### 2. Docker and UFW Compatibility

Docker bypasses UFW by default. To restrict Docker container access:

```bash
# Edit Docker daemon configuration
sudo vim /etc/docker/daemon.json
```

Add:

```json
{
    "iptables": false
}
```

```bash
# Restart Docker
sudo systemctl restart docker
```

---

## Verification

### 1. Check Service Status

```bash
# Check all containers
docker ps

# Check container logs
docker logs cerberus-backend
docker logs cerberus-postgres
docker logs cerberus-redis
docker logs cerberus-nginx

# Check resource usage
docker stats
```

### 2. Test Endpoints

```bash
# Test HTTP redirect
curl -I http://ctf.com

# Test HTTPS
curl -I https://ctf.com

# Test API health
curl https://ctf.com/health

# Test WebSocket
curl -I https://ctf.com/ws
```

### 3. Verify SSL Certificate

```bash
# Check certificate details
echo | openssl s_client -servername ctf.com -connect ctf.com:443 2>/dev/null | openssl x509 -noout -dates -subject -issuer

# Test SSL configuration
nmap --script ssl-enum-ciphers -p 443 ctf.com
```

---

## Troubleshooting

### Container Issues

```bash
# View all container logs
docker-compose logs

# View specific service logs
docker-compose logs -f backend

# Restart a service
docker-compose restart backend

# Rebuild and restart
docker-compose up -d --build backend
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker logs cerberus-postgres

# Test database connection from backend container
docker exec -it cerberus-backend python -c "
import asyncio
from app.core.database import get_db
async def test():
    async for db in get_db():
        print('Database connection successful')
asyncio.run(test())
"
```

### Nginx Issues

```bash
# Test configuration
sudo nginx -t

# View error logs
sudo tail -f /var/log/nginx/error.log

# View access logs
sudo tail -f /var/log/nginx/access.log
```

### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# Revoke and reissue
sudo certbot revoke --cert-name ctf.com
sudo certbot certonly --nginx -d ctf.com -d www.ctf.com
```

---

## Post-Deployment Checklist

- [ ] All containers running (`docker ps`)
- [ ] Database migrations applied
- [ ] Nginx serving traffic on HTTPS
- [ ] SSL certificate valid
- [ ] Firewall configured
- [ ] Admin user created
- [ ] Backup script configured (see [MAINTENANCE.md](MAINTENANCE.md))
- [ ] Monitoring/logging enabled
- [ ] DNS records pointing to server

---

## Next Steps

- Configure automated backups: [MAINTENANCE.md](MAINTENANCE.md)
- Set up monitoring (Prometheus/Grafana)
- Configure log aggregation
- Review security hardening

---

For ongoing maintenance tasks, see [MAINTENANCE.md](MAINTENANCE.md).
