# Archive Directory

This directory contains old files that have been moved from the project root to keep the main directory clean.

## Structure

### `old-tests/`
Contains legacy test files that have been superseded by the formal test suite in `/tests/`:
- `test_city24_simple.py` - Early City24 spider tests
- `test_pp_simple.py` - Early PP.lv spider tests  
- `test_simple_spider.py` - Basic spider functionality tests
- `test_ss_category.py` - SS.com category page tests
- `test_ss_scrapy.py` - SS.com Scrapy integration tests
- `test_ss_spider_extraction.py` - SS.com data extraction tests

### `debug-files/`
Contains development and debugging scripts used during development:
- `debug_listing_page.py` - Individual listing page analysis
- `debug_ss_html.py` - SS.com HTML structure analysis
- `dev.py` - Development runner script
- `dev-simple.py` - Simplified development script
- `improved_ss_scraper.py` - Early SS spider improvements

## Current Testing

The main test suite is now located in `/tests/` with:
- `test_ss_spider.py` - Comprehensive SS spider tests
- `test_models.py` - Pydantic model validation tests  
- `test_normalization.py` - Data normalization tests
- `conftest.py` - Test configuration and fixtures

## Utility Tests

Connection and system tests are located in `/utils/`:
- `test_connection.py` - MongoDB connectivity tests
- `test_celery_worker.py` - Celery worker connectivity tests
- `test_celery_beat.py` - Celery Beat scheduler tests

These files are kept in the archive for reference but are no longer actively used.