import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_NAME = 'proscrape'

SPIDER_MODULES = ['spiders']
NEWSPIDER_MODULE = 'spiders'

# MongoDB settings from environment
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'proscrape')

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure delays for requests
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = 0.5

# Enable AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 3
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Configure user agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Configure pipelines
ITEM_PIPELINES = {
    'spiders.pipelines.ValidationPipeline': 300,
    'spiders.pipelines.NormalizationPipeline': 350,
    'spiders.pipelines.DuplicatesPipeline': 400,
    'spiders.pipelines.MongoPipeline': 500,
}

# Configure downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'spiders.middlewares.EnhancedUserAgentMiddleware': 400,
    'spiders.middlewares.EnhancedProxyMiddleware': 410,
    'spiders.middlewares.EnhancedRetryMiddleware': 420,
    'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler': 585,
}

# Download handlers for Playwright
DOWNLOAD_HANDLERS = {
    'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
    'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
}

# Playwright settings
PLAYWRIGHT_BROWSER_TYPE = 'chromium'
PLAYWRIGHT_LAUNCH_OPTIONS = {
    'headless': True,
    'timeout': 30000,
    'args': [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
    ]
}

# Additional Playwright settings
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000
PLAYWRIGHT_PAGE_GOTO_KWARGS = {
    'wait_until': 'networkidle',
    'timeout': 30000,
}

# Enable asyncio reactor for Playwright
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# Request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Cookies
COOKIES_ENABLED = True

# Configure logging
LOG_LEVEL = 'INFO'

# Disable Telnet Console
TELNETCONSOLE_ENABLED = False

# Cache settings
HTTPCACHE_ENABLED = False