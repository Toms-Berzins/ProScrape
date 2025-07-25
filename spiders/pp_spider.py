import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from scrapy import Request
from scrapy_playwright.page import PageMethod
from spiders.base_spider import BaseRealEstateSpider
from spiders.items import ListingItem


class PPLVSpider(BaseRealEstateSpider):
    """Spider for scraping pp.lv real estate listings (dynamic JavaScript)."""
    
    name = 'pp_spider'
    allowed_domains = ['pp.lv']
    
    # Start URLs for different property types
    start_urls = [
        'https://pp.lv/lv/landing/nekustamais-ipasums?type=flat&location=riga',
        'https://pp.lv/lv/landing/nekustamais-ipasums?type=house&location=riga',
        'https://pp.lv/lv/landing/nekustamais-ipasums?type=flat&location=jurmala',
        'https://pp.lv/lv/landing/nekustamais-ipasums?type=house&location=jurmala',
        'https://pp.lv/lv/landing/nekustamais-ipasums?type=land&location=riga',
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2.5,
        'RANDOMIZE_DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'timeout': 40000,
        },
        'DOWNLOAD_HANDLERS': {
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
    }
    
    def start_requests(self):
        """Generate initial requests with Playwright."""
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'load'),  # Use 'load' instead of 'networkidle'
                        PageMethod('wait_for_timeout', 5000),  # Wait longer for heavy JS
                        # Handle cookie consent popup
                        PageMethod('evaluate', '''() => {
                            // Try multiple selectors for cookie consent
                            const selectors = [
                                '[data-accept-cookies]',
                                '.cookie-accept',
                                '#accept-cookies',
                                '.gdpr-accept',
                                'button[contains(text(), "Accept")]',
                                'button[contains(text(), "Piekrist")]'
                            ];
                            
                            for (const selector of selectors) {
                                const btn = document.querySelector(selector);
                                if (btn) {
                                    btn.click();
                                    break;
                                }
                            }
                        }'''),
                        PageMethod('wait_for_timeout', 2000),
                        # Scroll down to trigger lazy loading
                        PageMethod('evaluate', '''() => {
                            window.scrollTo(0, document.body.scrollHeight / 2);
                        }'''),
                        PageMethod('wait_for_timeout', 2000),
                    ]
                }
            )
    
    def parse_listing_urls(self, response):
        """Extract listing URLs from search results."""
        # PP.lv uses /nekustamais for real estate listings
        listing_selectors = [
            '//a[contains(@href, "/nekustamais")]/@href',
            '//a[contains(@href, "/ad/")]/@href',
            '//a[contains(@href, "/property/")]/@href',
            '//a[contains(@href, "/listing/")]/@href',
            '//a[contains(@class, "listing-link")]/@href',
            '//div[contains(@class, "property-card")]//a/@href',
        ]
        
        listing_links = []
        for selector in listing_selectors:
            links = response.xpath(selector).getall()
            listing_links.extend(links)
        
        # Filter and deduplicate
        unique_links = set()
        for link in listing_links:
            if link and ('/nekustamais' in link or '/ad/' in link or '/property/' in link or '/listing/' in link):
                full_url = urljoin(response.url, link)
                unique_links.add(full_url)
        
        return list(unique_links)
    
    def parse(self, response):
        """Parse search results page."""
        listing_urls = self.parse_listing_urls(response)
        
        # Process each listing
        for url in listing_urls:
            yield Request(
                url=url,
                callback=self.parse_listing,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'load'),  # Use 'load' instead of 'networkidle'
                        PageMethod('wait_for_timeout', 3000),
                        # Handle cookie consent on listing pages
                        PageMethod('evaluate', '''() => {
                            const selectors = [
                                '[data-accept-cookies]',
                                '.cookie-accept',
                                '#accept-cookies',
                                '.gdpr-accept'
                            ];
                            
                            for (const selector of selectors) {
                                const btn = document.querySelector(selector);
                                if (btn) {
                                    btn.click();
                                    break;
                                }
                            }
                        }'''),
                        PageMethod('wait_for_timeout', 1000),
                    ]
                }
            )
        
        # Handle pagination
        next_page = self.get_next_page_url(response)
        if next_page:
            yield Request(
                url=next_page,
                callback=self.parse,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'load'),  # Use 'load' instead of 'networkidle'
                        PageMethod('wait_for_timeout', 4000),
                        PageMethod('evaluate', '''() => {
                            const selectors = [
                                '[data-accept-cookies]',
                                '.cookie-accept',
                                '#accept-cookies'
                            ];
                            
                            for (const selector of selectors) {
                                const btn = document.querySelector(selector);
                                if (btn) {
                                    btn.click();
                                    break;
                                }
                            }
                        }'''),
                    ]
                }
            )
    
    def get_next_page_url(self, response):
        """Extract next page URL from pagination."""
        # Look for various pagination patterns
        next_selectors = [
            '//a[contains(@class, "next") or contains(@class, "pagination-next")]/@href',
            '//a[contains(text(), "Next") or contains(text(), "Nākamā")]/@href',
            '//a[@rel="next"]/@href',
        ]
        
        for selector in next_selectors:
            next_link = response.xpath(selector).get()
            if next_link:
                return urljoin(response.url, next_link)
        
        # Try to find page numbers
        current_page_selectors = [
            '//span[contains(@class, "current-page")]/text()',
            '//span[contains(@class, "active")]/text()',
        ]
        
        for selector in current_page_selectors:
            current_page = response.xpath(selector).get()
            if current_page:
                try:
                    current = int(current_page)
                    next_page_link = response.xpath(f'//a[text()="{current + 1}"]/@href').get()
                    if next_page_link:
                        return urljoin(response.url, next_page_link)
                except ValueError:
                    continue
        
        return None
    
    def parse_listing(self, response):
        """Parse individual listing from PP.lv."""
        try:
            # Extract listing ID from URL - PP.lv may use query params or path
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(response.url)
            
            # Try to extract from query parameters first
            listing_id = None
            query_params = parse_qs(parsed_url.query)
            if 'id' in query_params:
                listing_id = query_params['id'][0]
            elif 'listing' in query_params:
                listing_id = query_params['listing'][0]
            else:
                # Extract from path - try different patterns
                listing_id_match = re.search(r'/nekustamais[^/]*/([^/?]+)', response.url)
                if not listing_id_match:
                    listing_id_match = re.search(r'/ad/([^/]+)', response.url)
                if not listing_id_match:
                    listing_id_match = re.search(r'/property/([^/]+)', response.url)
                if not listing_id_match:
                    listing_id_match = re.search(r'/listing/([^/]+)', response.url)
                
                if listing_id_match:
                    listing_id = listing_id_match.group(1)
                else:
                    # Use a fallback - hash of URL
                    import hashlib
                    listing_id = hashlib.md5(response.url.encode()).hexdigest()[:8]
            
            if not listing_id:
                self.log_failure("unknown", "Could not extract listing ID from URL")
                return
            
            # Create item
            item = self.create_listing_item(response)
            item['listing_id'] = listing_id
            
            # Extract title - try multiple selectors
            title_selectors = [
                '//h1[contains(@class, "title") or contains(@class, "heading")]/text()',
                '//h1/text()',
                '//title/text()',
            ]
            
            title = None
            for selector in title_selectors:
                title = self.extract_text(response, selector)
                if title:
                    break
            
            item['title'] = title
            
            # Extract price - try multiple approaches
            price_selectors = [
                '//*[contains(@class, "price") or contains(@class, "cost")]//text()[normalize-space()]',
                '//*[contains(text(), "€") or contains(text(), "EUR")]//text()',
                '//span[contains(@class, "amount")]/text()',
            ]
            
            price_text = None
            for selector in price_selectors:
                price_text = self.extract_text(response, selector)
                if price_text and ('€' in price_text or 'EUR' in price_text or re.search(r'\d+', price_text)):
                    break
            
            if price_text:
                item['price'] = self.parse_price(price_text)
                item['price_currency'] = 'EUR'
            
            # Extract area
            area_selectors = [
                '//*[contains(text(), "m²") or contains(text(), "m2")]//text()',
                '//td[contains(text(), "Area") or contains(text(), "Platība")]/following-sibling::td/text()',
                '//*[contains(@class, "area")]//text()',
            ]
            
            area_text = None
            for selector in area_selectors:
                area_text = self.extract_text(response, selector)
                if area_text and ('m²' in area_text or re.search(r'\d+', area_text)):
                    break
            
            if area_text:
                item['area_sqm'] = self.parse_area(area_text)
            
            # Extract rooms
            rooms_selectors = [
                '//td[contains(text(), "Rooms") or contains(text(), "Istabas")]/following-sibling::td/text()',
                '//*[contains(text(), "room") or contains(text(), "istab")]//text()',
                '//*[contains(@class, "rooms")]//text()',
            ]
            
            rooms_text = None
            for selector in rooms_selectors:
                rooms_text = self.extract_text(response, selector)
                if rooms_text and re.search(r'\d+', rooms_text):
                    break
            
            if rooms_text:
                item['rooms'] = self.parse_rooms_count(rooms_text)
            
            # Extract floor information
            floor_selectors = [
                '//td[contains(text(), "Floor") or contains(text(), "Stāvs")]/following-sibling::td/text()',
                '//*[contains(text(), "floor") or contains(text(), "stāv")]//text()',
            ]
            
            floor_text = None
            for selector in floor_selectors:
                floor_text = self.extract_text(response, selector)
                if floor_text and re.search(r'\d+', floor_text):
                    break
            
            if floor_text:
                floor_info = self.parse_floor_info(floor_text)
                if floor_info.get('floor'):
                    item['floor'] = floor_info['floor']
                if floor_info.get('total_floors'):
                    item['total_floors'] = floor_info['total_floors']
            
            # Extract address/location
            address_selectors = [
                '//*[contains(@class, "address") or contains(@class, "location")]//text()[normalize-space()]',
                '//td[contains(text(), "Address") or contains(text(), "Adrese")]/following-sibling::td/text()',
                '//*[contains(@class, "locality")]//text()',
            ]
            
            address = None
            for selector in address_selectors:
                address = self.extract_text(response, selector)
                if address and len(address.strip()) > 3:
                    break
            
            if address:
                item['address'] = address.strip()
                
                # Extract city
                if 'Rīga' in address or 'Riga' in address:
                    item['city'] = 'Riga'
                elif 'Jūrmala' in address or 'Jurmala' in address:
                    item['city'] = 'Jurmala'
                elif 'Liepāja' in address or 'Liepaja' in address:
                    item['city'] = 'Liepaja'
            
            # Extract property type from URL or content
            url_lower = response.url.lower()
            title_lower = (title or '').lower()
            
            if 'type=flat' in url_lower or 'apartment' in title_lower or 'dzīvoklis' in title_lower:
                item['property_type'] = 'apartment'
            elif 'type=house' in url_lower or 'house' in title_lower or 'māja' in title_lower:
                item['property_type'] = 'house'
            elif 'type=land' in url_lower or 'land' in title_lower or 'zeme' in title_lower:
                item['property_type'] = 'land'
            
            # Extract description
            description_selectors = [
                '//*[contains(@class, "description") or contains(@class, "details")]//text()',
                '//div[contains(@class, "content")]//p//text()',
                '//*[contains(@class, "text-content")]//text()',
            ]
            
            description_parts = []
            for selector in description_selectors:
                parts = response.xpath(selector).getall()
                description_parts.extend([part.strip() for part in parts if part.strip() and len(part.strip()) > 10])
            
            if description_parts:
                description = ' '.join(description_parts[:5])  # Limit to avoid too much text
                item['description'] = description
            
            # Extract images
            image_urls = []
            
            # Try multiple image selectors
            image_selectors = [
                '//img[contains(@src, "property") or contains(@src, "listing")]/@src',
                '//img[contains(@class, "property") or contains(@class, "listing")]/@src',
                '//img/@data-src',
                '//div/@data-bg',
                '//div/@data-image',
            ]
            
            for selector in image_selectors:
                imgs = response.xpath(selector).getall()
                for img_url in imgs:
                    if img_url and any(ext in img_url.lower() for ext in ['jpg', 'jpeg', 'png', 'webp']):
                        full_img_url = urljoin(response.url, img_url)
                        image_urls.append(full_img_url)
            
            item['image_urls'] = list(set(image_urls))  # Remove duplicates
            
            # Extract features
            features = []
            
            # Look for feature lists
            feature_selectors = [
                '//*[contains(@class, "feature") or contains(@class, "amenity")]//text()',
                '//*[contains(@class, "property-features")]//text()',
                '//ul[contains(@class, "features")]//li//text()',
            ]
            
            for selector in feature_selectors:
                feature_texts = response.xpath(selector).getall()
                for feature_text in feature_texts:
                    if feature_text and feature_text.strip() and len(feature_text.strip()) > 2:
                        features.append(feature_text.strip())
            
            # Look for common features in description
            if item.get('description'):
                feature_keywords = ['balkons', 'parkošana', 'lifts', 'mēbelēts', 'renovēts', 'jauns', 'garāža']
                for keyword in feature_keywords:
                    if keyword.lower() in item['description'].lower():
                        features.append(keyword)
            
            item['features'] = list(set(features)) if features else []
            
            # Extract posting date
            date_selectors = [
                '//*[contains(text(), "Added") or contains(text(), "Pievienots")]/following-sibling::*/text()',
                '//*[contains(text(), "Posted") or contains(text(), "Publicēts")]/following-sibling::*/text()',
                '//*[contains(@class, "date")]//text()',
            ]
            
            date_text = None
            for selector in date_selectors:
                date_text = self.extract_text(response, selector)
                if date_text and re.search(r'\d+', date_text):
                    break
            
            if date_text:
                item['posted_date'] = self.parse_date(date_text)
            
            # Try to extract coordinates
            coords = self.extract_coordinates(response)
            if coords:
                item['latitude'] = coords.get('lat')
                item['longitude'] = coords.get('lng')
            
            # Store raw data for debugging
            item['raw_data'] = {
                'url': response.url,
                'response_length': len(response.text),
                'has_javascript': 'script' in response.text.lower(),
                'title_found': bool(title),
                'price_found': bool(price_text),
            }
            
            self.log_success(listing_id)
            yield item
            
        except Exception as e:
            self.log_failure(listing_id if 'listing_id' in locals() else 'unknown', str(e))
    
    def parse_rooms_count(self, rooms_text):
        """Parse room count from text."""
        if not rooms_text:
            return None
        
        # Look for numbers in the text
        match = re.search(r'(\d+)', rooms_text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def parse_floor_info(self, floor_text):
        """Parse floor information."""
        if not floor_text:
            return {}
        
        # Pattern for "3/5" format
        match = re.search(r'(\d+)/(\d+)', floor_text)
        if match:
            return {
                'floor': int(match.group(1)),
                'total_floors': int(match.group(2))
            }
        
        # Pattern for single floor number
        match = re.search(r'(\d+)', floor_text)
        if match:
            return {'floor': int(match.group(1))}
        
        return {}
    
    def parse_date(self, date_text):
        """Parse date from PP.lv format."""
        if not date_text:
            return None
        
        try:
            # Common Latvian date formats
            date_formats = [
                '%d.%m.%Y',
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%d.%m.%Y %H:%M',
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Could not parse date '{date_text}': {e}")
        
        return None
    
    def extract_coordinates(self, response):
        """Try to extract GPS coordinates from the page."""
        # Look for coordinate patterns in JavaScript
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
                        lat = float(matches[0])
                        # Validate Latvia coordinate range
                        if 55.0 < lat < 58.5:
                            coords['lat'] = lat
                    except (ValueError, IndexError):
                        pass
                elif 'lng' in pattern.lower() or 'longitude' in pattern.lower():
                    try:
                        lng = float(matches[0])
                        # Validate Latvia coordinate range  
                        if 20.0 < lng < 28.5:
                            coords['lng'] = lng
                    except (ValueError, IndexError):
                        pass
        
        return coords if len(coords) == 2 else None