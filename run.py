#!/usr/bin/env python3
"""
ProScrape - Latvian Real Estate Scraper
Main entry point for running different components of the application.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler()
        ]
    )


def run_api():
    """Run the FastAPI application."""
    import uvicorn
    from api.main import app
    
    print(f"Starting ProScrape API on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )


def run_celery_worker():
    """Run Celery worker."""
    import subprocess
    
    print("Starting Celery worker...")
    cmd = ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info"]
    subprocess.run(cmd)


def run_celery_beat():
    """Run Celery beat scheduler."""
    import subprocess
    
    print("Starting Celery beat scheduler...")
    cmd = ["celery", "-A", "tasks.celery_app", "beat", "--loglevel=info"]
    subprocess.run(cmd)


def run_celery_flower():
    """Run Celery flower monitoring."""
    import subprocess
    
    print("Starting Celery flower on port 5555...")
    cmd = ["celery", "-A", "tasks.celery_app", "flower", "--port=5555"]
    subprocess.run(cmd)


def run_spider(spider_name):
    """Run a specific Scrapy spider."""
    import subprocess
    
    valid_spiders = ["ss_spider", "city24_spider", "pp_spider"]
    
    if spider_name not in valid_spiders:
        print(f"Invalid spider name. Valid options: {', '.join(valid_spiders)}")
        return
    
    print(f"Running {spider_name}...")
    cmd = ["scrapy", "crawl", spider_name]
    subprocess.run(cmd)


def trigger_scrape(site):
    """Trigger manual scraping via Celery."""
    from tasks.scraping_tasks import trigger_manual_scrape
    
    print(f"Triggering manual scrape for: {site}")
    task = trigger_manual_scrape.delay(site)
    print(f"Task ID: {task.id}")
    print("Check Celery flower (http://localhost:5555) for task status")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ProScrape - Latvian Real Estate Scraper")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # API command
    subparsers.add_parser("api", help="Run FastAPI application")
    
    # Celery commands
    subparsers.add_parser("worker", help="Run Celery worker")
    subparsers.add_parser("beat", help="Run Celery beat scheduler")
    subparsers.add_parser("flower", help="Run Celery flower monitoring")
    
    # Spider commands
    spider_parser = subparsers.add_parser("spider", help="Run Scrapy spider")
    spider_parser.add_argument("name", choices=["ss_spider", "city24_spider", "pp_spider"], 
                              help="Spider name to run")
    
    # Manual scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Trigger manual scraping")
    scrape_parser.add_argument("site", choices=["ss.com", "city24.lv", "pp.lv", "all"],
                              help="Site to scrape")
    
    # Development command
    subparsers.add_parser("dev", help="Run development environment (API + worker)")
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    if args.command == "api":
        run_api()
    elif args.command == "worker":
        run_celery_worker()
    elif args.command == "beat":
        run_celery_beat()
    elif args.command == "flower":
        run_celery_flower()
    elif args.command == "spider":
        run_spider(args.name)
    elif args.command == "scrape":
        trigger_scrape(args.site)
    elif args.command == "dev":
        print("Development mode: Starting API and Celery worker...")
        print("For full development, also run:")
        print("  python run.py beat    # In another terminal")
        print("  python run.py flower  # In another terminal")
        import multiprocessing
        
        # Start API and worker in parallel
        api_process = multiprocessing.Process(target=run_api)
        worker_process = multiprocessing.Process(target=run_celery_worker)
        
        api_process.start()
        worker_process.start()
        
        try:
            api_process.join()
            worker_process.join()
        except KeyboardInterrupt:
            print("\nShutting down...")
            api_process.terminate()
            worker_process.terminate()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()