"""
Advanced stealth middleware specifically designed for bypassing sophisticated
anti-bot systems like those used by city24.lv with Cloudflare protection.
"""

import random
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.exceptions import IgnoreRequest, NotConfigured
from scrapy.http import HtmlResponse
from scrapy_playwright.page import PageMethod
from utils.stealth_config import stealth_config, behavior_simulator

logger = logging.getLogger(__name__)


class StealthPlaywrightMiddleware:
    """Advanced Playwright middleware with comprehensive anti-detection measures."""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        if not self.enabled:
            raise NotConfigured('Stealth Playwright middleware disabled')
        
        self.stealth_cfg = stealth_config
        self.behavior_sim = behavior_simulator
        self.session_cookies = {}
        self.request_count = 0
        
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        enabled = settings.getbool('STEALTH_ENABLED', True)
        instance = cls(enabled=enabled)
        
        # Connect spider signals
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(instance.spider_closed, signal=signals.spider_closed)
        
        return instance
    
    def spider_opened(self, spider):
        """Initialize when spider opens."""
        logger.info(f"Stealth middleware enabled for spider: {spider.name}")
        
    def spider_closed(self, spider):
        """Cleanup when spider closes."""
        logger.info(f"Stealth middleware closed for spider: {spider.name}")
    
    def process_request(self, request, spider):
        """Enhanced request processing with stealth measures."""
        if not self.enabled:
            return None
        
        # Only apply to requests that use Playwright
        if not request.meta.get('playwright'):
            return None
        
        self.request_count += 1
        
        # Apply stealth configuration
        stealth_config = self.stealth_cfg.get_stealth_playwright_config()
        
        # Update request meta with stealth settings
        request.meta.update({
            'playwright_browser_type': stealth_config['browser_type'],
            'playwright_launch_options': stealth_config['launch_options'],
            'playwright_context_options': stealth_config['context_options'],
            'playwright_page_goto_kwargs': stealth_config['navigation_options'],
        })
        
        # Generate enhanced page methods for stealth
        stealth_methods = self._get_stealth_page_methods(request, spider)
        
        # Merge with existing page methods if any
        existing_methods = request.meta.get('playwright_page_methods', [])
        all_methods = stealth_methods + existing_methods
        
        request.meta['playwright_page_methods'] = all_methods
        
        # Add session-specific headers
        headers = self.stealth_cfg.get_realistic_headers()
        for key, value in headers.items():
            request.headers[key] = value
        
        # Add random delay between requests
        if self.request_count > 1:
            delay = random.uniform(2.0, 8.0)
            logger.debug(f"Adding {delay:.2f}s delay before request to {request.url}")
            time.sleep(delay)
        
        logger.debug(f"Applied stealth configuration to request: {request.url}")
        return None
    
    def _get_stealth_page_methods(self, request, spider) -> list:
        """Generate comprehensive stealth page methods."""
        timing = self.stealth_cfg.get_human_timing_delays()
        
        methods = [
            # Initial stealth setup
            PageMethod('add_init_script', self.stealth_cfg.get_fingerprint_override_script()),
            
            # Set realistic viewport
            PageMethod('set_viewport_size', **self.stealth_cfg.get_realistic_viewport()),
            
            # Navigate with proper wait strategy
            PageMethod('goto', request.url, wait_until='load', timeout=45000),
            
            # Wait for initial page load
            PageMethod('wait_for_load_state', 'load'),
            
            # Execute human behavior simulation
            PageMethod('evaluate', self.behavior_sim.get_page_interaction_script()),
            
            # Initial wait for JavaScript
            PageMethod('wait_for_timeout', int(timing['page_load_wait'] * 1000)),
            
            # Handle cookie consent
            PageMethod('evaluate', self.behavior_sim.get_cookie_handling_script()),
            
            # Wait after cookie handling
            PageMethod('wait_for_timeout', 3000),
            
            # Additional stealth measures
            self._get_cloudflare_bypass_method(),
            
            # Wait for dynamic content
            PageMethod('wait_for_timeout', int(timing['element_wait'] * 1000)),
            
            # Simulate user interaction
            self._get_user_interaction_method(),
            
            # Final wait for stability
            PageMethod('wait_for_timeout', 2000),
        ]
        
        # Add site-specific methods for city24.lv
        if 'city24.lv' in request.url:
            methods.extend(self._get_city24_specific_methods())
        
        return methods
    
    def _get_cloudflare_bypass_method(self) -> PageMethod:
        """Method to handle Cloudflare challenge pages."""
        return PageMethod('evaluate', '''
        async () => {
            // Wait for potential Cloudflare challenge
            await new Promise(resolve => setTimeout(resolve, 5000));
            
            // Check for Cloudflare challenge indicators
            const challengeIndicators = [
                'cf-challenge-running',
                'cf-challenge',
                'checking-browser',
                'cf-checking-browser'
            ];
            
            for (const indicator of challengeIndicators) {
                if (document.querySelector(`[class*="${indicator}"]`) || 
                    document.querySelector(`[id*="${indicator}"]`)) {
                    console.log('Cloudflare challenge detected, waiting...');
                    
                    // Wait for challenge to complete
                    let attempts = 0;
                    while (attempts < 30) {
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        
                        // Check if challenge is complete
                        const challengeComplete = !document.querySelector(`[class*="${indicator}"]`) &&
                                                !document.querySelector(`[id*="${indicator}"]`);
                        
                        if (challengeComplete) {
                            console.log('Cloudflare challenge completed');
                            break;
                        }
                        
                        attempts++;
                    }
                    
                    break;
                }
            }
            
            // Additional wait for page stability
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
        ''')
    
    def _get_user_interaction_method(self) -> PageMethod:
        """Method to simulate realistic user interaction."""
        return PageMethod('evaluate', '''
        async () => {
            // Simulate mouse movement over page elements
            const elements = document.querySelectorAll('a, button, input, div');
            if (elements.length > 0) {
                for (let i = 0; i < Math.min(3, elements.length); i++) {
                    const element = elements[Math.floor(Math.random() * elements.length)];
                    
                    // Hover over element
                    const event = new MouseEvent('mouseover', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    element.dispatchEvent(event);
                    
                    await new Promise(resolve => setTimeout(resolve, Math.random() * 500 + 200));
                }
            }
            
            // Scroll to different positions
            const scrollPositions = [0.25, 0.5, 0.75, 1.0];
            for (const position of scrollPositions) {
                window.scrollTo({
                    top: document.body.scrollHeight * position,
                    behavior: 'smooth'
                });
                await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));
            }
            
            // Return to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        ''')
    
    def _get_city24_specific_methods(self) -> list:
        """City24.lv specific stealth methods."""
        return [
            # Wait for React app to load
            PageMethod('wait_for_function', '''
                () => window.React || window.__REACT_DEVTOOLS_GLOBAL_HOOK__ || 
                     document.querySelector('[data-reactroot]') ||
                     document.querySelector('#root > *')
            ''', timeout=30000),
            
            # Wait for property listings to appear
            PageMethod('wait_for_function', '''
                () => {
                    const listings = document.querySelectorAll('a[href*="apartment"], a[href*="house"]');
                    return listings.length > 0;
                }
            ''', timeout=30000),
            
            # Handle any modal dialogs or popups
            PageMethod('evaluate', '''
            async () => {
                // Close any modal dialogs
                const modalCloseButtons = document.querySelectorAll(
                    '[aria-label="Close"], [data-testid="close"], .modal-close, .close-button'
                );
                
                for (const button of modalCloseButtons) {
                    if (button.offsetParent !== null) {
                        button.click();
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
                
                // Handle overlay elements
                const overlays = document.querySelectorAll('.overlay, .modal-overlay, .backdrop');
                for (const overlay of overlays) {
                    if (overlay.offsetParent !== null) {
                        overlay.click();
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                }
            }
            '''),
            
            # Final wait for page stability
            PageMethod('wait_for_timeout', 5000),
        ]
    
    def process_response(self, request, response, spider):
        """Process response with stealth validation."""
        if not self.enabled or not request.meta.get('playwright'):
            return response
        
        # Validate response indicates successful bypass
        content_length = len(response.text)
        
        if content_length < 2000:
            logger.warning(f"Suspiciously short response ({content_length} chars) from {response.url}")
            
            # Check for common blocking indicators
            blocking_indicators = [
                'access denied',
                'blocked',
                'captcha',
                'cloudflare',
                'security check',
                'please verify',
                'bot detection',
            ]
            
            content_lower = response.text.lower()
            for indicator in blocking_indicators:
                if indicator in content_lower:
                    logger.error(f"Potential blocking detected: '{indicator}' in response from {response.url}")
                    break
        
        # Log successful stealth bypass
        if content_length > 5000:  # Good sign for city24.lv
            logger.info(f"Successful stealth response from {response.url} ({content_length} chars)")
        
        return response
    
    def process_exception(self, request, exception, spider):
        """Handle exceptions with retry logic."""
        if not self.enabled:
            return None
        
        logger.warning(f"Exception in stealth request to {request.url}: {exception}")
        
        # Implement intelligent retry for specific exceptions
        retry_exceptions = [
            'TimeoutError',
            'TargetClosedError',
            'NetworkError',
        ]
        
        exception_name = type(exception).__name__
        if any(exc in exception_name for exc in retry_exceptions):
            retry_count = request.meta.get('stealth_retry_count', 0)
            max_retries = 2
            
            if retry_count < max_retries:
                logger.info(f"Retrying stealth request to {request.url} (attempt {retry_count + 1}/{max_retries})")
                
                retry_request = request.copy()
                retry_request.meta['stealth_retry_count'] = retry_count + 1
                retry_request.dont_filter = True
                
                # Increase delays for retries
                time.sleep(random.uniform(5.0, 15.0))
                
                return retry_request
        
        return None


class CloudflareBypassMiddleware:
    """Specialized middleware for Cloudflare bypass techniques."""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        if not self.enabled:
            raise NotConfigured('Cloudflare bypass middleware disabled')
        
        self.challenge_count = 0
    
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        enabled = settings.getbool('CLOUDFLARE_BYPASS_ENABLED', True)
        return cls(enabled=enabled)
    
    def process_response(self, request, response, spider):
        """Detect and handle Cloudflare challenges."""
        if not self.enabled:
            return response
        
        # Check for Cloudflare challenge indicators
        cf_indicators = [
            'cf-challenge',
            'checking your browser',
            'cloudflare',
            'ddos protection',
            'please wait',
            'security check',
        ]
        
        content_lower = response.text.lower()
        is_challenge = any(indicator in content_lower for indicator in cf_indicators)
        
        if is_challenge:
            self.challenge_count += 1
            logger.warning(f"Cloudflare challenge detected on {response.url} (count: {self.challenge_count})")
            
            # For Playwright requests, the challenge should be handled automatically
            # by the stealth methods, so we just log and continue
            if request.meta.get('playwright'):
                logger.info("Cloudflare challenge should be handled by Playwright stealth methods")
            else:
                # For non-Playwright requests, we might want to switch to Playwright
                logger.warning("Consider using Playwright for this request to handle Cloudflare")
        
        return response


class TLSFingerprintMiddleware:
    """Middleware to randomize TLS fingerprints for better stealth."""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        if not self.enabled:
            raise NotConfigured('TLS fingerprint middleware disabled')
    
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        enabled = settings.getbool('TLS_FINGERPRINT_ENABLED', True)
        return cls(enabled=enabled)
    
    def process_request(self, request, spider):
        """Randomize TLS settings for better fingerprint diversity."""
        if not self.enabled:
            return None
        
        # Add TLS randomization to Playwright context if applicable
        if request.meta.get('playwright'):
            context_options = request.meta.get('playwright_context_options', {})
            
            # Add random TLS configuration
            context_options.update({
                'ignore_https_errors': True,
                'extra_http_headers': {
                    **context_options.get('extra_http_headers', {}),
                    'sec-ch-ua': self._generate_random_sec_ch_ua(),
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': f'"{random.choice(["Windows", "macOS", "Linux"])}"',
                }
            })
            
            request.meta['playwright_context_options'] = context_options
        
        return None
    
    def _generate_random_sec_ch_ua(self) -> str:
        """Generate randomized sec-ch-ua header."""
        chrome_versions = ['119', '120', '121']
        chromium_versions = ['119', '120', '121']
        
        chrome_version = random.choice(chrome_versions)
        chromium_version = random.choice(chromium_versions)
        
        return f'"Not_A Brand";v="8", "Chromium";v="{chromium_version}", "Google Chrome";v="{chrome_version}"'