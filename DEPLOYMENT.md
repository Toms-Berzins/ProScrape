# ProScrape Deployment Guide

This guide covers how to deploy ProScrape in different environments, from local development to production.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)  
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- MongoDB 7.0+
- Redis 7.0+
- At least 2GB RAM
- 10GB+ storage space

### Required Services
- **MongoDB**: For storing scraped listing data
- **Redis**: For Celery task queue and caching
- **Playwright browsers**: For dynamic content scraping

## Local Development Setup

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd ProScrape

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
playwright install-deps chromium
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# At minimum, configure:
# - MONGODB_URL
# - REDIS_URL
```

### 4. Start Services Locally

```bash
# Start MongoDB (if not using Docker)
mongod --dbpath /path/to/db

# Start Redis (if not using Docker)  
redis-server

# Test database connection
python test_connection.py
```

### 5. Run Development Server

```bash
# Start API server
python run.py api

# In another terminal, start Celery worker
python run.py worker

# In another terminal, start Celery beat (scheduler)
python run.py beat

# Optional: Start Celery flower (monitoring)
python run.py flower
```

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Services Included
- **mongodb**: MongoDB database
- **redis**: Redis for task queue
- **api**: FastAPI application
- **celery_worker**: Background task processor
- **celery_beat**: Task scheduler
- **celery_flower**: Task monitoring UI

### Service URLs
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Celery Flower**: http://localhost:5555
- **MongoDB**: localhost:27017

## Production Deployment

### 1. Environment Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Production Configuration

Create production environment file:

```bash
# .env.production
MONGODB_URL=mongodb://admin:secure_password@mongodb:27017/proscrape?authSource=admin
REDIS_URL=redis://redis:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Security settings
LOG_LEVEL=WARNING

# Scraping configuration
DOWNLOAD_DELAY=2.0
CONCURRENT_REQUESTS_PER_DOMAIN=1

# Site configuration
SS_COM_ENABLED=true
CITY24_ENABLED=true
PP_LV_ENABLED=true
```

### 3. Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: secure_password
    volumes:
      - mongodb_data:/data/db
    networks:
      - proscrape_network

  redis:
    image: redis:7.2-alpine
    restart: unless-stopped
    command: redis-server --requirepass secure_redis_password
    volumes:
      - redis_data:/data
    networks:
      - proscrape_network

  api:
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    depends_on:
      - mongodb
      - redis
    networks:
      - proscrape_network

  celery_worker:
    build: .
    restart: unless-stopped
    command: celery -A tasks.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - .env.production
    depends_on:
      - mongodb
      - redis
    networks:
      - proscrape_network

  celery_beat:
    build: .
    restart: unless-stopped
    command: celery -A tasks.celery_app beat --loglevel=info
    env_file:
      - .env.production
    depends_on:
      - mongodb
      - redis
    networks:
      - proscrape_network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    networks:
      - proscrape_network

volumes:
  mongodb_data:
  redis_data:

networks:
  proscrape_network:
    driver: bridge
```

### 4. Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream proscrape_api {
        server api:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://proscrape_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://proscrape_api/health;
            access_log off;
        }
    }
}
```

### 5. Deploy to Production

```bash
# Deploy with production configuration
docker-compose -f docker-compose.prod.yml up -d

# Monitor deployment
docker-compose -f docker-compose.prod.yml logs -f
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` | Yes |
| `MONGODB_DATABASE` | Database name | `proscrape` | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | Yes |
| `API_HOST` | FastAPI host | `0.0.0.0` | No |
| `API_PORT` | FastAPI port | `8000` | No |
| `API_DEBUG` | Enable debug mode | `false` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `LOG_FILE` | Log file path | `proscrape.log` | No |
| `DOWNLOAD_DELAY` | Delay between requests | `1.0` | No |
| `SS_COM_ENABLED` | Enable ss.com scraping | `true` | No |
| `CITY24_ENABLED` | Enable city24.lv scraping | `true` | No |
| `PP_LV_ENABLED` | Enable pp.lv scraping | `true` | No |

### Scraping Schedule

Default schedule (configured in `tasks/celery_app.py`):

- **Individual sites**: Once every 24 hours
- **All sites**: Once every 12 hours  
- **Cleanup task**: Weekly

Customize in production:

```python
# Custom schedule
beat_schedule = {
    'scrape-all-sites-hourly': {
        'task': 'tasks.scraping_tasks.scrape_all_sites',
        'schedule': 60 * 60.0,  # Every hour
    },
}
```

## Monitoring and Maintenance

### Health Checks

```bash
# API health check
curl http://localhost:8000/health

# Database connection test
python test_connection.py

# Celery worker status
celery -A tasks.celery_app inspect active
```

### Monitoring Endpoints

- **API Health**: `GET /health`
- **Database Stats**: `GET /stats`
- **Celery Flower**: `http://localhost:5555`

### Log Management

```bash
# View API logs
docker-compose logs -f api

# View worker logs  
docker-compose logs -f celery_worker

# View all logs
docker-compose logs -f

# Log rotation is handled automatically
```

### Database Maintenance

```bash
# Connect to MongoDB
docker-compose exec mongodb mongosh -u admin -p

# View collection stats
db.listings.stats()

# Create backup
docker-compose exec mongodb mongodump -u admin -p --out /backup

# Restore backup
docker-compose exec mongodb mongorestore -u admin -p /backup
```

### Performance Monitoring

Monitor these metrics:

- **API response times**: Check `/health` endpoint
- **Database performance**: MongoDB slow query log
- **Task queue**: Celery Flower dashboard
- **Memory usage**: Docker stats
- **Disk space**: Log files and database size

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check MongoDB is running
docker-compose ps mongodb

# Check connection string
python test_connection.py

# Check network connectivity
docker-compose exec api ping mongodb
```

#### 2. Playwright Browser Issues

```bash
# Reinstall browsers
docker-compose exec celery_worker playwright install chromium

# Check browser dependencies
docker-compose exec celery_worker playwright install-deps chromium
```

#### 3. Celery Worker Not Processing Tasks

```bash
# Check worker status
celery -A tasks.celery_app inspect active

# Restart workers
docker-compose restart celery_worker

# Check Redis connectivity
docker-compose exec celery_worker redis-cli -h redis ping
```

#### 4. High Memory Usage

```bash
# Monitor memory usage
docker stats

# Reduce worker concurrency
# In docker-compose.yml:
command: celery -A tasks.celery_app worker --loglevel=info --concurrency=1
```

#### 5. Scraping Failures

```bash
# Check spider logs
docker-compose logs celery_worker | grep spider

# Test individual spider
docker-compose exec celery_worker scrapy crawl ss_spider

# Check proxy configuration
# Review utils/proxies.py settings
```

### Log Analysis

```bash
# Find errors in logs
docker-compose logs | grep ERROR

# Monitor scraping progress
docker-compose logs celery_worker | grep "Successfully scraped"

# Check API access logs
docker-compose logs api | grep "GET /"
```

### Performance Tuning

#### For High-Volume Scraping

```yaml
# Increase worker concurrency
celery_worker:
  command: celery -A tasks.celery_app worker --concurrency=4
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G
```

#### For Limited Resources

```yaml
# Reduce memory usage
celery_worker:
  command: celery -A tasks.celery_app worker --concurrency=1 --prefetch-multiplier=1
  environment:
    - DOWNLOAD_DELAY=3.0
    - CONCURRENT_REQUESTS_PER_DOMAIN=1
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T mongodb mongodump -u admin -p --archive | gzip > backup_$DATE.gz

# Schedule with cron
0 2 * * * /path/to/backup.sh
```

### Recovery

```bash
# Restore from backup
gunzip -c backup_20240115_020000.gz | docker-compose exec -T mongodb mongorestore --archive
```

For more detailed troubleshooting, check the application logs and refer to the individual component documentation.