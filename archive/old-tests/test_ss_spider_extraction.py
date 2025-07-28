#!/usr/bin/env python3
"""
Test script to verify SS spider coordinate and image extraction fixes.
Tests specific URLs without going through the full Scrapy pipeline.
"""

import requests
import re
from urllib.parse import urljoin, unquote
import sys
import json
from datetime import datetime

class SSSpiderTester:
    """Minimal tester for SS spider extraction logic."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_page(self, url):
        """Fetch page content."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_images(self, response):
        """Extract image URLs using the same logic as SS spider."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(response.text, 'html.parser')
        image_urls = []
        
        # Primary: Get gallery images (high quality)
        gallery_links = []
        
        # Find all links that contain 'gallery' and image extensions
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'gallery' in href and any(ext in href for ext in ['.jpg', '.jpeg', '.png']):
                gallery_links.append(href)
        
        # Secondary: Get any other listing images if no gallery found
        if not gallery_links:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if any(ext in href for ext in ['.jpg', '.jpeg', '.png']):
                    # Filter out common ad/icon images
                    if not any(exclude in href.lower() for exclude in ['icon', 'logo', 'ad', 'banner', 'btn', 'button']):
                        gallery_links.append(href)
        
        for img_url in gallery_links:
            if img_url:
                full_img_url = urljoin(response.url, img_url)
                # Avoid duplicates
                if full_img_url not in image_urls:
                    image_urls.append(full_img_url)
        
        return image_urls
    
    def extract_coordinates_from_map_link(self, map_link):
        """Extract latitude and longitude from SS.com map link."""
        if not map_link:
            return None
        
        try:
            # URL decode the link to handle %20 (space) encoding
            decoded_link = unquote(map_link)
            
            # Look for c= parameter with coordinates
            coord_pattern = r'c=([0-9.]+),\s*([0-9.]+)(?:,\s*[0-9.]+)?'
            coord_match = re.search(coord_pattern, decoded_link)
            
            if coord_match:
                latitude = float(coord_match.group(1))
                longitude = float(coord_match.group(2))
                
                # Validate coordinates are reasonable for Latvia
                if 55.0 <= latitude <= 58.5 and 20.0 <= longitude <= 29.0:
                    return {
                        'latitude': latitude,
                        'longitude': longitude,
                        'source': 'map_link_c_param'
                    }
            
            # Try alternative patterns
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
                        return {
                            'latitude': latitude,
                            'longitude': longitude,
                            'source': f'map_link_alt_pattern'
                        }
                        
        except Exception as e:
            print(f"Error extracting coordinates from map link '{map_link}': {e}")
        
        return None
    
    def extract_coordinates_from_page(self, response):
        """Extract latitude and longitude from SS.com page content."""
        try:
            page_text = response.text
            
            # Look for coordinate patterns in the HTML
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
                            'longitude': longitude,
                            'source': 'page_content_decimal'
                        }
                        
            # Look for coords array format: coords = [lat, lng]
            coords_array_pattern = r'coords?\s*=\s*\[([0-9.]+),\s*([0-9.]+)\]'
            coords_match = re.search(coords_array_pattern, page_text)
            if coords_match:
                latitude = float(coords_match.group(1))
                longitude = float(coords_match.group(2))
                
                if 55.0 <= latitude <= 58.0 and 20.0 <= longitude <= 29.0:
                    return {
                        'latitude': latitude,
                        'longitude': longitude,
                        'source': 'page_content_array'
                    }
                    
        except Exception as e:
            print(f"Error extracting coordinates from page: {e}")
        
        return None
    
    def extract_coordinates(self, response):
        """Extract coordinates using both map links and page content."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for gmap links with coordinates in the URL
        gmap_links = []
        
        # Find all links containing 'gmap'
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'gmap' in href:
                gmap_links.append(href)
        
        # Also look for gmap links in onclick handlers (JavaScript)
        for element in soup.find_all(attrs={'onclick': True}):
            onclick = element.get('onclick', '')
            if 'gmap' in onclick:
                # Extract the gmap URL from the onclick JavaScript
                gmap_match = re.search(r"'([^']*gmap[^']*)'", onclick)
                if gmap_match:
                    gmap_links.append(gmap_match.group(1))
        
        # Try to extract coordinates from each gmap link
        for gmap_link in gmap_links:
            if gmap_link:
                coords = self.extract_coordinates_from_map_link(gmap_link)
                if coords:
                    coords['map_link'] = gmap_link
                    return coords
        
        # Fallback: Extract coordinates from page content
        coords = self.extract_coordinates_from_page(response)
        if coords:
            return coords
        
        return None
    
    def test_url(self, url):
        """Test extraction for a specific URL."""
        print(f"\n{'='*80}")
        print(f"Testing URL: {url}")
        print(f"{'='*80}")
        
        # Fetch the page
        response = self.get_page(url)
        if not response:
            print("Failed to fetch page")
            return None
        
        print(f"Page fetched successfully. Content length: {len(response.text)} chars")
        
        # Extract listing ID
        listing_id_match = re.search(r'/msg/.*/([^/]+)\.html', url)
        listing_id = listing_id_match.group(1) if listing_id_match else 'unknown'
        print(f"Listing ID: {listing_id}")
        
        # Test image extraction
        print(f"\n{'-'*40}")
        print("IMAGE EXTRACTION TEST")
        print(f"{'-'*40}")
        
        images = self.extract_images(response)
        print(f"Found {len(images)} images:")
        for i, img_url in enumerate(images, 1):
            print(f"  {i}. {img_url}")
        
        # Test coordinate extraction
        print(f"\n{'-'*40}")
        print("COORDINATE EXTRACTION TEST")
        print(f"{'-'*40}")
        
        coords = self.extract_coordinates(response)
        if coords:
            print(f"Coordinates found:")
            print(f"  Latitude: {coords['latitude']}")
            print(f"  Longitude: {coords['longitude']}")
            print(f"  Source: {coords['source']}")
            if 'map_link' in coords:
                print(f"  Map Link: {coords['map_link']}")
        else:
            print("No coordinates found")
        
        # Return summary
        return {
            'url': url,
            'listing_id': listing_id,
            'images_count': len(images),
            'images': images,
            'coordinates': coords,
            'has_coordinates': coords is not None,
            'has_images': len(images) > 0
        }

def main():
    """Main testing function."""
    print("SS Spider Extraction Tester")
    print("Testing coordinate and image extraction fixes")
    
    # Test URLs provided
    test_urls = [
        'https://ss.com/msg/en/real-estate/flats/riga/centre/dbjgj.html',
        'https://ss.com/msg/en/real-estate/flats/riga/imanta/hcbll.html'
    ]
    
    tester = SSSpiderTester()
    results = []
    
    for url in test_urls:
        try:
            result = tester.test_url(url)
            if result:
                results.append(result)
        except Exception as e:
            print(f"Error testing {url}: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    print(f"Tested {len(results)} URLs")
    
    urls_with_images = sum(1 for r in results if r['has_images'])
    urls_with_coords = sum(1 for r in results if r['has_coordinates'])
    
    print(f"URLs with images: {urls_with_images}/{len(results)}")
    print(f"URLs with coordinates: {urls_with_coords}/{len(results)}")
    
    # Detailed results
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['listing_id']}:")
        print(f"   Images: {result['images_count']} found")
        print(f"   Coordinates: {'Yes' if result['has_coordinates'] else 'No'}")
        if result['has_coordinates']:
            coords = result['coordinates']
            print(f"   - Lat/Lng: {coords['latitude']}, {coords['longitude']}")
            print(f"   - Source: {coords['source']}")
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"C:\\Users\\berzi\\ProScrape\\test_results_{timestamp}.json"
    
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nDetailed results saved to: {results_file}")
    except Exception as e:
        print(f"Error saving results: {e}")
    
    # Return success status
    all_working = all(r['has_images'] and r['has_coordinates'] for r in results)
    print(f"\nExtraction fixes status: {'SUCCESS' if all_working else 'PARTIAL/FAILED'}")
    
    return results

if __name__ == '__main__':
    main()