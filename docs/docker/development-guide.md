# ProScrape Docker Development Guide

This comprehensive guide covers Docker-based development workflows, monitoring, and deployment for the ProScrape real estate scraping platform.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Environment](#development-environment)
3. [Service URLs](#service-urls)
4. [Common Development Tasks](#common-development-tasks)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Database Management](#database-management)
7. [Testing](#testing)
8. [Debugging](#debugging)
9. [Production Deployment](#production-deployment)
10. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- Git
- Make (optional, for simplified commands)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ProScrape
   ```

2. **Set up environment**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your settings
   nano .env
   ```

3. **Start development environment**
   ```bash
   # Using Make (recommended)
   make dev-up
   
   # Or using Docker Compose directly
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

4. **Seed database with sample data**
   ```bash
   make seed-dev
   ```

5. **Verify services are running**
   ```bash
   make status-dev
   ```

## Development Environment

### Architecture Overview

The development environment consists of:

- **API Service**: FastAPI application with hot-reload
- **Celery Worker**: Background task processor
- **Celery Beat**: Task scheduler
- **MongoDB**: Document database
- **Redis**: Message broker and cache
- **Flower**: Celery monitoring interface
- **Mongo Express**: MongoDB web interface
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **Loki + Promtail**: Log aggregation

### Environment Configuration

Key environment variables in `.env`:

```bash
# Database
MONGODB_URL=mongodb://admin:password@mongodb:27017/proscrape_dev?authSource=admin

# Redis
REDIS_URL=redis://redis:6379

# API Configuration
API_DEBUG=true
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Scraping Configuration
DOWNLOAD_DELAY=1.0
SS_ENABLED=true
CITY24_ENABLED=true
PP_ENABLED=true
```

## Service URLs

When running the development environment, access services at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8000 | - |
| **API Documentation** | http://localhost:8000/docs | - |
| **Flower (Celery)** | http://localhost:5555 | admin:dev |
| **Mongo Express** | http://localhost:8081 | admin:admin123 |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3001 | admin:admin123 |
| **Loki** | http://localhost:3100 | - |

### Database Access

| Service | Connection String |
|---------|-------------------|
| **MongoDB** | mongodb://admin:password@localhost:27017/proscrape_dev?authSource=admin |
| **Redis** | redis://localhost:6379 |

## Common Development Tasks

### Using Make Commands

```bash
# Development lifecycle
make dev-up          # Start all development services
make dev-down        # Stop development services
make dev-restart     # Restart all services
make dev-rebuild     # Rebuild and restart services

# Monitoring
make logs            # Follow all container logs
make logs-api        # Follow API logs only
make logs-worker     # Follow worker logs only
make status-dev      # Show container status

# Database operations
make seed-dev        # Seed database with sample data
make shell-api       # Shell into API container
make shell-worker    # Shell into worker container
make shell-mongo     # MongoDB shell
make shell-redis     # Redis CLI

# Testing
make test            # Run test suite
make test-coverage   # Run tests with coverage report

# Utilities
make clean-dev       # Remove all containers and volumes
make monitor         # Show monitoring dashboard URLs
```

### Manual Docker Compose Commands

```bash
# Start services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f api
docker-compose logs -f celery_worker

# Execute commands in containers
docker-compose exec api python scripts/seed_data.py
docker-compose exec api pytest tests/
docker-compose exec api bash

# Stop services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

## Monitoring and Observability

### Prometheus Metrics

Access Prometheus at http://localhost:9090

Key metrics to monitor:
- `http_requests_total` - API request count
- `celery_workers_total` - Active Celery workers
- `celery_task_sent_total` - Tasks sent to queue
- `celery_task_succeeded_total` - Successfully completed tasks
- `celery_task_failed_total` - Failed tasks

### Grafana Dashboards

Access Grafana at http://localhost:3001 (admin:admin123)

Pre-configured dashboards:
- **ProScrape Overview**: Application metrics and health
- **Container Resources**: CPU, memory, disk usage
- **Database Performance**: MongoDB query performance
- **System Logs**: Aggregated application logs

### Log Aggregation

Logs are collected by Promtail and stored in Loki:
- Application logs from all containers
- System logs
- Container logs with metadata

Query logs in Grafana using LogQL:
```logql
{job="proscrape-api"} |= "ERROR"
{container_name="proscrape_celery_worker"} |= "task"
```

## Database Management

### MongoDB Operations

```bash
# Connect to MongoDB shell
make shell-mongo

# In MongoDB shell
use proscrape_dev
db.listings.countDocuments()
db.listings.find().limit(5)
db.listings.createIndex({listing_id: 1}, {unique: true})
```

### Database Seeding

```bash
# Seed with default data (50 listings per source)
make seed-dev

# Seed with custom amount
docker-compose exec api python scripts/seed_data.py 100

# Validate data integrity
docker-compose exec api python scripts/validate_data.py
```

### Data Validation

The validation script checks:
- Required field completeness
- Data type consistency
- Business logic validation
- Index presence
- Data quality metrics

## Testing

### Unit Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
docker-compose exec api pytest tests/test_models.py -v

# Run with debugging
docker-compose exec api pytest tests/ -v -s --pdb
```

### Integration Tests

```bash
# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/listings?limit=5

# Test WebSocket connection
wscat -c ws://localhost:8000/ws
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/listings

# Using wrk
wrk -t12 -c400 -d30s http://localhost:8000/listings
```

## Debugging

### Python Debugging

1. **Set breakpoint in code:**
   ```python
   import debugpy
   debugpy.breakpoint()
   ```

2. **Attach VS Code debugger:**
   - Use "Docker: FastAPI" debug configuration
   - Connect to localhost:5678

3. **Or debug in container:**
   ```bash
   docker-compose exec api python -c "import debugpy; debugpy.listen(('0.0.0.0', 5678)); debugpy.wait_for_client(); import your_module"
   ```

### Log Analysis

```bash
# Follow real-time logs
make logs-api

# Search logs for errors
docker-compose logs api 2>&1 | grep ERROR

# Export logs for analysis
docker-compose logs --no-color api > api.log
```

### Service Health Checks

```bash
# Check service health
make health

# Manual health checks
curl http://localhost:8000/health
curl http://localhost:5555/api/workers
```

## Production Deployment

### Building Production Images

```bash
# Build production images
make build-prod

# Tag and push to registry
docker tag proscrape-api:latest your-registry.com/proscrape-api:v1.0.0
docker push your-registry.com/proscrape-api:v1.0.0
```

### Production Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    image: your-registry.com/proscrape-api:latest
    environment:
      - API_DEBUG=false
      - LOG_LEVEL=INFO
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
```

### Environment-Specific Deployments

```bash
# Staging deployment
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

#### Services Not Starting

```bash
# Check container status
make status-dev

# Check logs for errors
make logs

# Rebuild containers
make dev-rebuild
```

#### Database Connection Issues

```bash
# Check MongoDB logs
docker-compose logs mongodb

# Verify connection string
docker-compose exec api python -c "
from utils.database import get_database
import asyncio
async def test():
    db = await get_database()
    print('Connected to:', db.name)
asyncio.run(test())
"
```

#### Port Conflicts

```bash
# Check what's using ports
netstat -tulpn | grep :8000
lsof -i :8000

# Change ports in docker-compose.dev.yml
```

#### Permission Issues (Linux/Mac)

```bash
# Fix ownership of mounted volumes
sudo chown -R $USER:$USER .

# Use proper user in Dockerfile
USER 1000:1000
```

### Performance Tuning

#### Memory Optimization

```yaml
# In docker-compose.dev.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

#### Worker Scaling

```bash
# Scale workers dynamically
docker-compose up -d --scale celery_worker=3

# Check worker status
curl http://localhost:5555/api/workers
```

### Backup and Recovery

#### Database Backup

```bash
# Create backup
make backup-data

# Manual backup
docker-compose exec mongodb mongodump --out /tmp/backup
docker cp $(docker-compose ps -q mongodb):/tmp/backup ./backups/
```

#### Volume Management

```bash
# List volumes
docker volume ls

# Backup volume
docker run --rm -v proscrape_mongodb_data:/data -v $(pwd):/backup alpine tar czf /backup/mongodb-backup.tar.gz /data

# Restore volume
docker run --rm -v proscrape_mongodb_data:/data -v $(pwd):/backup alpine tar xzf /backup/mongodb-backup.tar.gz -C /
```

## Development Workflow

### Recommended Development Process

1. **Start development environment**
   ```bash
   make dev-up
   ```

2. **Make code changes**
   - API code is auto-reloaded on changes
   - Worker code requires container restart

3. **Test changes**
   ```bash
   make test
   ```

4. **Validate data**
   ```bash
   docker-compose exec api python scripts/validate_data.py
   ```

5. **Check monitoring**
   - View Grafana dashboards
   - Check Prometheus metrics
   - Review logs in Loki

6. **Commit changes**
   - GitHub Actions will run CI/CD pipeline
   - Automated testing and security scanning
   - Deployment to staging/production

### Code Quality

The project uses:
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing
- **bandit**: Security linting

Run quality checks:
```bash
black .
isort .
flake8 .
mypy api/ models/ utils/
```

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

For support or questions, check the project's GitHub issues or create a new issue.