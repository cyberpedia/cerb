# Cerberus CTF Platform

> An enterprise-grade Capture The Flag platform with dynamic challenge orchestration, real-time leaderboards, and comprehensive team management.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node.js-20+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Development Commands](#development-commands)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [License](#license)

---

## Overview

Cerberus is a modern CTF platform built with:

- **Backend**: FastAPI (Python 3.12+) with async PostgreSQL
- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Infrastructure**: Docker, Redis, RabbitMQ, MinIO (S3-compatible)
- **Security**: JWT authentication, OAuth (GitHub/Google), rate limiting
- **Features**: Dynamic challenge instances, WebSocket leaderboards, ticket system

---

## Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| **Python** | 3.12+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 20+ | [nodejs.org](https://nodejs.org/) |
| **Docker** | 24+ | [docker.com](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.20+ | Included with Docker Desktop |
| **PostgreSQL** | 16+ | Via Docker (recommended) |
| **Redis** | 7+ | Via Docker (recommended) |

### Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.12 or higher

# Check Node.js version
node --version    # Should be 20.x or higher

# Check Docker version
docker --version
docker compose version
```

---

## Quick Start

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd cerberus
```

### 2. Install Dependencies

```bash
make install
```

This installs:
- Python dependencies from `requirements.txt`
- Node.js dependencies from `package.json`

### 3. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Start Infrastructure Services

```bash
make db-up
```

This starts PostgreSQL and Redis via Docker Compose.

### 5. Run the Application

In separate terminals:

```bash
# Terminal 1 - Backend API
make run-api

# Terminal 2 - Frontend UI
make run-ui
```

### 6. Access the Platform

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## Environment Variables

Create a `.env` file in the project root. See [`.env.example`](.env.example) for the complete template.

### Required Variables

```bash
# =============================================================================
# CORE APPLICATION
# =============================================================================
SECRET_KEY=your-super-secret-key-change-this-in-production
DEBUG=false
ENVIRONMENT=development

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cerberus

# =============================================================================
# REDIS
# =============================================================================
REDIS_URL=redis://localhost:6379/0

# =============================================================================
# OAUTH PROVIDERS (Optional)
# =============================================================================
OAUTH_GITHUB_CLIENT_ID=your-github-client-id
OAUTH_GITHUB_CLIENT_SECRET=your-github-client-secret
OAUTH_GOOGLE_CLIENT_ID=your-google-client-id
OAUTH_GOOGLE_CLIENT_SECRET=your-google-client-secret

# =============================================================================
# MINIO / S3 STORAGE
# =============================================================================
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=cerberus-files
S3_SECURE=false

# =============================================================================
# RABBITMQ
# =============================================================================
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### Complete .env.example

<details>
<summary>Click to expand full .env.example</summary>

```bash
# =============================================================================
# CERBERUS CTF PLATFORM - ENVIRONMENT CONFIGURATION
# =============================================================================

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------
APP_NAME=Cerberus
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=development
SECRET_KEY=change-this-to-a-secure-random-string-min-32-chars
LOG_LEVEL=INFO

# -----------------------------------------------------------------------------
# Database (PostgreSQL)
# -----------------------------------------------------------------------------
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cerberus
DATABASE_ECHO=false
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Individual components (for scripts/backup_db.py)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cerberus
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# -----------------------------------------------------------------------------
# Redis
# -----------------------------------------------------------------------------
REDIS_URL=redis://localhost:6379/0

# -----------------------------------------------------------------------------
# Security & Authentication
# -----------------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256
PASSWORD_MIN_LENGTH=8

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# -----------------------------------------------------------------------------
# OAuth Providers (Optional)
# -----------------------------------------------------------------------------
OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=

# -----------------------------------------------------------------------------
# File Upload
# -----------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB=10
AVATAR_UPLOAD_PATH=uploads/avatars

# -----------------------------------------------------------------------------
# MinIO / S3-Compatible Storage
# -----------------------------------------------------------------------------
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=cerberus-files
S3_SECURE=false

# -----------------------------------------------------------------------------
# RabbitMQ
# -----------------------------------------------------------------------------
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# -----------------------------------------------------------------------------
# Docker / Dynamic Challenge Instances
# -----------------------------------------------------------------------------
DOCKER_REGISTRY=localhost:5000
INSTANCE_CLEANUP_INTERVAL=300
DEFAULT_INSTANCE_TTL=3600

# -----------------------------------------------------------------------------
# Backup Configuration
# -----------------------------------------------------------------------------
BACKUP_DIR=/tmp/backups
BACKUP_RETENTION_DAYS=30
```

</details>

---

## Development Commands

Use the [`Makefile`](Makefile) for common tasks:

| Command | Description |
|---------|-------------|
| `make install` | Install Python and Node.js dependencies |
| `make db-up` | Start PostgreSQL and Redis containers |
| `make db-down` | Stop PostgreSQL and Redis containers |
| `make run-api` | Start FastAPI development server |
| `make run-ui` | Start Next.js development server |
| `make test` | Run all tests |
| `make test-backend` | Run backend tests with pytest |
| `make lint` | Run linting on Python and TypeScript |
| `make format` | Format code with black and prettier |
| `make migrate` | Run database migrations (alembic) |
| `make migrate-create` | Create a new migration |
| `make backup` | Trigger manual database backup |
| `make clean` | Clean up generated files and caches |

---

## Project Structure

```
cerberus/
├── app/                    # Backend FastAPI application
│   ├── api/               # API routes (auth, challenges, admin)
│   ├── core/              # Configuration, database, dependencies
│   ├── middleware/        # Security middleware
│   ├── models/            # SQLAlchemy ORM models
│   └── services/          # Business logic services
├── src/                   # Frontend Next.js application
│   ├── app/              # Next.js app router pages
│   ├── components/       # React components
│   ├── hooks/            # Custom React hooks
│   └── lib/              # Utility functions
├── config/               # Configuration files
│   ├── docker-compose.yml
│   └── nginx.conf
├── scripts/              # Utility scripts
│   ├── backup_db.py
│   └── setup-backup-cron.sh
├── tests/                # Test suites
├── docs/                 # Documentation
│   ├── DEPLOY.md
│   └── MAINTENANCE.md
├── public/               # Static assets
├── Makefile             # Development commands
├── requirements.txt     # Python dependencies
└── package.json         # Node.js dependencies
```

---

## Documentation

- **[DEPLOY.md](docs/DEPLOY.md)** - Production deployment guide
- **[MAINTENANCE.md](docs/MAINTENANCE.md)** - Day-to-day operations

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/your-org/cerberus/issues) page.

---

<p align="center">
  Built with ❤️ for the CTF community
</p>
