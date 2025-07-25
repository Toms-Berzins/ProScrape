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
        'DOWNLOAD_DELAY': 1.5,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'COOKIES_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
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
            
            # Extract price from options_list table
            price_text = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "Price:")]/following-sibling::td/text()')
            if price_text:
                item['price'] = self.parse_price(price_text)
                # SS.com usually shows prices in EUR
                if 'EUR' in price_text or '€' in price_text:
                    item['price_currency'] = 'EUR'
                elif 'USD' in price_text or '$' in price_text:
                    item['price_currency'] = 'USD'
                else:
                    item['price_currency'] = 'EUR'  # Default to EUR for SS.com
            
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
            # Try different patterns for address
            address = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "Street:")]/following-sibling::td/text()')
            if not address:
                address = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "Address:")]/following-sibling::td/text()')
            
            if address:
                item['address'] = address.strip()
            
            # Extract city and district from options_list table
            city = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "City:")]/following-sibling::td/text()')
            if city:
                item['city'] = city.strip()
            
            district = self.extract_text(response, '//table[@class="options_list"]//td[contains(text(), "District:")]/following-sibling::td/text()')
            if district:
                item['district'] = district.strip()
            
            # Extract property type from URL or content
            if '/flats/' in response.url:
                item['property_type'] = 'apartment'
            elif '/houses/' in response.url:
                item['property_type'] = 'house'
            elif '/land/' in response.url:
                item['property_type'] = 'land'
            
            # Extract description
            description_parts = response.xpath('//div[@id="msg_div_msg"]//text()').getall()
            if description_parts:
                description = ' '.join([part.strip() for part in description_parts if part.strip()])
                item['description'] = description
            
            # Extract images
            image_urls = []
            img_links = response.xpath('//a[contains(@href, ".jpg") or contains(@href, ".jpeg") or contains(@href, ".png")]/@href').getall()
            
            for img_url in img_links:
                full_img_url = urljoin(response.url, img_url)
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
            
            # Extract posting date (if available)
            date_text = self.extract_text(response, '//td[contains(text(), "Date:") or contains(text(), "Added:")]/following-sibling::td/text()')
            if date_text:
                item['posted_date'] = self.parse_date(date_text)
            
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
            # Try different date formats that might be used
            date_formats = [
                '%d.%m.%Y',
                '%d/%m/%Y',
                '%Y-%m-%d',
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