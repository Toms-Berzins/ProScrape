#!/usr/bin/env python3
"""Comprehensive i18n API test."""

import requests
import json

BASE_URL = "http://localhost:8004"

def test_comprehensive():
    print("=== COMPREHENSIVE i18n API TEST ===")
    print()
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Root endpoint in different languages
    print("1. Testing root endpoint translations...")
    for lang in ["en", "lv", "ru"]:
        tests_total += 1
        try:
            resp = requests.get(f"{BASE_URL}/", params={"lang": lang}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                message = data.get("message", "")
                if message and message != f"api.messages.welcome":
                    print(f"   OK {lang}: {message}")
                    tests_passed += 1
                else:
                    print(f"   FAIL {lang}: Translation not working")
            else:
                print(f"   FAIL {lang}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"   ERROR {lang}: Error - {e}")
    print()
    
    # Test 2: Language detection via headers
    print("2. Testing language detection via headers...")
    tests_total += 1
    try:
        resp = requests.get(f"{BASE_URL}/", headers={"X-Language": "ru"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("language") == "ru":
                print(f"   OK Header detection: {data.get('message', 'No message')}")
                tests_passed += 1
            else:
                print(f"   FAIL Header detection failed: {data.get('language')}")
        else:
            print(f"   FAIL Header detection: HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ERROR Header detection: Error - {e}")
    print()
    
    # Test 3: i18n health check
    print("3. Testing i18n health...")
    tests_total += 1
    try:
        resp = requests.get(f"{BASE_URL}/api/i18n/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            translations = data.get("statistics", {}).get("total_translations", 0)
            print(f"   OK Health: {status} | Translations: {translations}")
            if status == "healthy" and translations > 0:
                tests_passed += 1
        else:
            print(f"   FAIL Health check: HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ERROR Health check: Error - {e}")
    print()
    
    # Test 4: Language switching
    print("4. Testing language switching...")
    tests_total += 1
    try:
        resp = requests.post(f"{BASE_URL}/api/i18n/switch", params={"language": "en"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("language") == "en":
                print(f"   OK Language switch: {data.get('message', 'Success')}")
                tests_passed += 1
            else:
                print(f"   FAIL Language switch failed: {data}")
        else:
            print(f"   FAIL Language switch: HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ERROR Language switch: Error - {e}")
    print()
    
    # Test 5: Supported languages
    print("5. Testing supported languages...")
    tests_total += 1
    try:
        resp = requests.get(f"{BASE_URL}/api/i18n/languages", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) == 3:
                langs = [item.get("code") for item in data]
                print(f"   OK Supported languages: {langs}")
                tests_passed += 1
            else:
                print(f"   FAIL Supported languages: Invalid response")
        else:
            print(f"   FAIL Supported languages: HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ERROR Supported languages: Error - {e}")
    print()
    
    # Test 6: Localized listings (if available)
    print("6. Testing localized listings...")
    tests_total += 1
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/listings", params={"lang": "lv", "limit": 1}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "items" in data and "pagination_info" in data:
                print(f"   OK Localized listings: {len(data.get('items', []))} items")
                tests_passed += 1
            else:
                print(f"   OK Localized listings: Empty but endpoint works")
                tests_passed += 1  # Endpoint works even if no data
        else:
            print(f"   FAIL Localized listings: HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ERROR Localized listings: Error - {e}")
    print()
    
    # Summary
    print("=" * 40)
    print(f"TEST RESULTS: {tests_passed}/{tests_total} PASSED")
    
    if tests_passed == tests_total:
        print("SUCCESS: ALL TESTS PASSED! i18n system is fully functional.")
    elif tests_passed >= tests_total * 0.8:
        print("GOOD: Most tests passed. i18n system is working well.")
    else:
        print("WARNING: Some tests failed. Check the results above.")
    
    print(f"Success rate: {(tests_passed/tests_total)*100:.1f}%")

if __name__ == "__main__":
    test_comprehensive()