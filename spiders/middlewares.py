import random
import time
import logging
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.downloadermiddlewares.httpproxy import HttpProxyMiddleware
from scrapy.exceptions import IgnoreRequest, NotConfigured
from scrapy.http import HtmlResponse
from twisted.internet.error import TimeoutError, DNSLookupError, ConnectionRefusedError
from fake_useragent import UserAgent
from utils.proxies import proxy_rotator, user_agent_rotator

logger = logging.getLogger(__name__)


class EnhancedUserAgentMiddleware(UserAgentMiddleware):
    """Enhanced middleware to rotate user agents with better error handling."""
    
    def __init__(self, user_agent=''):
        self.user_agent = user_agent
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.warning(f"Failed to initialize UserAgent: {e}")
            self.ua = None
    
    def process_request(self, request, spider):
        try:
            # Try to get user agent from rotator first
            ua = user_agent_rotator.get_user_agent()
            if not ua and self.ua:
                ua = self.ua.random
            elif not ua:
                ua = user_agent_rotator.get_random_user_agent()
            
            request.headers['User-Agent'] = ua
            spider.logger.debug(f'Using User-Agent: {ua}')
            
        except Exception as e:
            logger.warning(f"Error setting User-Agent: {e}")
            # Fallback to default
            request.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        return None


class EnhancedProxyMiddleware:
    """Enhanced middleware to rotate proxies with health monitoring."""
    
    def __init__(self, enabled=False):
        self.enabled = enabled
        if not self.enabled:
            raise NotConfigured('Proxy middleware disabled')
    
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        enabled = settings.getbool('ROTATE_PROXIES', False)
        return cls(enabled=enabled)
    
    def process_request(self, request, spider):
        if not self.enabled or not proxy_rotator.has_working_proxies():
            return None
        
        try:
            proxy = proxy_rotator.get_proxy()
            if proxy:
                request.meta['proxy'] = proxy
                request.meta['proxy_used'] = proxy
                spider.logger.debug(f'Using proxy: {proxy}')
            
        except Exception as e:
            spider.logger.error(f'Error assigning proxy: {e}')
        
        return None
    
    def process_response(self, request, response, spider):
        # Mark proxy as successful if response is good
        proxy = request.meta.get('proxy_used')
        if proxy and response.status < 400:
            proxy_rotator.update_proxy_stats(proxy, success=True)
        
        return response
    
    def process_exception(self, request, exception, spider):
        # Mark proxy as failed on exception
        proxy = request.meta.get('proxy_used')
        if proxy:
            proxy_rotator.mark_proxy_failed(proxy)
            spider.logger.warning(f'Proxy {proxy} failed with exception: {exception}')
        
        return None


class EnhancedRetryMiddleware:
    """Enhanced retry middleware with exponential backoff and dead letter queue."""
    
    def __init__(self, max_retry_times=3, retry_http_codes=None, retry_exceptions=None):
        self.max_retry_times = max_retry_times
        self.retry_http_codes = retry_http_codes or [500, 502, 503, 504, 408, 429, 523, 524]
        self.retry_exceptions = retry_exceptions or [
            TimeoutError, DNSLookupError, ConnectionRefusedError
        ]
        self.dead_letter_queue = []
    
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(
            max_retry_times=settings.getint('RETRY_TIMES', 3),
            retry_http_codes=settings.getlist('RETRY_HTTP_CODES', [500, 502, 503, 504, 408, 429, 523, 524])
        )
    
    def process_response(self, request, response, spider):
        if response.status in self.retry_http_codes:
            return self._retry_request(request, response, spider, f'HTTP {response.status}')
        
        return response
    
    def process_exception(self, request, exception, spider):
        if any(isinstance(exception, exc_type) for exc_type in self.retry_exceptions):
            return self._retry_request(request, None, spider, f'Exception: {type(exception).__name__}')
        
        return None
    
    def _retry_request(self, request, response, spider, reason):
        """Handle request retry logic with exponential backoff."""
        retry_times = request.meta.get('retry_times', 0) + 1
        
        if retry_times <= self.max_retry_times:
            # Exponential backoff with jitter
            base_delay = 2 ** retry_times
            jitter = random.uniform(0.1, 0.5)
            delay = base_delay + jitter
            
            spider.logger.warning(
                f'Retrying {request.url} (attempt {retry_times}/{self.max_retry_times}) '
                f'after {delay:.2f}s delay due to {reason}'
            )
            
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retry_times
            retryreq.meta['retry_reason'] = reason
            retryreq.dont_filter = True
            
            # Add delay
            time.sleep(min(delay, 30))  # Cap at 30 seconds
            
            return retryreq
        else:
            # Add to dead letter queue
            self._add_to_dead_letter_queue(request, reason, spider)
            spider.logger.error(
                f'Giving up on {request.url} after {retry_times} retries. Reason: {reason}'
            )
            
            # Return empty response to continue processing
            return HtmlResponse(url=request.url, status=500, body=b'')
    
    def _add_to_dead_letter_queue(self, request, reason, spider):
        """Add failed request to dead letter queue for later analysis."""
        dead_item = {
            'url': request.url,
            'method': request.method,
            'headers': dict(request.headers),
            'meta': {k: v for k, v in request.meta.items() if isinstance(v, (str, int, float, bool))},
            'reason': reason,
            'timestamp': time.time(),
            'spider': spider.name
        }
        
        self.dead_letter_queue.append(dead_item)
        spider.logger.info(f'Added to dead letter queue: {request.url}')
        
        # Log dead letter queue statistics
        if len(self.dead_letter_queue) % 10 == 0:
            spider.logger.warning(f'Dead letter queue size: {len(self.dead_letter_queue)}')
    
    def get_dead_letter_stats(self):
        """Get statistics about failed requests."""
        if not self.dead_letter_queue:
            return {'total': 0, 'by_reason': {}, 'by_spider': {}}
        
        by_reason = {}
        by_spider = {}
        
        for item in self.dead_letter_queue:
            reason = item['reason']
            spider = item['spider']
            
            by_reason[reason] = by_reason.get(reason, 0) + 1
            by_spider[spider] = by_spider.get(spider, 0) + 1
        
        return {
            'total': len(self.dead_letter_queue),
            'by_reason': by_reason,
            'by_spider': by_spider,
            'items': self.dead_letter_queue[-10:]  # Last 10 items
        }


# Global retry middleware instance for accessing dead letter queue
retry_middleware_instance = None