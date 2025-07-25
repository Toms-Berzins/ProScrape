import subprocess
import logging
from datetime import datetime
from celery import Task
from tasks.celery_app import celery_app
from config.settings import settings

logger = logging.getLogger(__name__)


class ScrapingTask(Task):
    """Base class for scraping tasks with error handling."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed: {exc}")
        # You can add notification logic here (email, Slack, etc.)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {task_id} completed successfully")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(f"Task {task_id} retrying due to: {exc}")


@celery_app.task(base=ScrapingTask, bind=True)
def scrape_ss_com(self):
    """Scrape ss.com real estate listings."""
    try:
        if not settings.ss_com_enabled:
            logger.info("SS.com scraping is disabled")
            return {"status": "skipped", "reason": "disabled"}
        
        logger.info("Starting SS.com scraping task")
        
        # Run Scrapy spider
        cmd = ["scrapy", "crawl", "ss_spider"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logger.info("SS.com scraping completed successfully")
            return {
                "status": "success",
                "site": "ss.com",
                "completed_at": datetime.utcnow().isoformat(),
                "stdout": result.stdout[-1000:],  # Last 1000 chars
            }
        else:
            logger.error(f"SS.com scraping failed: {result.stderr}")
            raise Exception(f"Scrapy command failed: {result.stderr}")
    
    except subprocess.TimeoutExpired:
        logger.error("SS.com scraping timed out")
        raise Exception("Scraping task timed out")
    
    except Exception as exc:
        logger.error(f"SS.com scraping error: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(base=ScrapingTask, bind=True)
def scrape_city24(self):
    """Scrape city24.lv real estate listings."""
    try:
        if not settings.city24_enabled:
            logger.info("City24.lv scraping is disabled")
            return {"status": "skipped", "reason": "disabled"}
        
        logger.info("Starting City24.lv scraping task")
        
        # Run Scrapy spider
        cmd = ["scrapy", "crawl", "city24_spider"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logger.info("City24.lv scraping completed successfully")
            return {
                "status": "success",
                "site": "city24.lv",
                "completed_at": datetime.utcnow().isoformat(),
                "stdout": result.stdout[-1000:],
            }
        else:
            logger.error(f"City24.lv scraping failed: {result.stderr}")
            raise Exception(f"Scrapy command failed: {result.stderr}")
    
    except subprocess.TimeoutExpired:
        logger.error("City24.lv scraping timed out")
        raise Exception("Scraping task timed out")
    
    except Exception as exc:
        logger.error(f"City24.lv scraping error: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(base=ScrapingTask, bind=True)
def scrape_pp_lv(self):
    """Scrape pp.lv real estate listings."""
    try:
        if not settings.pp_lv_enabled:
            logger.info("PP.lv scraping is disabled")
            return {"status": "skipped", "reason": "disabled"}
        
        logger.info("Starting PP.lv scraping task")
        
        # Run Scrapy spider
        cmd = ["scrapy", "crawl", "pp_spider"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logger.info("PP.lv scraping completed successfully")
            return {
                "status": "success",
                "site": "pp.lv",
                "completed_at": datetime.utcnow().isoformat(),
                "stdout": result.stdout[-1000:],
            }
        else:
            logger.error(f"PP.lv scraping failed: {result.stderr}")
            raise Exception(f"Scrapy command failed: {result.stderr}")
    
    except subprocess.TimeoutExpired:
        logger.error("PP.lv scraping timed out")
        raise Exception("Scraping task timed out")
    
    except Exception as exc:
        logger.error(f"PP.lv scraping error: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(base=ScrapingTask, bind=True)
def scrape_all_sites(self):
    """Scrape all enabled sites in parallel."""
    try:
        logger.info("Starting parallel scraping of all sites")
        
        # Create subtasks for each enabled site
        tasks = []
        
        if settings.ss_com_enabled:
            tasks.append(scrape_ss_com.delay())
        
        if settings.city24_enabled:
            tasks.append(scrape_city24.delay())
        
        if settings.pp_lv_enabled:
            tasks.append(scrape_pp_lv.delay())
        
        if not tasks:
            logger.warning("No sites enabled for scraping")
            return {"status": "skipped", "reason": "no_sites_enabled"}
        
        # Wait for all tasks to complete
        results = []
        for task in tasks:
            try:
                result = task.get(timeout=7200)  # 2 hours total timeout
                results.append(result)
            except Exception as e:
                logger.error(f"Subtask failed: {e}")
                results.append({"status": "failed", "error": str(e)})
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        
        logger.info(f"Parallel scraping completed: {success_count}/{len(results)} successful")
        
        return {
            "status": "completed",
            "total_tasks": len(results),
            "successful_tasks": success_count,
            "completed_at": datetime.utcnow().isoformat(),
            "results": results
        }
    
    except Exception as exc:
        logger.error(f"Parallel scraping error: {exc}")
        raise self.retry(exc=exc, countdown=300, max_retries=2)  # 5 min delay, 2 retries


@celery_app.task
def cleanup_old_listings():
    """Clean up old listing data (optional maintenance task)."""
    try:
        from utils.database import db
        from datetime import timedelta
        
        db.connect()
        collection = db.get_collection("listings")
        
        # Remove listings older than 30 days that haven't been updated
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        result = collection.delete_many({
            "scraped_at": {"$lt": cutoff_date},
            "updated_date": {"$lt": cutoff_date}
        })
        
        logger.info(f"Cleaned up {result.deleted_count} old listings")
        
        return {
            "status": "success",
            "deleted_count": result.deleted_count,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    except Exception as exc:
        logger.error(f"Cleanup task error: {exc}")
        raise
    
    finally:
        if 'db' in locals():
            db.disconnect()


# Manual task triggers
@celery_app.task
def trigger_manual_scrape(site: str):
    """Manually trigger scraping for a specific site."""
    site_tasks = {
        'ss.com': scrape_ss_com,
        'city24.lv': scrape_city24,
        'pp.lv': scrape_pp_lv,
        'all': scrape_all_sites
    }
    
    if site not in site_tasks:
        raise ValueError(f"Unknown site: {site}")
    
    logger.info(f"Manually triggering scrape for: {site}")
    return site_tasks[site].delay()