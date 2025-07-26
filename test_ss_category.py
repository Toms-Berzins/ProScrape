#!/usr/bin/env python3
"""Test specific SS.com category pages."""

import requests
from bs4 import BeautifulSoup

def test_ss_category():
    """Test SS.com specific category page"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Try more specific category
    urls_to_test = [
        'https://ss.com/en/real-estate/flats/riga/all/',
        'https://ss.com/en/real-estate/flats/riga/centre/',
        'https://ss.com/msg/en/real-estate/flats/riga/all/',
    ]
    
    for url in urls_to_test:
        print(f"\n=== Testing: {url} ===")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for links that end with .html
                html_links = [link['href'] for link in soup.find_all('a', href=True) 
                             if link['href'].endswith('.html')]
                print(f"HTML links found: {len(html_links)}")
                
                # Look for links with specific patterns
                id_links = [link['href'] for link in soup.find_all('a', href=True) 
                           if any(char.isupper() for char in link['href']) and 
                           any(char.islower() for char in link['href']) and
                           any(char.isdigit() for char in link['href'])]
                print(f"ID-pattern links found: {len(id_links)}")
                
                if html_links:
                    print("Sample HTML links:")
                    for link in html_links[:5]:
                        print(f"  {link}")
                
                if id_links:
                    print("Sample ID-pattern links:")
                    for link in id_links[:5]:
                        print(f"  {link}")
                
                # Look for table with ads
                ad_table = soup.find('table', {'id': 'page_main'}) or soup.find('table', class_='list_table')
                if ad_table:
                    print("Found potential ads table!")
                    rows = ad_table.find_all('tr')
                    print(f"Table has {len(rows)} rows")
                    
                    for i, row in enumerate(rows[1:6]):  # Skip header, check first 5
                        cells = row.find_all('td')
                        if len(cells) > 2:  # Should have multiple columns
                            links = row.find_all('a', href=True)
                            if links:
                                main_link = links[0]['href']
                                text = links[0].get_text(strip=True)
                                print(f"  Row {i+2}: {main_link} -> {text[:50]}")
                
        except Exception as e:
            print(f"Error fetching {url}: {e}")

if __name__ == '__main__':
    test_ss_category()