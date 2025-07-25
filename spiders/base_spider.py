import scrapy
from abc import ABC, abstractmethod
from datetime import datetime
from urllib.parse import urljoin
from spiders.items import ListingItem


class BaseRealEstateSpider(scrapy.Spider, ABC):
    """Base spider class for real estate scraping."""
    
    name = None
    allowed_domains = []
    start_urls = []
    
    # Site-specific settings
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scraped_count = 0
        self.failed_count = 0
    
    @abstractmethod
    def parse_listing_urls(self, response):
        """Extract listing URLs from search/category pages."""
        pass
    
    @abstractmethod
    def parse_listing(self, response):
        """Parse individual listing page."""
        pass
    
    def start_requests(self):
        """Generate initial requests."""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'dont_cache': True}
            )
    
    def parse(self, response):
        """Default parse method to extract listing URLs."""
        listing_urls = self.parse_listing_urls(response)
        
        for url in listing_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_listing,
                meta={'dont_cache': True}
            )
        
        # Handle pagination
        next_page = self.get_next_page_url(response)
        if next_page:
            yield scrapy.Request(
                url=next_page,
                callback=self.parse,
                meta={'dont_cache': True}
            )
    
    def get_next_page_url(self, response):
        """Extract next page URL for pagination."""
        # Override in subclasses for site-specific pagination
        return None
    
    def create_listing_item(self, response, **kwargs):
        """Create a ListingItem with common fields populated."""
        item = ListingItem()
        
        # Set common fields
        item['source_site'] = self.name
        item['source_url'] = response.url
        item['scraped_at'] = datetime.utcnow()
        
        # Update with provided kwargs
        for key, value in kwargs.items():
            if key in item.fields:
                item[key] = value
        
        return item
    
    def extract_text(self, response, xpath, default=None):
        """Extract text using XPath with error handling."""
        try:
            result = response.xpath(xpath).get()
            return result.strip() if result else default
        except Exception as e:
            self.logger.warning(f"Error extracting text with xpath '{xpath}': {e}")
            return default
    
    def extract_text_list(self, response, xpath):
        """Extract list of texts using XPath."""
        try:
            results = response.xpath(xpath).getall()
            return [text.strip() for text in results if text.strip()]
        except Exception as e:
            self.logger.warning(f"Error extracting text list with xpath '{xpath}': {e}")
            return []
    
    def normalize_url(self, url, response):
        """Normalize relative URLs to absolute."""
        return urljoin(response.url, url) if url else None
    
    def log_success(self, listing_id):
        """Log successful item processing."""
        self.scraped_count += 1
        self.logger.info(f"Successfully scraped listing: {listing_id} (Total: {self.scraped_count})")
    
    def log_failure(self, listing_id, error):
        """Log failed item processing."""
        self.failed_count += 1
        self.logger.error(f"Failed to scrape listing: {listing_id} - {error} (Failed: {self.failed_count})")
    
    def parse_price(self, price_text):
        """Parse price from text with various formats."""
        if not price_text:
            return None
        
        import re
        
        # Remove common currency symbols and text
        cleaned = re.sub(r'[€$£¥]|EUR|USD|GBP|JPY', '', price_text)
        cleaned = re.sub(r'[,\s]+', '', cleaned)
        
        # Extract numeric value
        match = re.search(r'(\d+\.?\d*)', cleaned)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def parse_area(self, area_text):
        """Parse area from text with various formats."""
        if not area_text:
            return None
        
        import re
        
        # Extract numeric value before m² or similar
        match = re.search(r'(\d+\.?\d*)\s*m[²2]?', area_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def closed(self, reason):
        """Called when spider closes."""
        self.logger.info(
            f"Spider closed: {reason}. "
            f"Scraped: {self.scraped_count}, Failed: {self.failed_count}"
        )