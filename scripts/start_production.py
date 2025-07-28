#!/usr/bin/env python3
"""
Production startup script for ProScrape.
Sets up environment and starts services for large-scale scraping.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.production_settings import production_settings, setup_production_logging

logger = logging.getLogger(__name__)


def check_prerequisites():
    """Check if all prerequisites are met for production deployment."""
    logger.info("Checking production prerequisites...")
    
    checks = []
    
    # Check MongoDB connection
    try:
        from utils.database import DatabaseManager
        db = DatabaseManager()
        db.connect()
        db.disconnect()
        checks.append(("MongoDB Connection", True, "Connected successfully"))
    except Exception as e:
        checks.append(("MongoDB Connection", False, f"Failed: {e}"))
    
    # Check Redis connection
    try:
        import redis
        r = redis.from_url(production_settings.redis_url)
        r.ping()
        checks.append(("Redis Connection", True, "Connected successfully"))
    except Exception as e:
        checks.append(("Redis Connection", False, f"Failed: {e}"))
    
    # Check log directory
    try:
        production_settings.log_dir.mkdir(parents=True, exist_ok=True)
        test_file = production_settings.log_dir / "test.tmp"
        test_file.write_text("test")
        test_file.unlink()
        checks.append(("Log Directory", True, f"Writable: {production_settings.log_dir}"))
    except Exception as e:
        checks.append(("Log Directory", False, f"Failed: {e}"))
    
    # Check Docker availability
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append(("Docker", True, result.stdout.strip()))
        else:
            checks.append(("Docker", False, "Docker not available"))
    except Exception as e:
        checks.append(("Docker", False, f"Failed: {e}"))
    
    # Check Docker Compose availability
    try:
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append(("Docker Compose", True, result.stdout.strip()))
        else:
            checks.append(("Docker Compose", False, "Docker Compose not available"))
    except Exception as e:
        checks.append(("Docker Compose", False, f"Failed: {e}"))
    
    # Print results
    logger.info("Prerequisites check results:")
    all_passed = True
    for check_name, passed, message in checks:
        status = "PASS" if passed else "FAIL"
        logger.info(f"  {check_name}: {status} - {message}")
        if not passed:
            all_passed = False
    
    return all_passed


def setup_environment():
    """Set up production environment."""
    logger.info("Setting up production environment...")
    
    # Create necessary directories
    directories = [
        production_settings.log_dir,
        project_root / "data",
        project_root / "tmp",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # Set environment variables
    env_vars = {
        'PRODUCTION': 'true',
        'LOG_LEVEL': production_settings.log_level,
        'MONGODB_URL': production_settings.mongodb_url,
        'REDIS_URL': production_settings.redis_url,
        'SS_COM_ENABLED': 'true',
        'CITY24_ENABLED': 'false',
        'PP_LV_ENABLED': 'false',
        'CELERY_CONCURRENCY': str(production_settings.celery_concurrency),
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"Set environment variable: {key}={value}")


def start_production_services():
    """Start production services using Docker Compose."""
    logger.info("Starting production services...")
    
    compose_file = project_root / "docker-compose.production.yml"
    
    if not compose_file.exists():
        logger.error(f"Production compose file not found: {compose_file}")
        return False
    
    try:
        # Build and start services
        logger.info("Building and starting Docker services...")
        
        cmd = [
            'docker-compose',
            '-f', str(compose_file),
            'up', '-d',
            '--build',
            '--scale', 'celery_worker=2'  # Start 2 worker instances
        ]
        
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Services started successfully")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"Failed to start services: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error starting services: {e}")
        return False


def wait_for_services():
    """Wait for services to be ready."""
    logger.info("Waiting for services to be ready...")
    
    services = [
        ("Redis", "redis://localhost:6379", "ping"),
        ("API", "http://localhost:8000/health", "GET"),
        ("Flower", "http://localhost:5555", "GET"),
    ]
    
    max_wait = 120  # 2 minutes
    start_time = time.time()
    
    for service_name, endpoint, check_type in services:
        logger.info(f"Checking {service_name}...")
        service_ready = False
        
        while not service_ready and (time.time() - start_time) < max_wait:
            try:
                if check_type == "ping":
                    import redis
                    r = redis.from_url(endpoint)
                    r.ping()
                    service_ready = True
                elif check_type == "GET":
                    import requests
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        service_ready = True
                        
            except Exception:
                time.sleep(5)
        
        if service_ready:
            logger.info(f"{service_name} is ready")
        else:
            logger.warning(f"{service_name} not ready after {max_wait}s")
    
    logger.info("Service readiness check completed")


def trigger_initial_scrape():
    """Trigger initial SS.com scraping."""
    logger.info("Triggering initial SS.com scraping...")
    
    try:
        from tasks.scraping_tasks import scrape_ss_com
        
        # Trigger the scraping task
        task = scrape_ss_com.delay()
        logger.info(f"Scraping task triggered with ID: {task.id}")
        
        return task.id
        
    except Exception as e:
        logger.error(f"Failed to trigger scraping: {e}")
        return None


def monitor_scraping_progress(task_id):
    """Monitor the progress of the scraping task."""
    if not task_id:
        logger.warning("No task ID provided for monitoring")
        return
    
    logger.info(f"Monitoring scraping task: {task_id}")
    
    try:
        from tasks.celery_app import celery_app
        
        task = celery_app.AsyncResult(task_id)
        
        while not task.ready():
            logger.info(f"Task status: {task.status}")
            time.sleep(30)  # Check every 30 seconds
        
        result = task.result
        if task.successful():
            logger.info(f"Scraping completed successfully: {result}")
        else:
            logger.error(f"Scraping failed: {result}")
            
    except Exception as e:
        logger.error(f"Error monitoring task: {e}")


def show_service_status():
    """Show the status of all services."""
    logger.info("Production service status:")
    
    try:
        cmd = ['docker-compose', '-f', 'docker-compose.production.yml', 'ps']
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Service status:")
            for line in result.stdout.strip().split('\n'):
                logger.info(f"  {line}")
        else:
            logger.error(f"Failed to get service status: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error checking service status: {e}")
    
    # Show access URLs
    logger.info("Service URLs:")
    logger.info("  API: http://localhost:8000")
    logger.info("  API Documentation: http://localhost:8000/docs")
    logger.info("  Flower (Celery Monitoring): http://localhost:5555")
    logger.info("  cAdvisor (System Monitoring): http://localhost:8080")


def main():
    """Main production startup function."""
    print("=== ProScrape Production Deployment ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project Root: {project_root}")
    print("=" * 50)
    
    # Setup logging
    setup_production_logging()
    logger.info("Starting ProScrape production deployment")
    
    # Check prerequisites
    if not check_prerequisites():
        logger.error("Prerequisites check failed. Please fix issues before continuing.")
        return False
    
    # Setup environment
    setup_environment()
    
    # Start services
    if not start_production_services():
        logger.error("Failed to start services")
        return False
    
    # Wait for services
    wait_for_services()
    
    # Show status
    show_service_status()
    
    # Trigger initial scrape
    logger.info("Production deployment completed successfully!")
    logger.info("You can now:")
    logger.info("1. Monitor services at http://localhost:5555 (Flower)")
    logger.info("2. Access API at http://localhost:8000")
    logger.info("3. Trigger manual scraping via API or Flower")
    
    # Ask if user wants to trigger immediate scraping
    response = input("\nWould you like to trigger immediate SS.com scraping? (y/N): ")
    if response.lower() in ['y', 'yes']:
        task_id = trigger_initial_scrape()
        if task_id:
            response = input(f"Monitor task progress? (y/N): ")
            if response.lower() in ['y', 'yes']:
                monitor_scraping_progress(task_id)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)