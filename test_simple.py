#!/usr/bin/env python3
"""Simple i18n test using requests instead of aiohttp."""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, params=None, headers=None):
    """Test an endpoint and print results."""
    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", params=params or {}, headers=headers or {}, timeout=10)
        response_time = (time.time() - start_time) * 1000
        
        print(f"OK {endpoint} ({response.status_code}) - {response_time:.1f}ms")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'language' in data:
                    print(f"   Language: {data['language']}")
                if 'message' in data:
                    print(f"   Message: {data['message'][:60]}...")
                if 'items' in data:
                    print(f"   Items: {len(data['items'])}")
                if 'supported_languages' in data:
                    print(f"   Supported: {data['supported_languages']}")
            except:
                print(f"   Response: {response.text[:100]}...")
        else:
            print(f"   Error: {response.text[:100]}...")
            
    except Exception as e:
        print(f"ERROR {endpoint} - Error: {str(e)}")
    
    print()

def main():
    print("ProScrape i18n API Test")
    print("=" * 40)
    
    # Basic health check
    test_endpoint("/health")
    
    # Root endpoint
    test_endpoint("/")
    
    # Language detection tests
    for lang in ["en", "lv", "ru"]:
        test_endpoint("/", params={"lang": lang})
    
    # I18n specific endpoints
    test_endpoint("/api/i18n/languages")
    test_endpoint("/api/i18n/health")
    
    # Test language switching
    for lang in ["en", "lv", "ru"]:
        try:
            response = requests.post(f"{BASE_URL}/api/i18n/switch", params={"language": lang}, timeout=10)
            print(f"Language switch to {lang}: {response.status_code}")
        except Exception as e:
            print(f"Language switch to {lang}: Error - {e}")
    
    print("Test completed!")

if __name__ == "__main__":
    print("Waiting 3 seconds for API...")
    time.sleep(3)
    main()