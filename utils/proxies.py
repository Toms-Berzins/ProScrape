import random
import requests
import logging
from typing import List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class ProxyRotator:
    """Proxy rotation manager."""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxy_list = proxy_list or settings.proxy_list or []
        self.current_index = 0
        self.working_proxies = []
        self.failed_proxies = set()
        
        if self.proxy_list:
            self.test_proxies()
    
    def test_proxies(self, test_url: str = "http://httpbin.org/ip", timeout: int = 10):
        """Test all proxies and keep only working ones."""
        logger.info(f"Testing {len(self.proxy_list)} proxies...")
        
        self.working_proxies = []
        
        for proxy in self.proxy_list:
            if self.test_single_proxy(proxy, test_url, timeout):
                self.working_proxies.append(proxy)
                logger.info(f"Proxy working: {proxy}")
            else:
                self.failed_proxies.add(proxy)
                logger.warning(f"Proxy failed: {proxy}")
        
        logger.info(f"Working proxies: {len(self.working_proxies)}/{len(self.proxy_list)}")
    
    def test_single_proxy(self, proxy: str, test_url: str, timeout: int) -> bool:
        """Test a single proxy."""
        try:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                headers={'User-Agent': 'ProxyTester/1.0'}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.debug(f"Proxy test failed for {proxy}: {e}")
            return False
    
    def get_proxy(self) -> Optional[str]:
        """Get the next working proxy in rotation."""
        if not self.working_proxies:
            return None
        
        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        
        return proxy
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random working proxy."""
        if not self.working_proxies:
            return None
        
        return random.choice(self.working_proxies)
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed and remove from working list."""
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
            self.failed_proxies.add(proxy)
            logger.warning(f"Marked proxy as failed: {proxy}")
    
    def get_proxy_dict(self, proxy: str) -> dict:
        """Convert proxy string to requests-compatible dict."""
        return {
            'http': proxy,
            'https': proxy
        }
    
    def has_working_proxies(self) -> bool:
        """Check if there are any working proxies available."""
        return len(self.working_proxies) > 0


class UserAgentRotator:
    """User-Agent rotation manager."""
    
    def __init__(self, user_agents: Optional[List[str]] = None):
        self.user_agents = user_agents or settings.user_agents or self.get_default_user_agents()
        self.current_index = 0
    
    def get_default_user_agents(self) -> List[str]:
        """Get default user agent list."""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
    
    def get_user_agent(self) -> str:
        """Get the next user agent in rotation."""
        user_agent = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return user_agent
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent."""
        return random.choice(self.user_agents)


# Global instances
proxy_rotator = ProxyRotator()
user_agent_rotator = UserAgentRotator()