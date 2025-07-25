import random
import requests
import logging
import time
import threading
from typing import List, Optional, Dict
from config.settings import settings

logger = logging.getLogger(__name__)


class ProxyRotator:
    """Enhanced proxy rotation manager with health checking and automatic failover."""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxy_list = proxy_list or settings.proxy_list or []
        self.current_index = 0
        self.working_proxies = []
        self.failed_proxies = set()
        self.proxy_stats: Dict[str, Dict] = {}
        self.health_check_thread = None
        self.health_check_running = False
        
        if self.proxy_list:
            self.initialize_proxy_stats()
            self.test_proxies()
            self.start_health_monitoring()
    
    def initialize_proxy_stats(self):
        """Initialize statistics tracking for all proxies."""
        for proxy in self.proxy_list:
            self.proxy_stats[proxy] = {
                'success_count': 0,
                'failure_count': 0,
                'last_success': None,
                'last_failure': None,
                'avg_response_time': 0,
                'consecutive_failures': 0,
                'is_healthy': True
            }
    
    def update_proxy_stats(self, proxy: str, success: bool, response_time: float = 0):
        """Update statistics for a proxy."""
        if proxy not in self.proxy_stats:
            self.proxy_stats[proxy] = {
                'success_count': 0,
                'failure_count': 0,
                'last_success': None,
                'last_failure': None,
                'avg_response_time': 0,
                'consecutive_failures': 0,
                'is_healthy': True
            }
        
        stats = self.proxy_stats[proxy]
        current_time = time.time()
        
        if success:
            stats['success_count'] += 1
            stats['last_success'] = current_time
            stats['consecutive_failures'] = 0
            stats['is_healthy'] = True
            
            # Update average response time
            if stats['avg_response_time'] == 0:
                stats['avg_response_time'] = response_time
            else:
                stats['avg_response_time'] = (stats['avg_response_time'] + response_time) / 2
        else:
            stats['failure_count'] += 1
            stats['last_failure'] = current_time
            stats['consecutive_failures'] += 1
            
            # Mark as unhealthy after consecutive failures
            if stats['consecutive_failures'] >= settings.max_proxy_retries:
                stats['is_healthy'] = False
    
    def start_health_monitoring(self):
        """Start background health monitoring of proxies."""
        if not self.health_check_running:
            self.health_check_running = True
            self.health_check_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
            self.health_check_thread.start()
            logger.info("Started proxy health monitoring")
    
    def stop_health_monitoring(self):
        """Stop background health monitoring."""
        self.health_check_running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
            logger.info("Stopped proxy health monitoring")
    
    def _health_monitor_loop(self):
        """Background loop for monitoring proxy health."""
        while self.health_check_running:
            try:
                self._perform_health_check()
                time.sleep(settings.proxy_health_check_interval)
            except Exception as e:
                logger.error(f"Error in proxy health monitoring: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _perform_health_check(self):
        """Perform health check on all proxies."""
        logger.debug("Performing proxy health check...")
        
        for proxy in self.proxy_list.copy():
            start_time = time.time()
            is_healthy = self.test_single_proxy(proxy, settings.proxy_test_url, settings.proxy_test_timeout)
            response_time = time.time() - start_time
            
            self.update_proxy_stats(proxy, is_healthy, response_time)
            
            if is_healthy and proxy not in self.working_proxies:
                self.working_proxies.append(proxy)
                if proxy in self.failed_proxies:
                    self.failed_proxies.remove(proxy)
                logger.info(f"Proxy recovered: {proxy}")
            elif not is_healthy and proxy in self.working_proxies:
                self.working_proxies.remove(proxy)
                self.failed_proxies.add(proxy)
                logger.warning(f"Proxy failed health check: {proxy}")
    
    def test_proxies(self, test_url: str = None, timeout: int = None):
        """Test all proxies and keep only working ones."""
        test_url = test_url or settings.proxy_test_url
        timeout = timeout or settings.proxy_test_timeout
        
        logger.info(f"Testing {len(self.proxy_list)} proxies...")
        
        self.working_proxies = []
        
        for proxy in self.proxy_list:
            start_time = time.time()
            is_working = self.test_single_proxy(proxy, test_url, timeout)
            response_time = time.time() - start_time
            
            self.update_proxy_stats(proxy, is_working, response_time)
            
            if is_working:
                self.working_proxies.append(proxy)
                logger.info(f"Proxy working: {proxy} ({response_time:.2f}s)")
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
        """Get the next working proxy in rotation, preferring healthiest ones."""
        if not self.working_proxies:
            return None
        
        # Sort by health and performance
        healthy_proxies = [p for p in self.working_proxies 
                          if self.proxy_stats.get(p, {}).get('is_healthy', True)]
        
        if not healthy_proxies:
            # Fallback to any working proxy
            healthy_proxies = self.working_proxies
        
        # Sort by success rate and response time
        healthy_proxies.sort(key=lambda p: (
            self._get_success_rate(p),
            -self.proxy_stats.get(p, {}).get('avg_response_time', 999)
        ), reverse=True)
        
        proxy = healthy_proxies[self.current_index % len(healthy_proxies)]
        self.current_index = (self.current_index + 1) % len(healthy_proxies)
        
        return proxy
    
    def _get_success_rate(self, proxy: str) -> float:
        """Calculate success rate for a proxy."""
        stats = self.proxy_stats.get(proxy, {})
        total = stats.get('success_count', 0) + stats.get('failure_count', 0)
        if total == 0:
            return 1.0
        return stats.get('success_count', 0) / total
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random working proxy."""
        if not self.working_proxies:
            return None
        
        return random.choice(self.working_proxies)
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed and remove from working list."""
        self.update_proxy_stats(proxy, success=False)
        
        if proxy in self.working_proxies:
            stats = self.proxy_stats.get(proxy, {})
            # Only remove if it has too many consecutive failures
            if stats.get('consecutive_failures', 0) >= settings.max_proxy_retries:
                self.working_proxies.remove(proxy)
                self.failed_proxies.add(proxy)
                logger.warning(f"Marked proxy as failed after {stats['consecutive_failures']} failures: {proxy}")
            else:
                logger.debug(f"Proxy {proxy} failed but still has retries left ({stats['consecutive_failures']}/{settings.max_proxy_retries})")
    
    def get_proxy_statistics(self) -> Dict:
        """Get comprehensive proxy statistics."""
        total_proxies = len(self.proxy_list)
        working_proxies = len(self.working_proxies)
        failed_proxies = len(self.failed_proxies)
        
        stats = {
            'total_proxies': total_proxies,
            'working_proxies': working_proxies,
            'failed_proxies': failed_proxies,
            'health_rate': working_proxies / total_proxies if total_proxies > 0 else 0,
            'proxy_details': {}
        }
        
        for proxy, data in self.proxy_stats.items():
            success_rate = self._get_success_rate(proxy)
            stats['proxy_details'][proxy] = {
                'success_rate': success_rate,
                'avg_response_time': data.get('avg_response_time', 0),
                'success_count': data.get('success_count', 0),
                'failure_count': data.get('failure_count', 0),
                'consecutive_failures': data.get('consecutive_failures', 0),
                'is_healthy': data.get('is_healthy', True),
                'status': 'working' if proxy in self.working_proxies else 'failed'
            }
        
        return stats
    
    def get_proxy_dict(self, proxy: str) -> dict:
        """Convert proxy string to requests-compatible dict."""
        return {
            'http': proxy,
            'https': proxy
        }
    
    def has_working_proxies(self) -> bool:
        """Check if there are any working proxies available."""
        return len(self.working_proxies) > 0
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        try:
            self.stop_health_monitoring()
        except:
            pass


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