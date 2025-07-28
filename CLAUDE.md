# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProScrape is a web scraping pipeline for Latvian real estate websites. The project is designed to scrape three specific sites:
- ss.com/en/real-estate/ (static HTML, requires standard HTTP scraping)
- city24.lv/en/ (JavaScript-heavy, requires dynamic scraping)
- pp.lv/lv/landing/nekustamais-ipasums (JavaScript-heavy, requires dynamic scraping)

## Technology Stack

- **Scraping**: Scrapy framework with scrapy-playwright for dynamic content
- **Static scraping**: BeautifulSoup/XPath for HTML parsing
- **Dynamic scraping**: Playwright for JavaScript-rendered pages
- **Data storage**: MongoDB with Motor (async driver)
- **API**: FastAPI with Pydantic for data validation
- **Task queue**: Celery with RabbitMQ/Redis
- **Task scheduling**: Celery Beat

## Project Structure (Implemented)

The project has been successfully implemented with the following structure:
```
ProScrape/
├── spiders/
│   ├── __init__.py
│   ├── base_spider.py       # Base spider class with common functionality
│   ├── ss_spider.py         # Static HTML scraper (implemented)
│   ├── city24_spider.py     # Dynamic JS scraper (implemented)
│   ├── pp_spider.py         # Dynamic JS scraper (implemented)
│   ├── items.py             # Scrapy item definitions
│   ├── middlewares.py       # Custom middlewares for UA/proxy rotation
│   ├── pipelines.py         # Data validation and MongoDB storage
│   └── settings.py          # Scrapy configuration
├── models/
│   ├── __init__.py
│   └── listing.py           # Pydantic models (Pydantic v2 compatible)
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py        # Celery configuration
│   └── scraping_tasks.py    # Celery task definitions
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI application with endpoints
├── utils/
│   ├── __init__.py
│   ├── database.py          # MongoDB connection utilities
│   ├── proxies.py           # Proxy and UA rotation logic
│   ├── normalization.py     # Data normalization utilities
│   └── logging_config.py    # Structured logging configuration
├── config/
│   ├── __init__.py
│   └── settings.py          # Environment-based configuration
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration
│   ├── test_models.py       # Model unit tests
│   └── test_normalization.py # Normalization tests
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker service orchestration
├── Dockerfile              # Container definition
├── run.py                  # Main entry point script
├── test_connection.py      # Database connection tester
├── test_celery_worker.py   # Celery worker connectivity tester
├── test_celery_beat.py     # Celery Beat scheduler tester
├── start_redis.bat         # Redis server startup script (Windows)
├── stop_redis.bat          # Redis server stop script (Windows)
├── docker-compose.redis.yml # Production Redis/Celery deployment
├── .env                    # Environment configuration
└── DEPLOYMENT.md           # Comprehensive deployment guide
```

## Development Commands

The project is fully implemented and tested. Here are the key commands:

```bash
# Environment setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m playwright install chromium

# Start Redis server
start_redis.bat  # Windows batch script
# OR: docker run -d --name redis-server -p 6379:6379 redis:7-alpine

# Test system connectivity
python test_connection.py       # MongoDB connection
python test_celery_worker.py    # Celery worker connectivity  
python test_celery_beat.py      # Celery Beat scheduler

# Run services (use separate terminals)
python run.py api       # FastAPI server on port 8000
python run.py worker    # Celery worker
python run.py beat      # Celery scheduler
python run.py flower    # Monitoring UI on port 5555

# Run spiders directly
python -m scrapy crawl ss_spider
python -m scrapy crawl city24_spider
python -m scrapy crawl pp_spider

# Run tests
pytest tests/

# Docker deployment (production)
docker-compose -f docker-compose.redis.yml up -d
```

## Current Status

- ✅ **MongoDB**: Connected to Atlas cluster (connection string in .env)
- ✅ **Spiders**: All three spiders implemented and tested with proper selectors
- ✅ **API**: FastAPI running with full CRUD endpoints
- ✅ **Models**: Pydantic v2 compatible with Decimal handling
- ✅ **Tests**: Unit tests for models and normalization
- ✅ **Redis**: Installed and configured with Docker for Celery
- ✅ **Celery**: Worker and Beat scheduler tested and working
- ✅ **Data Normalization**: Integrated into Scrapy pipelines
- ⚠️ **Proxies**: Proxy rotation implemented but no proxies configured

## Key Implementation Guidelines

### Site-Specific Considerations

1. **ss.com**: Use standard HTTP requests with proper User-Agent headers and rate limiting
2. **city24.lv & pp.lv**: Implement Playwright automation to handle JavaScript rendering and cookie consent popups

### Data Schema

All scrapers should extract data into a unified schema with these fields:
- listing_id (unique identifier)
- title
- price (normalized to EUR)
- area
- coordinates
- features
- posted_date
- image_urls

### Anti-Scraping Measures

- Implement proxy rotation for all spiders
- Use randomized request headers
- Add delays between requests
- Handle captchas and honeypot detection
- Use realistic User-Agent strings

### Database Considerations

- Use unique indexes on listing_id to prevent duplicates
- Implement Pydantic models for data validation before MongoDB insertion
- Use Motor for async MongoDB operations in FastAPI

## Next Steps (Priority Order)

### High Priority (COMPLETED)
1. ✅ **Test Scraping Functionality**
   - ✅ Run each spider with limited items to verify selectors
   - ✅ Check data quality and completeness
   - ✅ Monitor for blocking or rate limiting

2. ✅ **Implement Data Normalization**
   - ✅ Integrate `utils/normalization.py` into pipelines
   - ✅ Ensure consistent data format across all spiders
   - ✅ Handle currency conversion and date parsing

3. ✅ **Set up Redis**
   - ✅ Install Redis locally with Docker
   - ✅ Test Celery worker connectivity
   - ✅ Verify task scheduling works with Celery Beat

### Medium Priority (COMPLETED)
4. ✅ **Enhance API Endpoints**
   - ✅ Add filtering by date ranges (date_from, date_to, posted_from, posted_to)
   - ✅ Implement data export endpoints (CSV/JSON with /export/csv and /export/json)
   - ✅ Add websocket support for real-time updates (/ws endpoint with connection manager)

5. ✅ **Configure Proxy Rotation**
   - ✅ Add proxy list to settings (enhanced with health monitoring settings)
   - ✅ Test proxy health checking (background monitoring with statistics)
   - ✅ Implement automatic failover (intelligent proxy selection with success rates)

6. ✅ **Improve Error Handling**
   - ✅ Add retry logic for failed requests (exponential backoff with jitter)
   - ✅ Implement dead letter queue for failed items (comprehensive failure tracking)
   - ✅ Set up alerting for critical failures (email/webhook notifications)

### Low Priority
7. **Create Monitoring Dashboard**
   - Build React/Vue frontend
   - Display scraping statistics
   - Show data quality metrics

8. **Data Quality Validation**
   - Implement price reasonableness checks
   - Validate coordinate boundaries
   - Flag suspicious listings

9. **Automated Testing**
   - Create spider contracts
   - Add integration tests
   - Set up CI/CD pipeline

10. **Production Deployment**
    - Configure Docker Swarm/K8s
    - Set up SSL certificates
    - Implement log aggregation

## Testing and Validation

The system includes comprehensive testing utilities:

### Spider Testing Results
- **SS Spider**: Successfully extracts listings from static HTML
- **City24 Spider**: Fixed 404 issues, now scrapes from main page
- **PP Spider**: Resolved Playwright timeout issues with load strategy

### Integration Testing
- **Data Normalization**: All fields properly normalized across spiders
- **Celery Workers**: Connectivity and task queuing tested
- **Celery Beat**: Scheduler configuration and timing validated
- **Redis**: Docker-based setup working reliably

## Known Issues and Solutions

### Issue: Windows Unicode Encoding
**Solution**: Replace Unicode characters (✓, ❌) with ASCII equivalents in console output

### Issue: City24 Spider 404 Errors
**Solution**: Updated from search endpoints to main page scraping with `/apartment` and `/house` patterns

### Issue: PP Spider Playwright Timeouts
**Solution**: Changed wait strategy from 'networkidle' to 'load' due to continuous JS activity

### Issue: Pydantic v2 Compatibility
**Solution**: 
- Use `field_validator` instead of `validator`
- Use `populate_by_name` instead of `allow_population_by_field_name`
- Convert Decimal to float before MongoDB insertion

### Issue: MongoDB Atlas SSL Certificate Warning
**Solution**: This is a known issue with PyMongo and can be safely ignored in development

## API Endpoints

### Core Endpoints
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /listings` - List listings with pagination and filters (now includes date range filtering)
- `GET /listings/{listing_id}` - Get specific listing
- `GET /listings/search` - Search listings by text
- `GET /stats` - Get database statistics

### Export Endpoints
- `GET /export/csv` - Export listings to CSV format with filtering
- `GET /export/json` - Export listings to JSON format with filtering

### Real-time Updates
- `WebSocket /ws` - WebSocket endpoint for real-time listing updates

### Monitoring Endpoints
- `GET /proxy/stats` - Get proxy rotation statistics and health information
- `GET /monitoring/dead-letter-queue` - Get dead letter queue statistics
- `GET /monitoring/alerts` - Get recent alerts and alert summary
- `POST /monitoring/check-alerts` - Manually trigger alert checking
- `GET /monitoring/health` - Get comprehensive system health information

## Environment Variables

Key variables in `.env`:
- `MONGODB_URL` - MongoDB connection string (Atlas)
- `MONGODB_DATABASE` - Database name
- `REDIS_URL` - Redis connection (for Celery)
- `LOG_LEVEL` - Logging verbosity
- `DOWNLOAD_DELAY` - Delay between requests
- `*_ENABLED` - Enable/disable specific spiders

## Agent and Task Management Guidelines

- Always use agents for specific tasks