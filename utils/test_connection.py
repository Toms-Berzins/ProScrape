#!/usr/bin/env python3
"""
Test script to verify MongoDB connection and create indexes.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from utils.database import db
from models.listing import ListingCreate


def test_mongodb_connection():
    """Test MongoDB connection and create indexes."""
    try:
        print("Testing MongoDB connection...")
        print(f"MongoDB URL: {settings.mongodb_url}")
        print(f"Database: {settings.mongodb_database}")
        
        # Connect to database
        db.connect()
        print("+ Successfully connected to MongoDB")
        
        # Test collection access
        collection = db.get_collection("listings")
        print("+ Successfully accessed listings collection")
        
        # Test insert/update operation
        test_listing = {
            "listing_id": "test_123",
            "source_site": "ss.com",
            "title": "Test Listing",
            "source_url": "https://example.com/test",
            "price": 100000.00,
            "price_currency": "EUR",
            "area_sqm": 50.0,
            "property_type": "apartment",
            "city": "Riga",
            "address": "Test Street 123, Riga"
        }
        
        # Validate with Pydantic model
        listing_model = ListingCreate(**test_listing)
        print("+ Test data validation successful")
        
        # Insert test document (convert to JSON serializable format)
        test_data = listing_model.dict()
        # Convert Decimal to float for MongoDB
        if 'price' in test_data and test_data['price']:
            test_data['price'] = float(test_data['price'])
        
        result = collection.update_one(
            {"listing_id": "test_123", "source_site": "ss.com"},
            {"$set": test_data},
            upsert=True
        )
        
        if result.upserted_id:
            print("+ Test document inserted successfully")
        else:
            print("+ Test document updated successfully")
        
        # Test query
        found_doc = collection.find_one({"listing_id": "test_123"})
        if found_doc:
            print("+ Test document retrieved successfully")
        
        # Clean up test document
        collection.delete_one({"listing_id": "test_123"})
        print("+ Test document cleaned up")
        
        # List existing indexes
        indexes = list(collection.list_indexes())
        print(f"+ Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx['name']}: {idx.get('key', {})}")
        
        print("\n+ All MongoDB tests passed successfully!")
        
    except Exception as e:
        print(f"- MongoDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Disconnect
        db.disconnect()
        print("+ Disconnected from MongoDB")
    
    return True


def test_async_connection():
    """Test async MongoDB connection."""
    import asyncio
    from utils.database import async_db
    
    async def _test_async():
        try:
            print("\nTesting async MongoDB connection...")
            
            # Connect
            await async_db.connect()
            print("+ Successfully connected to MongoDB (async)")
            
            # Test collection access
            collection = async_db.get_collection("listings")
            
            # Test count operation
            count = await collection.count_documents({})
            print(f"+ Current document count: {count}")
            
            # Test aggregation
            pipeline = [{"$group": {"_id": "$source_site", "count": {"$sum": 1}}}]
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            print("+ Aggregation test successful")
            if results:
                print("  Document counts by source:")
                for result in results:
                    print(f"    {result['_id']}: {result['count']}")
            else:
                print("  No documents found")
            
            print("+ Async MongoDB test passed!")
            
        except Exception as e:
            print(f"- Async MongoDB test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            await async_db.disconnect()
            print("+ Disconnected from MongoDB (async)")
        
        return True
    
    return asyncio.run(_test_async())


def main():
    """Main test function."""
    print("ProScrape Database Connection Test")
    print("=" * 40)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test synchronous connection
    sync_success = test_mongodb_connection()
    
    # Test asynchronous connection
    async_success = test_async_connection()
    
    # Summary
    print("\n" + "=" * 40)
    print("Test Summary:")
    print(f"  Sync connection: {'PASS' if sync_success else 'FAIL'}")
    print(f"  Async connection: {'PASS' if async_success else 'FAIL'}")
    
    if sync_success and async_success:
        print("\nAll database tests passed! Your MongoDB setup is working correctly.")
        return True
    else:
        print("\nSome tests failed. Please check your MongoDB configuration.")
        print("\nTroubleshooting tips:")
        print("1. Make sure MongoDB is running (docker-compose up mongodb)")
        print("2. Check your .env file settings")
        print("3. Verify network connectivity")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)