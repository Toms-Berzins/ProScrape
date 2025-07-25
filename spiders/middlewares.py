import random
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.downloadermiddlewares.httpproxy import HttpProxyMiddleware
from fake_useragent import UserAgent


class UserAgentMiddleware(UserAgentMiddleware):
    """Middleware to rotate user agents."""
    
    def __init__(self, user_agent=''):
        self.user_agent = user_agent
        self.ua = UserAgent()
        
        # Fallback user agents
        self.user_agent_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
        ]
    
    def process_request(self, request, spider):
        try:
            ua = self.ua.random
        except Exception:
            ua = random.choice(self.user_agent_list)
        
        request.headers['User-Agent'] = ua
        return None


class ProxyMiddleware:
    """Middleware to rotate proxies."""
    
    def __init__(self):
        self.proxies = []
        self.proxy_index = 0
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls()
    
    def process_request(self, request, spider):
        if not self.proxies:
            # Load proxies from settings or configuration
            proxy_list = getattr(spider.settings, 'PROXY_LIST', [])
            if proxy_list:
                self.proxies = proxy_list
            else:
                return None
        
        if self.proxies:
            proxy = self.proxies[self.proxy_index]
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
            
            request.meta['proxy'] = proxy
            spider.logger.debug(f'Using proxy: {proxy}')
        
        return None


class RetryMiddleware:
    """Custom retry middleware with backoff."""
    
    def __init__(self, max_retry_times=3, retry_http_codes=None):
        self.max_retry_times = max_retry_times
        self.retry_http_codes = retry_http_codes or [500, 502, 503, 504, 408, 429]
    
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(
            max_retry_times=settings.getint('RETRY_TIMES', 3),
            retry_http_codes=settings.getlist('RETRY_HTTP_CODES', [500, 502, 503, 504, 408, 429])
        )
    
    def process_response(self, request, response, spider):
        if response.status in self.retry_http_codes:
            retry_times = request.meta.get('retry_times', 0) + 1
            
            if retry_times <= self.max_retry_times:
                # Exponential backoff
                delay = 2 ** retry_times
                spider.logger.warning(
                    f'Retrying {request.url} (attempt {retry_times}/{self.max_retry_times}) '
                    f'after {delay}s delay due to status {response.status}'
                )
                
                retryreq = request.copy()
                retryreq.meta['retry_times'] = retry_times
                retryreq.dont_filter = True
                
                return retryreq
        
        return response