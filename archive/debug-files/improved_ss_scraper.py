#!/usr/bin/env python3
"""Improved SS.com scraper with proper data extraction."""

import requests
from bs4 import BeautifulSoup
import time
import sys
import re
from datetime import datetime
sys.path.append('.')

from utils.database import async_db
from models.listing import Listing
import asyncio

def extract_ss_listing_data(soup, url):
    """Extract detailed data from SS.com listing page"""
    
    # Extract title from page title (contains price info)
    title_elem = soup.find('title')
    full_title = title_elem.get_text(strip=True) if title_elem else ""
    
    # Clean up title - extract the property description part
    title = "Property listing"
    if "Price" in full_title:
        title_parts = full_title.split("Price")[0].strip()
        if title_parts.startswith("SS.COM"):
            title = title_parts.replace("SS.COM", "").strip(" -")
    
    # Initialize data structure
    listing_data = {
        'listing_id': url.split('/')[-1].replace('.html', ''),
        'title': title,
        'description': None,
        'price': 0.0,
        'price_currency': 'EUR',
        'price_per_sqm': None,
        'source_url': url,
        'source_site': 'ss.com',
        'property_type': 'apartment',
        'area_sqm': 0.0,
        'rooms': 0,
        'floor': None,
        'total_floors': None,
        'address': None,
        'city': 'Riga',
        'district': None,
        'postal_code': None,
        'latitude': None,
        'longitude': None,
        'features': [],
        'amenities': [],
        'image_urls': [],
        'video_urls': [],
        'posted_date': datetime.now(),
        'updated_date': None,
        'scraped_at': datetime.now(),
        'raw_data': None
    }
    
    # Find the main data table (look for tables with structured property info)
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # Get cell text
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                
                # Look for key-value pairs
                for i in range(len(cell_texts) - 1):
                    key = cell_texts[i].lower().strip(':')
                    value = cell_texts[i + 1].strip()
                    
                    if key == 'price' and '€' in value:
                        # Extract price: "54 800 € (1 118.37 €/m²)"
                        price_match = re.search(r'(\d+[\s\d]*)\s*€', value.replace(',', '').replace(' ', ''))
                        if price_match:
                            listing_data['price'] = float(price_match.group(1).replace(' ', ''))
                        
                        # Extract price per sqm
                        per_sqm_match = re.search(r'\(([\d\s.]+)\s*€/m', value)
                        if per_sqm_match:
                            listing_data['price_per_sqm'] = float(per_sqm_match.group(1).replace(' ', ''))
                    
                    elif key == 'area' and 'm' in value:
                        # Extract area: "49 m²"
                        area_match = re.search(r'(\d+(?:\.\d+)?)', value)
                        if area_match:
                            listing_data['area_sqm'] = float(area_match.group(1))
                    
                    elif key == 'rooms':
                        # Extract number of rooms
                        rooms_match = re.search(r'(\d+)', value)
                        if rooms_match:
                            listing_data['rooms'] = int(rooms_match.group(1))
                    
                    elif key == 'city':
                        listing_data['city'] = value
                    
                    elif key == 'district':
                        listing_data['district'] = value
                    
                    elif key == 'street':
                        listing_data['address'] = value.replace('[Map]', '').strip()
                    
                    elif key == 'floor / floors' or key == 'floor':
                        # Extract floor info: "1/9/elevator"
                        floor_match = re.search(r'(\d+)/(\d+)', value)
                        if floor_match:
                            listing_data['floor'] = int(floor_match.group(1))
                            listing_data['total_floors'] = int(floor_match.group(2))
                        
                        # Check for elevator
                        if 'elevator' in value.lower():
                            if 'features' not in listing_data:
                                listing_data['features'] = []
                            if 'elevator' not in listing_data['features']:
                                listing_data['features'].append('elevator')
    
    # Extract description from the main content
    # Look for the main property description (usually in Latvian and English)
    description_candidates = []
    
    # Look for long text blocks that might be descriptions
    all_text = soup.get_text()
    paragraphs = [p.strip() for p in all_text.split('\n') if len(p.strip()) > 50]
    
    for p in paragraphs:
        # Skip navigation and footer text
        if not any(skip_word in p.lower() for skip_word in ['advertisement', 'phone', 'email', 'company', 'back to', 'send to']):
            if any(desc_word in p.lower() for desc_word in ['apartment', 'flat', 'room', 'kitchen', 'bathroom']):
                description_candidates.append(p)
    
    if description_candidates:
        # Use the longest relevant description
        listing_data['description'] = max(description_candidates, key=len)[:500]  # Limit length
    
    # Set property type based on URL and content
    if '/flats/' in url:
        listing_data['property_type'] = 'apartment'
    elif '/houses/' in url:
        listing_data['property_type'] = 'house'
    elif '/land/' in url:
        listing_data['property_type'] = 'land'
    
    return listing_data

def scrape_ss_improved():
    """Improved SS.com scraper"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Test URL
    url = 'https://ss.com/en/real-estate/flats/riga/all/'
    
    print(f"Fetching: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find listing links
        listing_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/msg/' in href and 'real-estate' in href and href.endswith('.html'):
                if href.startswith('/'):
                    href = 'https://ss.com' + href
                listing_links.append(href)
        
        print(f"Found {len(listing_links)} listing links")
        
        # Scrape first few listings with improved extraction
        listings = []
        for i, listing_url in enumerate(listing_links[:5]):  # Limit to 5 for testing
            print(f"\nScraping listing {i+1}: {listing_url}")
            
            try:
                time.sleep(2)  # Be respectful
                listing_response = requests.get(listing_url, headers=headers, timeout=30)
                
                if listing_response.status_code == 200:
                    listing_soup = BeautifulSoup(listing_response.content, 'html.parser')
                    
                    # Extract comprehensive data
                    listing_data = extract_ss_listing_data(listing_soup, listing_url)
                    listings.append(listing_data)
                    
                    # Safe output
                    try:
                        print(f"  Title: {listing_data['title']}")
                        print(f"  Price: €{listing_data['price']:,.0f}")
                        print(f"  Area: {listing_data['area_sqm']} m²")
                        print(f"  Rooms: {listing_data['rooms']}")
                        print(f"  Address: {listing_data['address']}")
                        print(f"  District: {listing_data['district']}")
                    except UnicodeEncodeError:
                        print(f"  Title: {listing_data['title'].encode('ascii', 'ignore').decode('ascii')}")
                        print(f"  Price: €{listing_data['price']:,.0f}")
                        print(f"  Area: {listing_data['area_sqm']} m²")
                        print(f"  Rooms: {listing_data['rooms']}")
                        
                else:
                    print(f"  Failed to fetch listing: {listing_response.status_code}")
                    
            except Exception as e:
                print(f"  Error scraping listing: {e}")
        
        return listings
    else:
        print(f"Failed to fetch main page: {response.status_code}")
        return []

async def save_improved_listings(listings):
    """Save improved listings to MongoDB"""
    if not listings:
        print("No listings to save")
        return
    
    await async_db.connect()
    
    try:
        collection = async_db.database.listings
        
        # Clear old test data first
        delete_result = await collection.delete_many({"source_site": "ss.com"})
        print(f"Deleted {delete_result.deleted_count} old ss.com listings")
        
        for listing in listings:
            try:
                # Validate with Pydantic model
                listing_model = Listing(**listing)
                listing_dict = listing_model.model_dump()
                
                # Convert Decimal fields to float for MongoDB
                for key, value in listing_dict.items():
                    if hasattr(value, 'to_eng_string'):  # Decimal object
                        listing_dict[key] = float(value)
                
                # Insert the listing
                result = await collection.insert_one(listing_dict)
                print(f"Saved listing {listing_dict['listing_id']}: inserted with ID {result.inserted_id}")
                
            except Exception as e:
                print(f"Error validating/saving listing {listing.get('listing_id', 'unknown')}: {e}")
    
    finally:
        await async_db.disconnect()

async def main():
    """Main function"""
    print("=== Improved SS.com Scraper ===")
    
    # Scrape listings with improved extraction
    listings = scrape_ss_improved()
    
    if listings:
        print(f"\nExtracted {len(listings)} listings with complete data")
        
        # Save to MongoDB
        await save_improved_listings(listings)
        
        print("\n=== Improved scraping completed! ===")
    else:
        print("No listings found")

if __name__ == '__main__':
    asyncio.run(main())