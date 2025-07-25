from celery import Celery
from config.settings import settings

# Create Celery app
celery_app = Celery(
    'proscrape',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['tasks.scraping_tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'tasks.scraping_tasks.scrape_ss_com': {'queue': 'scraping'},
        'tasks.scraping_tasks.scrape_city24': {'queue': 'scraping'},
        'tasks.scraping_tasks.scrape_pp_lv': {'queue': 'scraping'},
        'tasks.scraping_tasks.scrape_all_sites': {'queue': 'scraping'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Task retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'scrape-ss-com-daily': {
            'task': 'tasks.scraping_tasks.scrape_ss_com',
            'schedule': 24 * 60 * 60.0,  # Every 24 hours
        },
        'scrape-city24-daily': {
            'task': 'tasks.scraping_tasks.scrape_city24',
            'schedule': 24 * 60 * 60.0,  # Every 24 hours
        },
        'scrape-pp-lv-daily': {
            'task': 'tasks.scraping_tasks.scrape_pp_lv',
            'schedule': 24 * 60 * 60.0,  # Every 24 hours
        },
        'scrape-all-sites-twice-daily': {
            'task': 'tasks.scraping_tasks.scrape_all_sites',
            'schedule': 12 * 60 * 60.0,  # Every 12 hours
        },
    },
)