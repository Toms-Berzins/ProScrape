import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from scrapy import Request
from scrapy_playwright.page import PageMethod
from spiders.base_spider import BaseRealEstateSpider
from spiders.items import ListingItem


class City24Spider(BaseRealEstateSpider):
    """Spider for scraping city24.lv real estate listings (dynamic JavaScript)."""
    
    name = 'city24_spider'
    allowed_domains = ['city24.lv']
    
    # Start URLs for different property types and cities
    start_urls = [
        'https://city24.lv/en',  # Main page with all listings
    ]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'timeout': 30000,
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
                        PageMethod('wait_for_load_state', 'networkidle'),
                        PageMethod('wait_for_timeout', 3000),  # Wait for JS to load
                        # Handle cookie consent popup
                        PageMethod('evaluate', '''() => {
                            const cookieBtn = document.querySelector('[data-accept-cookies], .cookie-accept, #accept-cookies');
                            if (cookieBtn) cookieBtn.click();
                        }'''),
                        PageMethod('wait_for_timeout', 1000),
                    ]
                }
            )
    
    def parse_listing_urls(self, response):
        """Extract listing URLs from search results."""
        # City24.lv uses apartment and house links
        apartment_links = response.xpath('//a[contains(@href, "/apartment")]/@href').getall()
        house_links = response.xpath('//a[contains(@href, "/house")]/@href').getall()
        
        all_links = apartment_links + house_links
        
        for link in all_links:
            if link:
                full_url = urljoin(response.url, link)
                yield full_url
    
    def parse(self, response):
        """Parse search results page."""
        listing_urls = list(self.parse_listing_urls(response))
        
        # Process each listing
        for url in listing_urls:
            yield Request(
                url=url,
                callback=self.parse_listing,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'networkidle'),
                        PageMethod('wait_for_timeout', 2000),
                        # Handle cookie consent on listing pages too
                        PageMethod('evaluate', '''() => {
                            const cookieBtn = document.querySelector('[data-accept-cookies], .cookie-accept, #accept-cookies');
                            if (cookieBtn) cookieBtn.click();
                        }'''),
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
                        PageMethod('wait_for_load_state', 'networkidle'),
                        PageMethod('wait_for_timeout', 3000),
                        PageMethod('evaluate', '''() => {
                            const cookieBtn = document.querySelector('[data-accept-cookies], .cookie-accept, #accept-cookies');
                            if (cookieBtn) cookieBtn.click();
                        }'''),
                    ]
                }
            )
    
    def get_next_page_url(self, response):
        """Extract next page URL from pagination."""
        # Look for pagination links
        next_link = response.xpath('//a[contains(@class, "pagination-next") or contains(text(), "Next")]/@href').get()
        
        if next_link:
            return urljoin(response.url, next_link)
        
        # Alternative: look for numbered pagination
        current_page = response.xpath('//span[contains(@class, "pagination-current")]/text()').get()
        if current_page:
            try:
                current = int(current_page)
                next_page_link = response.xpath(f'//a[text()="{current + 1}"]/@href').get()
                if next_page_link:
                    return urljoin(response.url, next_page_link)
            except ValueError:
                pass
        
        return None
    
    def parse_listing(self, response):
        """Parse individual listing from City24.lv."""
        try:
            # Extract listing ID from URL (apartment or house format)
            listing_id_match = re.search(r'/(?:apartment|house)[^/]*/([^/]+)/?$', response.url)
            if not listing_id_match:
                self.log_failure("unknown", "Could not extract listing ID from URL")
                return
            
            listing_id = listing_id_match.group(1)
            
            # Create item
            item = self.create_listing_item(response)
            item['listing_id'] = listing_id
            
            # Extract title
            title = self.extract_text(response, '//h1[@class="property-title" or contains(@class, "title")]/text()')
            if not title:
                title = self.extract_text(response, '//title/text()')
            item['title'] = title
            
            # Extract price
            price_text = self.extract_text(response, '//*[contains(@class, "price") or contains(@class, "cost")]//text()[normalize-space()]')
            if price_text:
                item['price'] = self.parse_price(price_text)
                if '€' in price_text or 'EUR' in price_text:
                    item['price_currency'] = 'EUR'
            
            # Extract area
            area_text = self.extract_text(response, '//*[contains(text(), "m²") or contains(text(), "Area")]/text()')
            if not area_text:
                # Look in property details table
                area_text = self.extract_text(response, '//td[contains(text(), "Area")]/following-sibling::td/text()')
            
            if area_text:
                item['area_sqm'] = self.parse_area(area_text)
            
            # Extract rooms
            rooms_text = self.extract_text(response, '//*[contains(text(), "room") or contains(text(), "Room")]/text()')
            if not rooms_text:
                rooms_text = self.extract_text(response, '//td[contains(text(), "Rooms")]/following-sibling::td/text()')
            
            if rooms_text:
                item['rooms'] = self.parse_rooms_count(rooms_text)
            
            # Extract floor information
            floor_text = self.extract_text(response, '//td[contains(text(), "Floor")]/following-sibling::td/text()')
            if floor_text:
                floor_info = self.parse_floor_info(floor_text)
                if floor_info.get('floor'):
                    item['floor'] = floor_info['floor']
                if floor_info.get('total_floors'):
                    item['total_floors'] = floor_info['total_floors']
            
            # Extract address/location
            address = self.extract_text(response, '//*[contains(@class, "address") or contains(@class, "location")]//text()[normalize-space()]')
            if address:
                item['address'] = address.strip()
                
                # Extract city
                if 'Riga' in address or 'Rīga' in address:
                    item['city'] = 'Riga'
                elif 'Jurmala' in address or 'Jūrmala' in address:
                    item['city'] = 'Jurmala'
            
            # Extract property type from URL or content
            if '/apartments-' in response.url or 'apartment' in (title or '').lower():
                item['property_type'] = 'apartment'
            elif '/houses-' in response.url or 'house' in (title or '').lower():
                item['property_type'] = 'house'
            elif '/land-' in response.url or 'land' in (title or '').lower():
                item['property_type'] = 'land'
            
            # Extract description
            description_elements = response.xpath('//*[contains(@class, "description") or contains(@class, "details")]//text()').getall()
            if description_elements:
                description = ' '.join([text.strip() for text in description_elements if text.strip()])
                item['description'] = description
            
            # Extract images
            image_urls = []
            
            # Look for image galleries or sliders
            img_srcs = response.xpath('//img[contains(@src, "property") or contains(@class, "property-image")]/@src').getall()
            
            # Also check for data attributes commonly used in galleries
            img_data = response.xpath('//img/@data-src | //div/@data-bg | //div/@data-image').getall()
            
            all_images = img_srcs + img_data
            
            for img_url in all_images:
                if img_url and ('jpg' in img_url or 'jpeg' in img_url or 'png' in img_url or 'webp' in img_url):
                    full_img_url = urljoin(response.url, img_url)
                    image_urls.append(full_img_url)
            
            item['image_urls'] = list(set(image_urls))  # Remove duplicates
            
            # Extract features
            features = []
            feature_elements = response.xpath('//*[contains(@class, "feature") or contains(@class, "amenity")]//text()').getall()
            
            for feature_text in feature_elements:
                if feature_text and feature_text.strip():
                    features.append(feature_text.strip())
            
            # Also look for common features in description
            if description:
                feature_keywords = ['balcony', 'parking', 'elevator', 'furnished', 'renovated', 'new building', 'garage']
                for keyword in feature_keywords:
                    if keyword.lower() in description.lower():
                        features.append(keyword)
            
            item['features'] = list(set(features)) if features else []
            
            # Extract posting date
            date_text = self.extract_text(response, '//*[contains(text(), "Added") or contains(text(), "Posted")]/following-sibling::*/text()')
            if date_text:
                item['posted_date'] = self.parse_date(date_text)
            
            # Try to extract coordinates if available
            coords = self.extract_coordinates(response)
            if coords:
                item['latitude'] = coords.get('lat')
                item['longitude'] = coords.get('lng')
            
            # Store raw data for debugging
            item['raw_data'] = {
                'url': response.url,
                'response_length': len(response.text),
                'has_javascript': 'script' in response.text.lower(),
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
        """Parse date from City24.lv format."""
        if not date_text:
            return None
        
        try:
            # Try different date formats
            date_formats = [
                '%d.%m.%Y',
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%d %B %Y',
                '%B %d, %Y',
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
        # Look for common coordinate patterns in JavaScript
        coord_patterns = [
            r'lat["\']?\s*:\s*([0-9.-]+)',
            r'lng["\']?\s*:\s*([0-9.-]+)',
            r'latitude["\']?\s*:\s*([0-9.-]+)',
            r'longitude["\']?\s*:\s*([0-9.-]+)',
        ]
        
        coords = {}
        
        for pattern in coord_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                if 'lat' in pattern.lower():
                    try:
                        coords['lat'] = float(matches[0])
                    except (ValueError, IndexError):
                        pass
                elif 'lng' in pattern.lower() or 'longitude' in pattern.lower():
                    try:
                        coords['lng'] = float(matches[0])
                    except (ValueError, IndexError):
                        pass
        
        return coords if len(coords) == 2 else None