import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ.setdefault('MONGODB_URL', 'mongodb://localhost:27017')
os.environ.setdefault('MONGODB_DATABASE', 'proscrape_test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/1')  # Use different Redis DB for tests


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_listing_data():
    """Sample listing data for testing."""
    return {
        "listing_id": "test_12345",
        "source_site": "ss.com",
        "title": "Beautiful 3-room apartment in central Riga",
        "description": "Spacious apartment with balcony and parking",
        "source_url": "https://ss.com/msg/test_12345",
        "price": 150000.00,
        "price_currency": "EUR",
        "area_sqm": 75.5,
        "rooms": 3,
        "floor": 4,
        "total_floors": 9,
        "property_type": "apartment",
        "address": "Elizabetes iela 123",
        "city": "Riga",
        "district": "Centre",
        "postal_code": "LV-1050",
        "latitude": 56.9496,
        "longitude": 24.1052,
        "features": ["balcony", "parking", "elevator"],
        "amenities": ["security", "internet"],
        "image_urls": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ]
    }


@pytest.fixture
def sample_raw_data():
    """Sample raw scraped data for normalization testing."""
    return {
        "listing_id": "raw_123",
        "source_site": "city24.lv",
        "title": "Dzīvoklis Rīgā",
        "source_url": "https://city24.lv/property/raw_123",
        "price": "€120,000",
        "price_currency": "EUR",
        "area_sqm": "65.5 m²",
        "property_type": "dzīvoklis",
        "address": "Brīvības iela 45, Rīga, LV-1010",
        "features": ["balkons", "lifts", "renovēts"],
        "posted_date": "01.02.2024"
    }


@pytest.fixture
async def mongodb_connection():
    """Provide a test MongoDB connection."""
    from utils.database import async_db
    
    # Connect to test database
    await async_db.connect()
    
    yield async_db
    
    # Clean up after tests
    test_collection = async_db.get_collection("listings")
    await test_collection.delete_many({})  # Clear test data
    
    # Disconnect
    await async_db.disconnect()


@pytest.fixture
def mock_scrapy_response():
    """Mock Scrapy response object for spider testing."""
    class MockResponse:
        def __init__(self, url="https://example.com", text="<html></html>"):
            self.url = url
            self.text = text
            self.meta = {}
        
        def xpath(self, query):
            # Mock xpath method that returns empty results
            class MockSelector:
                def get(self):
                    return None
                
                def getall(self):
                    return []
            
            return MockSelector()
    
    return MockResponse


@pytest.fixture(autouse=True)
def clean_test_environment():
    """Clean up test environment before and after each test."""
    # Setup: Clean any existing test data
    yield
    # Teardown: Additional cleanup if needed
    pass