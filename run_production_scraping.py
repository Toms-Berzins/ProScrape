#!/usr/bin/env python3
"""
Direct production scraping script without Celery dependencies.
Runs the SS spider directly for immediate production deployment.
"""

import os
import sys
import time
import logging
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from spiders.ss_spider import SSSpider
from utils.database import Database

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('production_scraping.log')
    ]
)

logger = logging.getLogger(__name__)


def check_database_connection():
    """Check if database is accessible."""
    try:
        db = Database()
        db.connect()
        collection = db.get_collection('listings')
        initial_count = collection.count_documents({})
        db.disconnect()
        logger.info(f"Database connection successful. Current listings: {initial_count}")
        return initial_count
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def run_production_scraping():
    """Run SS spider for production scraping."""
    
    print("=== ProScrape Production Scraping ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)
    
    # Check database connection
    logger.info("Checking database connection...")
    initial_count = check_database_connection()
    if initial_count is None:
        logger.error("Cannot proceed without database connection")
        return False
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Override with production settings
    production_settings = {
        'LOG_LEVEL': 'INFO',
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'AUTOTHROTTLE_DEBUG': True,
        'COOKIES_ENABLED': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'DOWNLOAD_TIMEOUT': 30,
        'TELNETCONSOLE_ENABLED': False,
        
        # Pipeline configuration
        'ITEM_PIPELINES': {
            'spiders.pipelines.ValidationPipeline': 300,
            'spiders.pipelines.NormalizationPipeline': 350,
            'spiders.pipelines.DuplicatesPipeline': 400,
            'spiders.pipelines.MongoPipeline': 500,
        },
        
        # Middleware configuration
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'spiders.middlewares.EnhancedUserAgentMiddleware': 400,
            'spiders.middlewares.EnhancedRetryMiddleware': 420,
        },
    }
    
    # Update settings
    settings.update(production_settings)
    
    # Configure logging to file
    log_file = f"production_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    settings.set('LOG_FILE', log_file)
    
    logger.info("Starting production scraping with settings:")
    for key, value in production_settings.items():
        logger.info(f"  {key}: {value}")
    
    # Start scraping
    start_time = time.time()
    logger.info("Initializing Scrapy crawler...")
    
    try:
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Add spider
        process.crawl(SSSpider)
        
        logger.info("Starting SS.com production scraping...")
        logger.info("This may take 30-60 minutes to complete...")
        
        # Start the crawling process
        process.start()
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return False
    
    # Calculate execution time
    end_time = time.time()
    execution_time = end_time - start_time
    
    logger.info(f"Scraping completed in {execution_time:.2f} seconds")
    
    # Check results
    try:
        db = Database()
        db.connect()
        collection = db.get_collection('listings')
        final_count = collection.count_documents({})
        new_listings = final_count - initial_count
        db.disconnect()
        
        logger.info(f"Scraping results:")
        logger.info(f"  Initial listings: {initial_count}")
        logger.info(f"  Final listings: {final_count}")
        logger.info(f"  New listings scraped: {new_listings}")
        
        print("\n" + "=" * 50)
        print("PRODUCTION SCRAPING COMPLETED")
        print("=" * 50)
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"New listings scraped: {new_listings}")
        print(f"Total listings in database: {final_count}")
        print(f"Log file: {log_file}")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking results: {e}")
        return False


def monitor_scraping_progress():
    """Monitor scraping progress in real-time."""
    
    logger.info("Starting scraping progress monitor...")
    initial_count = check_database_connection()
    
    if initial_count is None:
        return
    
    start_time = time.time()
    last_count = initial_count
    
    try:
        while True:
            time.sleep(30)  # Check every 30 seconds
            
            try:
                db = Database()
                db.connect()
                collection = db.get_collection('listings')
                current_count = collection.count_documents({})
                db.disconnect()
                
                elapsed_time = time.time() - start_time
                new_listings = current_count - initial_count
                rate = new_listings / (elapsed_time / 60) if elapsed_time > 0 else 0
                
                if current_count != last_count:
                    logger.info(f"Progress: {new_listings} new listings ({rate:.1f}/min) - Total: {current_count}")
                    last_count = current_count
                
            except Exception as e:
                logger.warning(f"Error checking progress: {e}")
                
    except KeyboardInterrupt:
        logger.info("Progress monitoring stopped by user")


if __name__ == "__main__":
    try:
        success = run_production_scraping()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Production scraping failed: {e}")
        sys.exit(1)