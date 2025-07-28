#!/usr/bin/env python3
"""
Test script for ProScrape i18n API implementation.
Tests the main i18n endpoints and functionality.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.translation_manager import translation_manager
from utils.i18n import SupportedLanguage, set_current_language
from models.i18n_models import LocalizedListingResponse, LanguageInfo

async def test_translation_manager():
    """Test the translation manager initialization and basic functionality."""
    print("=== Testing Translation Manager ===")
    
    try:
        # Initialize translation manager
        await translation_manager.initialize()
        print("✓ Translation manager initialized successfully")
        
        # Test getting translations
        for lang in SupportedLanguage:
            set_current_language(lang.value)
            welcome_msg = translation_manager.get_translation(
                "api.messages.welcome",
                lang.value,
                fallback="Welcome to ProScrape API"
            )
            print(f"✓ {lang.value}: {welcome_msg}")
        
        # Test translation statistics
        stats = translation_manager.get_statistics()
        print(f"✓ Translation statistics: {stats['total_translations']} total translations")
        
        # Test health check
        health = translation_manager.health_check()
        print(f"✓ Translation health: {health['status']}")
        
    except Exception as e:
        print(f"✗ Translation manager test failed: {e}")
        return False
    
    return True


def test_i18n_models():
    """Test the i18n Pydantic models."""
    print("\n=== Testing I18n Models ===")
    
    try:
        # Test LanguageInfo model
        lang_info = LanguageInfo(
            code="en",
            name="English",
            name_en="English",
            name_local="English",
            is_default=False,
            is_current=True
        )
        print(f"✓ LanguageInfo model created: {lang_info.code}")
        
        # Test display_info computed field
        display_info = lang_info.display_info
        print(f"✓ Display info computed: {display_info['code']}")
        
        # Mock listing data for LocalizedListingResponse
        mock_listing_data = {
            "id": "test123",
            "listing_id": "test123",
            "title": "Test Apartment",
            "description": "A nice test apartment",
            "price": 50000.0,
            "area_sqm": 65.5,
            "property_type": "apartment",
            "listing_type": "sell",
            "city": "Riga",
            "district": "Centrs",
            "address": "Test Street 123",
            "source_site": "test.com",
            "url": "https://test.com/listing/123",
            "rooms": 2,
            "floor": 3,
            "posted_date": None,
            "scraped_at": None,
            "image_urls": [],
            "features": [],
            "latitude": None,
            "longitude": None
        }
        
        # Set language context
        set_current_language("en")
        
        # Test LocalizedListingResponse
        localized_listing = LocalizedListingResponse(**mock_listing_data)
        print(f"✓ LocalizedListingResponse created: {localized_listing.title}")
        
        # Test computed fields
        display_title = localized_listing.display_title
        display_price = localized_listing.display_price
        display_area = localized_listing.display_area
        display_location = localized_listing.display_location
        
        print(f"✓ Display fields computed:")
        print(f"  - Title: {display_title}")
        print(f"  - Price: {display_price}")
        print(f"  - Area: {display_area}")
        print(f"  - Location: {display_location}")
        
    except Exception as e:
        print(f"✗ I18n models test failed: {e}")
        return False
    
    return True


def test_language_detection():
    """Test language detection functionality."""
    print("\n=== Testing Language Detection ===")
    
    try:
        from utils.i18n import LanguageDetector
        
        # Test Accept-Language header detection
        test_cases = [
            ("en-US,en;q=0.9,lv;q=0.8", "en"),
            ("lv,en;q=0.8,ru;q=0.6", "lv"),
            ("ru-RU,ru;q=0.9", "ru"),
            ("fr-FR,fr;q=0.9,en;q=0.8", "en"),  # Fallback to supported language
            ("", "lv"),  # Default
        ]
        
        for accept_lang, expected in test_cases:
            detected = LanguageDetector.detect_from_accept_language(accept_lang)
            status = "✓" if detected == expected else "✗"
            print(f"{status} '{accept_lang}' -> {detected} (expected: {expected})")
        
        # Test text detection
        text_cases = [
            ("This is an English text about apartments", "en"),
            ("Šis ir latviešu teksts par dzīvokļiem", "lv"),
            ("Это русский текст о квартирах", "ru"),
            ("", "lv"),  # Default
        ]
        
        for text, expected in text_cases:
            detected = LanguageDetector.detect_from_text(text)
            status = "✓" if detected == expected else "✗"
            print(f"{status} Text detection: '{text[:30]}...' -> {detected}")
        
    except Exception as e:
        print(f"✗ Language detection test failed: {e}")
        return False
    
    return True


def test_formatters():
    """Test the i18n formatters."""
    print("\n=== Testing I18n Formatters ===")
    
    try:
        from utils.i18n import CurrencyFormatter, DateTimeFormatter, NumberFormatter
        from datetime import datetime
        
        # Test currency formatting
        test_price = 125000.50
        for lang in SupportedLanguage:
            formatted = CurrencyFormatter.format_price(test_price, lang.value)
            print(f"✓ {lang.value} price format: {formatted}")
        
        # Test area formatting
        test_area = 65.75
        for lang in SupportedLanguage:
            formatted = NumberFormatter.format_area(test_area, lang.value)
            print(f"✓ {lang.value} area format: {formatted}")
        
        # Test date formatting
        test_date = datetime(2024, 1, 15, 14, 30)
        for lang in SupportedLanguage:
            formatted = DateTimeFormatter.format_date(test_date, lang.value)
            relative = DateTimeFormatter.format_relative_date(test_date, lang.value)
            print(f"✓ {lang.value} date format: {formatted} ({relative})")
        
        # Test room formatting
        for lang in SupportedLanguage:
            rooms_1 = NumberFormatter.format_rooms(1, lang.value)
            rooms_3 = NumberFormatter.format_rooms(3, lang.value)
            print(f"✓ {lang.value} rooms: {rooms_1}, {rooms_3}")
        
    except Exception as e:
        print(f"✗ Formatters test failed: {e}")
        return False
    
    return True


async def main():
    """Run all i18n tests."""
    print("ProScrape I18n API Integration Test")
    print("=" * 40)
    
    tests = [
        test_translation_manager(),
        test_i18n_models(),
        test_language_detection(),
        test_formatters()
    ]
    
    results = []
    for test in tests:
        if asyncio.iscoroutine(test):
            result = await test
        else:
            result = test
        results.append(result)
    
    print("\n" + "=" * 40)
    print("Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All i18n tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))