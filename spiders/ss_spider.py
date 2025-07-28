import re
from datetime import datetime
from urllib.parse import urljoin
from scrapy import Request
from spiders.base_spider import BaseRealEstateSpider
from spiders.items import ListingItem


class SSSpider(BaseRealEstateSpider):
    """Spider for scraping ss.com real estate listings (static HTML)."""
    
    name = 'ss_spider'
    allowed_domains = ['ss.com']
    
    # Start URLs for different property types
    start_urls = [
        'https://ss.com/en/real-estate/flats/riga/',
        'https://ss.com/en/real-estate/flats/jurmala/',
        'https://ss.com/en/real-estate/flats/liepaja/',
        'https://ss.com/en/real-estate/houses/riga/',
        'https://ss.com/en/real-estate/houses/jurmala/',
        'https://ss.com/en/real-estate/land/riga/',
    ]
    
    custom_settings = {
        # Production rate limiting - conservative to avoid blocking
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'AUTOTHROTTLE_DEBUG': True,
        
        # Enhanced cookie and session handling
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': False,
        
        # Disable Playwright for SS spider (static HTML only)
        'DOWNLOAD_HANDLERS': {
            'https': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
            'http': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
        },
        
        # Production middleware stack with all anti-detection measures
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'spiders.middlewares.EnhancedUserAgentMiddleware': 400,
            'spiders.middlewares.EnhancedProxyMiddleware': 410,
            'spiders.middlewares.EnhancedRetryMiddleware': 420,
            # Disable Playwright middleware
            'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler': None,
        },
        
        # Production pipeline with full data processing
        'ITEM_PIPELINES': {
            'spiders.pipelines.ValidationPipeline': 300,
            'spiders.pipelines.NormalizationPipeline': 350,
            'spiders.pipelines.DuplicatesPipeline': 400,
            'spiders.pipelines.MongoPipeline': 500,
        },
        
        # Enhanced headers for better stealth
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        },
        
        # Production logging and monitoring
        'LOG_LEVEL': 'INFO',
        'STATS_CLASS': 'scrapy.statscollectors.MemoryStatsCollector',
        
        # Error handling and retries
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        
        # Timeouts
        'DOWNLOAD_TIMEOUT': 30,
    }
    
    def parse(self, response):
        """Parse category pages and extract listing URLs."""
        self.logger.info(f"Parsing category page: {response.url}")
        
        # Extract listing URLs from the current page
        listing_links = response.xpath('//a[contains(@href, "/msg/")]/@href').getall()
        
        self.logger.info(f"Found {len(listing_links)} listing links on {response.url}")
        
        for link in listing_links:
            if link and '/msg/' in link and 'real-estate' in link:
                full_url = urljoin(response.url, link)
                yield Request(full_url, callback=self.parse_listing)
        
        # Look for next page pagination
        next_page = response.xpath('//a[contains(text(), "next") or contains(text(), "Next") or contains(text(), ">")]/@href').get()
        
        if next_page:
            next_url = urljoin(response.url, next_page)
            self.logger.info(f"Following next page: {next_url}")
            yield Request(next_url, callback=self.parse)
    
    def parse_listing_urls(self, response):
        """Extract listing URLs from category pages."""
        # SS.com uses /msg/ links for individual listings
        listing_links = response.xpath('//a[contains(@href, "/msg/")]/@href').getall()
        
        for link in listing_links:
            if link and '/msg/' in link and 'real-estate' in link:
                full_url = urljoin(response.url, link)
                yield full_url
    
    def get_next_page_url(self, response):
        """Extract next page URL for pagination."""
        # Look for pagination links
        next_page = response.xpath('//a[contains(text(), "next") or contains(text(), "Next") or contains(text(), ">")]/@href').get()
        
        if next_page:
            return urljoin(response.url, next_page)
        
        return None
    
    def parse_listing(self, response):
        """Parse individual listing from SS.com."""
        try:
            # Extract listing ID from URL (/msg/ format)
            listing_id_match = re.search(r'/msg/.*/([^/]+)\.html', response.url)
            if not listing_id_match:
                self.log_failure("unknown", "Could not extract listing ID from URL")
                return
            
            listing_id = listing_id_match.group(1)
            
            # Create item
            item = self.create_listing_item(response)
            item['listing_id'] = listing_id
            
            # Extract title
            title = self.extract_text(response, '//h1[@id="msg_div_msg"]/text()')
            if not title:
                title = self.extract_text(response, '//title/text()')
            item['title'] = title
            
            # Extract main content table
            main_table = response.xpath('//table[@id="page_main"]')
            
            if not main_table:
                self.log_failure(listing_id, "Could not find main content table")
                return
            
            # Extract price - SS.com puts price in title and header, not options_list table
            price_text = None
            
            # Try extracting from page title first
            title_text = self.extract_text(response, '//title/text()')
            if title_text and ('EUR' in title_text or '€' in title_text or '/mon' in title_text):
                price_text = title_text
            
            # Try extracting from h1 header if not found in title
            if not price_text:
                h1_text = self.extract_text(response, '//h1[@id="msg_div_msg"]/text()')
                if h1_text and ('EUR' in h1_text or '€' in h1_text or '/mon' in h1_text):
                    price_text = h1_text
            
            # Try extracting from any text containing price and currency
            if not price_text:
                price_text = self.extract_text(response, '//text()[contains(., "EUR") or contains(., "€")][contains(., "/mon") or contains(translate(., "PRICE", "price"), "price")]')
            
            if price_text:
                item['price'] = self.parse_price(price_text)
                # SS.com shows prices in EUR
                item['price_currency'] = 'EUR'
            
            # Extract area from options_list table
            area_text = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "Area:")]/following-sibling::td/text()')
            if area_text:
                item['area_sqm'] = self.parse_area(area_text)
            
            # Extract rooms from options_list table
            rooms_text = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "Rooms:") or contains(text(), "Istabas:")]/following-sibling::td/text()')
            if rooms_text:
                item['rooms'] = self.parse_rooms_count(rooms_text)
            
            # Extract floor information from options_list table
            floor_text = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "Floor") or contains(text(), "floors")]/following-sibling::td/text()')
            if floor_text:
                floor_info = self.parse_floor_info(floor_text)
                if floor_info.get('floor'):
                    item['floor'] = floor_info['floor']
                if floor_info.get('total_floors'):
                    item['total_floors'] = floor_info['total_floors']
            
            # Extract address/location from options_list table
            # Use normalize-space to handle whitespace issues
            address = self.extract_text(response, 'normalize-space(//table[@class="options_list"]//td[contains(text(), "Street:")]/following-sibling::td)')
            if not address:
                address = self.extract_text(response, 'normalize-space(//table[@class="options_list"]//td[contains(text(), "Address:")]/following-sibling::td)')
            
            # Clean up address by removing [Map] link text
            if address:
                address = address.replace('[', '').replace('Map', '').replace(']', '').strip()
                item['address'] = address
            
            # Extract city and district from options_list table
            city = self.extract_text(response, 'normalize-space(//table[@class="options_list"]//td[contains(text(), "City:")]/following-sibling::td)')
            if city:
                item['city'] = city.strip()
            
            district = self.extract_text(response, 'normalize-space(//table[@class="options_list"]//td[contains(text(), "District:")]/following-sibling::td)')
            if district:
                item['district'] = district.strip()
            
            # Extract property type from URL or content
            if '/flats/' in response.url:
                item['property_type'] = 'apartment'
            elif '/houses/' in response.url:
                item['property_type'] = 'house'
            elif '/land/' in response.url:
                item['property_type'] = 'land'
            
            # Extract listing type (sell/rent) from price text and content
            listing_type = self.determine_listing_type(response, price_text)
            item['listing_type'] = listing_type
            
            # Extract description - focus on actual description paragraphs
            # Look for the main description text, avoiding navigation and footer elements
            description_parts = []
            
            # Method 1: Extract paragraphs from msg_div_msg that contain substantial text
            # First, get all text nodes from the main div
            all_text_nodes = response.xpath('//div[@id="msg_div_msg"]//text()').getall()
            
            # Filter to get meaningful description text
            for text in all_text_nodes:
                text = text.strip()
                # Include text that is substantial (>20 chars) and looks like description content
                if (text and len(text) > 20 and 
                    not text.startswith('window.') and 
                    not text.startswith('var ') and
                    not text.startswith('function') and
                    'Date:' not in text and
                    'Price:' not in text and
                    'City:' not in text and
                    'District:' not in text and
                    not text.startswith('LINK_MAIN_HOST')):
                    description_parts.append(text)
            
            # Join the filtered parts with proper spacing
            if description_parts:
                # Take only the first 2-3 meaningful paragraphs (description usually comes first)
                description = ' '.join(description_parts[:3]).strip()
                
                # Clean up the description
                # Remove extra whitespace and normalize  
                description = re.sub(r'\s+', ' ', description)
                
                # Remove any remaining technical artifacts
                description = re.sub(r'(?:print_phone|show_banner|eval)\([^)]*\)', '', description)
                description = re.sub(r'var\s+\w+\s*=.*?;', '', description)
                
                item['description'] = description.strip()
            else:
                item['description'] = None
            
            # Extract images - focus on gallery images to avoid ads/icons
            image_urls = []
            
            # Get gallery images from JPG links (SS.com specific pattern)
            gallery_links = response.xpath('//a[contains(@href, "jpg")]/@href').getall()
            
            # Filter to high quality gallery images only
            gallery_links = [link for link in gallery_links if 'gallery' in link and link.startswith('http')]
            
            for img_url in gallery_links:
                if img_url:
                    full_img_url = urljoin(response.url, img_url)
                    # Avoid duplicates
                    if full_img_url not in image_urls:
                        image_urls.append(full_img_url)
            
            item['image_urls'] = image_urls
            
            # Extract features from the listing text
            features = []
            feature_keywords = ['balcony', 'parking', 'elevator', 'furnished', 'renovated', 'new building']
            
            full_text = (title or '') + ' ' + (description or '')
            for keyword in feature_keywords:
                if keyword.lower() in full_text.lower():
                    features.append(keyword)
            
            item['features'] = features
            
            # Extract posting date from SS.com footer
            # SS.com shows date in format: "Date: 26.07.2025 18:48"
            date_text = self.extract_text(response, '//text()[contains(., "Date:")][contains(., "2025") or contains(., "2024") or contains(., "2026")]')
            
            if date_text:
                # Extract date from "Date: 26.07.2025 18:48" format
                date_match = re.search(r'Date:\s*(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})', date_text)
                if date_match:
                    clean_date = date_match.group(1)
                    parsed_date = self.parse_date(clean_date)
                    if parsed_date:
                        item['posted_date'] = parsed_date
                    else:
                        # Fallback: try with just the date part
                        date_only_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', clean_date)
                        if date_only_match:
                            item['posted_date'] = self.parse_date(date_only_match.group(1))
            
            # If no posted_date found, leave it None (don't set to scraped_at)
            
            # Extract coordinates from map links (primary method)
            coords = None
            
            # Look for gmap links with coordinates in the URL
            gmap_links = response.xpath('//a[contains(@href, "gmap")]/@href').getall()
            
            # Also look for gmap links in onclick handlers (JavaScript)
            onclick_links = response.xpath('//a[contains(@onclick, "gmap")]/@onclick').getall()
            for onclick in onclick_links:
                # Extract the gmap URL from the onclick JavaScript
                gmap_match = re.search(r"'([^']*gmap[^']*)'", onclick)
                if gmap_match:
                    gmap_links.append(gmap_match.group(1))
            
            for gmap_link in gmap_links:
                if gmap_link:
                    coords = self.extract_coordinates_from_map_link(gmap_link)
                    if coords:
                        break
            
            # Fallback: Extract coordinates from page content
            if not coords:
                coords = self.extract_coordinates_from_page(response)
            
            # Store coordinates
            if coords:
                item['latitude'] = coords['latitude']
                item['longitude'] = coords['longitude']
            else:
                item['latitude'] = None
                item['longitude'] = None
            
            # Store map link for reference
            map_link = None
            
            # First try to get direct gmap href
            map_link = response.xpath('//a[contains(@href, "gmap")]/@href').get()
            
            # If not found, extract from onclick handlers
            if not map_link:
                onclick_links = response.xpath('//a[contains(@onclick, "gmap")]/@onclick').getall()
                for onclick in onclick_links:
                    gmap_match = re.search(r"'([^']*gmap[^']*)'", onclick)
                    if gmap_match:
                        map_link = gmap_match.group(1)
                        break
            
            # Store the map link if found
            if map_link and map_link != 'javascript:;':
                # Convert relative URLs to absolute URLs
                if map_link.startswith('/'):
                    map_link = urljoin('https://www.ss.com', map_link)
                item['map_link'] = map_link
            
            # Store address components for potential geocoding fallback
            full_address_parts = []
            if item.get('address'):
                full_address_parts.append(item['address'])
            if item.get('district'):
                full_address_parts.append(item['district'])
            if item.get('city'):
                full_address_parts.append(item['city'])
            
            if full_address_parts:
                item['full_address'] = ', '.join(full_address_parts)
            
            # Store raw data for debugging
            item['raw_data'] = {
                'url': response.url,
                'response_length': len(response.text),
                'main_table_found': bool(main_table),
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
        """Parse floor information like '3/5' or '3rd floor of 5'."""
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
        """Parse date from SS.com format."""
        if not date_text:
            return None
        
        try:
            # Clean the date text
            clean_date = date_text.strip()
            
            # Try different date formats that might be used by SS.com
            date_formats = [
                '%d.%m.%Y %H:%M',  # SS.com format: "26.07.2025 18:48"
                '%d.%m.%Y',        # Date only: "26.07.2025"
                '%d/%m/%Y',        # Alternative format
                '%Y-%m-%d',        # ISO format
                '%d.%m.%Y %H:%M:%S',  # With seconds
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(clean_date, fmt)
                    return parsed_date
                except ValueError:
                    continue
            
            # If no format matches, try parsing just the date part
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', clean_date)
            if date_match:
                try:
                    return datetime.strptime(date_match.group(1), '%d.%m.%Y')
                except ValueError:
                    pass
            
        except Exception as e:
            # Use a simple print for now since logger might not be available
            print(f"Could not parse date '{date_text}': {e}")
        
        return None
    
    def extract_coordinates_from_page(self, response):
        """Extract latitude and longitude from SS.com page content."""
        try:
            # SS.com embeds coordinates in the page source in various formats
            page_text = response.text
            
            # Look for coordinate patterns in the HTML
            # Pattern: two decimal numbers with 2+ digits before decimal, separated by comma and optional space
            coord_pattern = r'(\d{2}\.\d+),\s*(\d{2}\.\d+)'
            matches = re.findall(coord_pattern, page_text)
            
            if matches:
                # Take the first match and validate it's in Latvia bounds
                for match in matches:
                    latitude = float(match[0])
                    longitude = float(match[1])
                    
                    # Validate coordinates are reasonable for Latvia
                    if 55.0 <= latitude <= 58.0 and 20.0 <= longitude <= 29.0:
                        return {
                            'latitude': latitude,
                            'longitude': longitude
                        }
                        
            # If no valid coordinates found in decimal format, try other patterns
            # Look for coords array format: coords = [lat, lng]
            coords_array_pattern = r'coords?\s*=\s*\[([0-9.]+),\s*([0-9.]+)\]'
            coords_match = re.search(coords_array_pattern, page_text)
            if coords_match:
                latitude = float(coords_match.group(1))
                longitude = float(coords_match.group(2))
                
                if 55.0 <= latitude <= 58.0 and 20.0 <= longitude <= 29.0:
                    return {
                        'latitude': latitude,
                        'longitude': longitude
                    }
                    
        except Exception as e:
            self.logger.warning(f"Error extracting coordinates from page: {e}")
        
        return None
    
    def determine_listing_type(self, response, price_text):
        """Determine if listing is for sale or rent based on price indicators."""
        try:
            # Check price text for rental indicators
            if price_text:
                price_lower = price_text.lower()
                # Common rental indicators in English and Latvian
                rent_indicators = [
                    '/mon', '/month', 'per month', 'monthly',
                    'mēnesī', 'mēn', '/mēn',
                    'rent', 'rental', 'īre', 'noma'
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
            
            # Check URL patterns (SS.com might have different sections)
            url_lower = response.url.lower()
            if any(keyword in url_lower for keyword in ['rent', 'rental', 'īre', 'noma']):
                return 'rent'
            
            if any(keyword in url_lower for keyword in ['sale', 'sell', 'pārdod', 'pārdošana']):
                return 'sell'
            
            # Default assumption: if no rental indicators found, it's likely for sale
            # This is based on SS.com typically showing sales listings more prominently
            return 'sell'
            
        except Exception as e:
            self.logger.warning(f"Error determining listing type: {e}")
            return None
    
    def extract_coordinates_from_map_link(self, map_link):
        """Extract latitude and longitude from SS.com map link.
        
        Expected format: https://www.ss.com/en/gmap/fTgTeF4QAzt4FD4eFFM=.html?mode=1&c=56.9619537,%2024.1227746,%2014
        Where 56.9619537 and 24.1227746 are the latitude and longitude coordinates.
        """
        if not map_link:
            return None
        
        try:
            # First, URL decode the link to handle %20 (space) encoding
            from urllib.parse import unquote
            decoded_link = unquote(map_link)
            
            # Look for c= parameter with coordinates
            # Pattern: c=latitude,longitude,zoom
            # The coordinates are separated by comma, and zoom is optional
            coord_pattern = r'c=([0-9.]+),\s*([0-9.]+)(?:,\s*[0-9.]+)?'
            coord_match = re.search(coord_pattern, decoded_link)
            
            if coord_match:
                latitude = float(coord_match.group(1))
                longitude = float(coord_match.group(2))
                
                # Validate coordinates are reasonable for Latvia
                # Latvia bounds: roughly 55.67-58.08 N, 20.97-28.24 E
                if 55.0 <= latitude <= 58.5 and 20.0 <= longitude <= 29.0:
                    self.logger.info(f"Extracted coordinates from map link: {latitude}, {longitude}")
                    return {
                        'latitude': latitude,
                        'longitude': longitude
                    }
                else:
                    self.logger.warning(f"Coordinates out of Latvia bounds: {latitude}, {longitude}")
                    
            # If no c= parameter found, try alternative patterns
            # Some links might use different parameter names
            alt_patterns = [
                r'lat=([0-9.]+).*?lng=([0-9.]+)',
                r'latitude=([0-9.]+).*?longitude=([0-9.]+)',
                r'coords?=([0-9.]+),\s*([0-9.]+)'
            ]
            
            for pattern in alt_patterns:
                alt_match = re.search(pattern, decoded_link)
                if alt_match:
                    latitude = float(alt_match.group(1))
                    longitude = float(alt_match.group(2))
                    
                    if 55.0 <= latitude <= 58.5 and 20.0 <= longitude <= 29.0:
                        self.logger.info(f"Extracted coordinates from map link (alt pattern): {latitude}, {longitude}")
                        return {
                            'latitude': latitude,
                            'longitude': longitude
                        }
                    
        except Exception as e:
            self.logger.warning(f"Error extracting coordinates from map link '{map_link}': {e}")
        
        return None