import re
import json
import asyncio
import random
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from scrapy import Request
from scrapy_playwright.page import PageMethod
from spiders.base_spider import BaseRealEstateSpider
from spiders.items import ListingItem
from utils.stealth_config import stealth_config, behavior_simulator


class City24Spider(BaseRealEstateSpider):
    """Advanced stealth spider for scraping city24.lv real estate listings.
    
    This spider implements comprehensive anti-bot evasion techniques including:
    - Browser fingerprint randomization
    - Human-like behavior simulation
    - Cloudflare challenge bypass
    - Advanced request timing
    - Realistic browser automation
    
    Designed to bypass sophisticated detection systems while maintaining
    reliable data extraction from JavaScript-heavy pages.
    """
    
    name = 'city24_spider'
    allowed_domains = ['city24.lv']
    
    start_urls = ['https://city24.lv/en']
    
    custom_settings = {
        # Enhanced stealth settings
        'DOWNLOAD_DELAY': 8,
        'RANDOMIZE_DOWNLOAD_DELAY': 5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_TIMEOUT': 120,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 523, 524, 403],
        
        # Stealth middleware configuration
        'STEALTH_ENABLED': True,
        'CLOUDFLARE_BYPASS_ENABLED': True,
        'TLS_FINGERPRINT_ENABLED': True,
        
        # Enhanced Playwright settings
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': False,  # Use headed mode for better stealth
            'timeout': 120000,
            'slow_mo': random.randint(200, 800),
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--start-maximized',
            ]
        },
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 60000,
        'PLAYWRIGHT_PAGE_GOTO_KWARGS': {
            'wait_until': 'load',
            'timeout': 60000,
        },
        
        # Enhanced middleware stack
        'DOWNLOADER_MIDDLEWARES': {
            'spiders.stealth_middleware.StealthPlaywrightMiddleware': 585,
            'spiders.stealth_middleware.CloudflareBypassMiddleware': 586,
            'spiders.stealth_middleware.TLSFingerprintMiddleware': 587,
            'spiders.middlewares.EnhancedUserAgentMiddleware': 400,
            'spiders.middlewares.EnhancedProxyMiddleware': 410,
            'spiders.middlewares.EnhancedRetryMiddleware': 420,
        },
        
        'DOWNLOAD_HANDLERS': {
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
    }
    
    def start_requests(self):
        """Generate initial requests with advanced stealth configuration."""
        self.logger.info("Starting City24 spider with advanced anti-bot evasion")
        
        # Get stealth configuration
        stealth_cfg = stealth_config.get_stealth_playwright_config()
        timing = stealth_config.get_human_timing_delays()
        
        for url in self.start_urls:
            # Generate comprehensive stealth page methods
            page_methods = self._get_comprehensive_stealth_methods(url)
            
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    'playwright': True,
                    'playwright_page_methods': page_methods,
                    'stealth_enabled': True,
                    'max_retry_times': 3,
                },
                headers=stealth_config.get_realistic_headers(),
                dont_filter=True
            )
    
    def parse_listing_urls(self, response):
        """Extract listing URLs from the main page."""
        property_links = response.xpath('//a[contains(@href, "/apartment") or contains(@href, "/house")]/@href').getall()
        
        for link in property_links[:5]:  # Limit to 5 for testing
            if link.startswith('/'):
                yield urljoin(response.url, link)
            else:
                yield link
    
    def parse(self, response):
        """Parse the main page and extract listing URLs with validation."""
        self.logger.info(f"Parsing main page: {response.url} (content length: {len(response.text)})")
        
        # Validate successful page load
        if len(response.text) < 2000:
            self.logger.warning(f"Suspiciously short response from {response.url}, may be blocked")
            return
        
        # Check for successful React app load
        if 'react' not in response.text.lower() and 'javascript' not in response.text.lower():
            self.logger.warning("JavaScript application may not have loaded properly")
        
        listing_urls = list(self.parse_listing_urls(response))
        self.logger.info(f"Successfully extracted {len(listing_urls)} property links")
        
        if len(listing_urls) == 0:
            self.logger.error("No property links found - possible anti-bot blocking")
            self._log_response_debug_info(response)
            return
        
        # Process each listing with stealth configuration
        for url in listing_urls:
            # Add random delay between listing requests
            random_delay = random.uniform(3.0, 8.0)
            
            yield Request(
                url=url,
                callback=self.parse_listing,
                meta={
                    'playwright': True,
                    'playwright_page_methods': self._get_listing_stealth_methods(),
                    'stealth_enabled': True,
                    'download_delay': random_delay,
                },
                headers=stealth_config.get_realistic_headers(),
                dont_filter=True
            )
    
    def _get_comprehensive_stealth_methods(self, url):
        """Get comprehensive stealth methods for initial page load."""
        timing = stealth_config.get_human_timing_delays()
        
        return [
            # Enhanced fingerprint protection
            PageMethod('add_init_script', stealth_config.get_fingerprint_override_script()),
            
            # Set realistic browser properties
            PageMethod('set_viewport_size', **stealth_config.get_realistic_viewport()),
            
            # Navigate with proper timing
            PageMethod('goto', url, wait_until='load', timeout=60000),
            
            # Initial page load wait
            PageMethod('wait_for_load_state', 'load'),
            
            # Execute human behavior simulation
            PageMethod('evaluate', behavior_simulator.get_page_interaction_script()),
            
            # Wait for JavaScript to initialize
            PageMethod('wait_for_timeout', int(timing['page_load_wait'] * 1000)),
            
            # Handle Cloudflare challenges
            PageMethod('evaluate', '''
            async () => {
                // Wait for potential Cloudflare challenge
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                const challengeSelectors = [
                    '[class*="cf-challenge"]',
                    '[id*="cf-challenge"]',
                    '[class*="checking-browser"]'
                ];
                
                for (const selector of challengeSelectors) {
                    if (document.querySelector(selector)) {
                        console.log('Cloudflare challenge detected, waiting...');
                        let attempts = 0;
                        while (attempts < 30) {
                            await new Promise(resolve => setTimeout(resolve, 1000));
                            if (!document.querySelector(selector)) {
                                console.log('Challenge completed');
                                break;
                            }
                            attempts++;
                        }
                        break;
                    }
                }
            }
            '''),
            
            # Handle cookie consent
            PageMethod('evaluate', behavior_simulator.get_cookie_handling_script()),
            
            # Wait for React app to load
            PageMethod('wait_for_function', '''
                () => {
                    return window.React || 
                           window.__REACT_DEVTOOLS_GLOBAL_HOOK__ || 
                           document.querySelector('[data-reactroot]') ||
                           document.querySelector('#root > *') ||
                           document.querySelectorAll('a[href*="apartment"], a[href*="house"]').length > 0;
                }
            ''', timeout=45000),
            
            # Additional wait for dynamic content
            PageMethod('wait_for_timeout', 8000),
            
            # Final interaction simulation
            PageMethod('evaluate', '''
            async () => {
                // Simulate scrolling to load any lazy content
                window.scrollTo({ top: document.body.scrollHeight / 2, behavior: 'smooth' });
                await new Promise(resolve => setTimeout(resolve, 2000));
                window.scrollTo({ top: 0, behavior: 'smooth' });
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            '''),
        ]
    
    def _get_listing_stealth_methods(self):
        """Get stealth methods for individual listing pages."""
        return [
            PageMethod('add_init_script', stealth_config.get_fingerprint_override_script()),
            PageMethod('wait_for_load_state', 'load'),
            PageMethod('wait_for_timeout', 3000),
            PageMethod('evaluate', '''
            async () => {
                // Simulate user interaction on listing page
                const images = document.querySelectorAll('img');
                if (images.length > 0) {
                    images[0].scrollIntoView({ behavior: 'smooth' });
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
                
                // Scroll through content
                window.scrollTo({ top: document.body.scrollHeight * 0.3, behavior: 'smooth' });
                await new Promise(resolve => setTimeout(resolve, 1500));
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
            '''),
        ]
    
    def _log_response_debug_info(self, response):
        """Log debug information about the response."""
        self.logger.debug(f"Response URL: {response.url}")
        self.logger.debug(f"Response status: {response.status}")
        self.logger.debug(f"Response headers: {dict(response.headers)}")
        self.logger.debug(f"Response length: {len(response.text)}")
        
        # Check for blocking indicators
        blocking_indicators = [
            'access denied', 'blocked', 'captcha', 'cloudflare',
            'security check', 'please verify', 'bot detection'
        ]
        
        content_lower = response.text.lower()
        for indicator in blocking_indicators:
            if indicator in content_lower:
                self.logger.warning(f"Blocking indicator found: '{indicator}'")
        
        # Log first 500 chars of response for debugging
        self.logger.debug(f"Response preview: {response.text[:500]}")
    
    def parse_listing(self, response):
        """Parse individual listing page with enhanced validation."""
        try:
            self.logger.info(f"Parsing listing: {response.url} (content length: {len(response.text)})")
            
            # Validate response
            if len(response.text) < 1000:
                self.logger.warning(f"Suspiciously short listing response from {response.url}")
                self._log_response_debug_info(response)
                return
            
            # Extract listing ID from URL
            listing_id_match = re.search(r'/(\d+)/?$', response.url)
            if not listing_id_match:
                self.logger.warning(f"Could not extract listing ID from {response.url}")
                return
            
            listing_id = listing_id_match.group(1)
            
            # Create listing item
            item = self.create_listing_item(response)
            item['listing_id'] = listing_id
            
            # Extract title - try multiple selectors
            title_selectors = [
                '//h1//text()',
                '//*[@class="title"]//text()',
                '//*[contains(@class, "property-title")]//text()',
                '//title/text()'
            ]
            
            title = None
            for selector in title_selectors:
                title = self.extract_text(response, selector)
                if title and len(title.strip()) > 5:
                    break
            
            item['title'] = title or 'No title found'
            
            # Extract price - look for Euro amounts
            price_selectors = [
                '//*[contains(@class, "price")]//text()',
                '//*[contains(text(), "€")]//text()',
                '//*[contains(text(), "EUR")]//text()',
            ]
            
            price_text = None
            for selector in price_selectors:
                price_text = self.extract_text(response, selector)
                if price_text and ('€' in price_text or 'EUR' in price_text):
                    break
            
            if price_text:
                item['price'] = self.parse_price(price_text)
                item['price_currency'] = 'EUR'
            
            # Extract area
            area_selectors = [
                '//*[contains(text(), "m²")]//text()',
                '//*[contains(@class, "area")]//text()',
            ]
            
            area_text = None
            for selector in area_selectors:
                area_text = self.extract_text(response, selector)
                if area_text and 'm²' in area_text:
                    break
            
            if area_text:
                item['area_sqm'] = self.parse_area(area_text)
            
            # Extract rooms
            rooms_selectors = [
                '//*[contains(text(), "room") or contains(text(), "Room")]//text()',
                '//*[contains(@class, "rooms")]//text()',
                '//td[contains(text(), "Rooms")]/following-sibling::td/text()',
                '//*[contains(text(), "istabas")]//text()',  # Latvian for rooms
            ]
            
            rooms_text = None
            for selector in rooms_selectors:
                rooms_text = self.extract_text(response, selector)
                if rooms_text and any(digit.isdigit() for digit in rooms_text):
                    break
            
            if rooms_text:
                rooms_match = re.search(r'(\d+)', rooms_text)
                if rooms_match:
                    item['rooms'] = int(rooms_match.group(1))
            
            # Extract floor information
            floor_selectors = [
                '//td[contains(text(), "Floor")]/following-sibling::td/text()',
                '//*[contains(text(), "stāvs")]//text()',  # Latvian for floor
                '//*[contains(@class, "floor")]//text()',
            ]
            
            floor_text = None
            for selector in floor_selectors:
                floor_text = self.extract_text(response, selector)
                if floor_text and ('/' in floor_text or any(digit.isdigit() for digit in floor_text)):
                    break
            
            if floor_text:
                # Handle "3/5" format (floor/total_floors)
                floor_match = re.search(r'(\d+)/(\d+)', floor_text)
                if floor_match:
                    item['floor'] = int(floor_match.group(1))
                    item['total_floors'] = int(floor_match.group(2))
                else:
                    # Single floor number
                    single_floor = re.search(r'(\d+)', floor_text)
                    if single_floor:
                        item['floor'] = int(single_floor.group(1))
            
            # Extract address and location
            address_selectors = [
                '//*[contains(@class, "address")]//text()',
                '//*[contains(@class, "location")]//text()',
                '//*[contains(text(), "Address")]//text()',
                '//td[contains(text(), "Location")]/following-sibling::td/text()',
            ]
            
            address_text = None
            for selector in address_selectors:
                address_text = self.extract_text(response, selector)
                if address_text and len(address_text.strip()) > 5:
                    break
            
            if address_text:
                item['address'] = address_text.strip()
                
                # Extract city from address
                if 'Riga' in address_text or 'Rīga' in address_text:
                    item['city'] = 'Riga'
                elif 'Jurmala' in address_text or 'Jūrmala' in address_text:
                    item['city'] = 'Jurmala'
                elif 'Daugavpils' in address_text:
                    item['city'] = 'Daugavpils'
                elif 'Liepāja' in address_text or 'Liepaja' in address_text:
                    item['city'] = 'Liepaja'
            
            # Extract coordinates if available in JavaScript or data attributes
            coords = self.extract_coordinates(response)
            if coords:
                item['latitude'] = coords.get('lat')
                item['longitude'] = coords.get('lng')
            
            # Extract features and amenities
            features = []
            feature_selectors = [
                '//*[contains(@class, "feature")]//text()',
                '//*[contains(@class, "amenity")]//text()',
                '//*[contains(@class, "facility")]//text()',
                '//ul[contains(@class, "features")]//li//text()',
            ]
            
            for selector in feature_selectors:
                feature_texts = response.xpath(selector).getall()
                for text in feature_texts:
                    if text and text.strip() and len(text.strip()) > 2:
                        features.append(text.strip())
            
            # Look for common features in description
            if item.get('description'):
                feature_keywords = [
                    'balcony', 'balkons', 'parking', 'elevator', 'lifts', 
                    'furnished', 'renovated', 'new building', 'garage',
                    'terrace', 'garden', 'cellar', 'loggia'
                ]
                for keyword in feature_keywords:
                    if keyword.lower() in item['description'].lower():
                        features.append(keyword)
            
            item['features'] = list(set(features)) if features else []
            
            # Extract posting date
            date_selectors = [
                '//*[contains(text(), "Posted") or contains(text(), "Added")]/following-sibling::*/text()',
                '//*[contains(text(), "Date")]//text()',
                '//*[contains(@class, "date")]//text()',
                '//time/@datetime',
            ]
            
            date_text = None
            for selector in date_selectors:
                date_text = self.extract_text(response, selector)
                if date_text and any(char.isdigit() for char in date_text):
                    break
            
            if date_text:
                item['posted_date'] = self.parse_date(date_text)
            
            # Extract basic property info
            property_info = response.xpath('//div[contains(@class, "property-info")]//text()').getall()
            description_parts = response.xpath('//div[contains(@class, "description")]//text()').getall()
            
            if property_info:
                item['description'] = ' '.join([text.strip() for text in property_info if text.strip()])
            elif description_parts:
                item['description'] = ' '.join([text.strip() for text in description_parts if text.strip()])
            
            # Extract images
            image_urls = []
            img_selectors = [
                '//img[contains(@src, "property")]/@src',
                '//img[contains(@src, "real-estate")]/@src',
                '//img[contains(@class, "property")]/@src',
            ]
            
            for selector in img_selectors:
                imgs = response.xpath(selector).getall()
                for img in imgs:
                    if img and any(ext in img.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        full_img_url = urljoin(response.url, img)
                        image_urls.append(full_img_url)
            
            item['image_urls'] = list(set(image_urls))[:10]  # Limit to 10 images
            
            # Set property type based on URL
            if '/apartment' in response.url:
                item['property_type'] = 'apartment'
            elif '/house' in response.url:
                item['property_type'] = 'house'
            else:
                item['property_type'] = 'unknown'
            
            # Extract listing type (sell/rent) from price text and content
            listing_type = self.determine_listing_type(response, price_text)
            item['listing_type'] = listing_type
            
            # Store source info
            item['source_url'] = response.url
            item['source_site'] = 'city24.lv'
            
            self.log_success(listing_id)
            yield item
            
        except Exception as e:
            self.logger.error(f"Error parsing listing {response.url}: {e}")
            self.log_failure(listing_id if 'listing_id' in locals() else 'unknown', str(e))
            # Log additional debug info on errors
            self._log_response_debug_info(response)
    
    def extract_coordinates(self, response):
        """Try to extract GPS coordinates from JavaScript or data attributes."""
        try:
            # Look for common coordinate patterns in JavaScript
            coord_patterns = [
                r'lat["\']?\s*:\s*([0-9.-]+)',
                r'lng["\']?\s*:\s*([0-9.-]+)',
                r'latitude["\']?\s*:\s*([0-9.-]+)',
                r'longitude["\']?\s*:\s*([0-9.-]+)',
                r'"lat"\s*:\s*([0-9.-]+)',
                r'"lng"\s*:\s*([0-9.-]+)',
            ]
            
            coords = {}
            
            for pattern in coord_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    if 'lat' in pattern.lower():
                        try:
                            lat_val = float(matches[0])
                            # Validate Latvia coordinates range
                            if 55.0 <= lat_val <= 58.5:
                                coords['lat'] = lat_val
                        except (ValueError, IndexError):
                            pass
                    elif 'lng' in pattern.lower() or 'longitude' in pattern.lower():
                        try:
                            lng_val = float(matches[0])
                            # Validate Latvia coordinates range
                            if 20.0 <= lng_val <= 28.5:
                                coords['lng'] = lng_val
                        except (ValueError, IndexError):
                            pass
            
            return coords if len(coords) == 2 else None
            
        except Exception as e:
            self.logger.warning(f"Error extracting coordinates: {e}")
            return None
    
    def parse_date(self, date_text):
        """Parse date from various City24.lv formats."""
        if not date_text:
            return None
        
        try:
            # Clean the date text
            date_text = date_text.strip()
            
            # Try different date formats common in Latvia
            date_formats = [
                '%d.%m.%Y',          # 25.12.2023
                '%Y-%m-%d',          # 2023-12-25
                '%d/%m/%Y',          # 25/12/2023
                '%d %B %Y',          # 25 December 2023
                '%B %d, %Y',         # December 25, 2023
                '%d.%m.%y',          # 25.12.23
                '%d-%m-%Y',          # 25-12-2023
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_text, fmt)
                except ValueError:
                    continue
            
            # Try to extract date from longer text
            date_match = re.search(r'(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})', date_text)
            if date_match:
                extracted_date = date_match.group(1)
                for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%y']:
                    try:
                        return datetime.strptime(extracted_date, fmt)
                    except ValueError:
                        continue
                        
        except Exception as e:
            self.logger.warning(f"Could not parse date '{date_text}': {e}")
        
        return None
    
    def determine_listing_type(self, response, price_text):
        """Determine if listing is for sale or rent based on price indicators and page content."""
        try:
            # Check price text for rental indicators
            if price_text:
                price_lower = price_text.lower()
                # Common rental indicators in English and Latvian
                rent_indicators = [
                    '/mēn', '/month', 'per month', 'monthly', 'mēnesī',
                    'rent', 'rental', 'īre', 'noma', 'iznomā'
                ]
                
                for indicator in rent_indicators:
                    if indicator in price_lower:
                        return 'rent'
            
            # Check page content for rental/sale keywords
            page_text = response.text.lower()
            
            # Look for stronger indicators in the full text
            if any(keyword in page_text for keyword in ['for rent', 'rental', 'īre', 'noma', 'iznomā']):
                return 'rent'
            
            if any(keyword in page_text for keyword in ['for sale', 'pārdod', 'pārdošana', 'sale']):
                return 'sell'
            
            # Check URL patterns (city24.lv might have different sections)
            url_lower = response.url.lower()
            if any(keyword in url_lower for keyword in ['rent', 'rental', 'īre', 'noma']):
                return 'rent'
            
            if any(keyword in url_lower for keyword in ['sale', 'sell', 'pārdod', 'pārdošana']):
                return 'sell'
            
            # Default assumption: if no rental indicators found, it's likely for sale
            return 'sell'
            
        except Exception as e:
            self.logger.warning(f"Error determining listing type: {e}")
            return None