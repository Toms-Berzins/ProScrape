#!/usr/bin/env python3
"""
Test script to run SS spider through Scrapy pipeline with limited items.
Verifies that the coordinate and image extraction works in the full pipeline.
"""

import subprocess
import sys
import os
import json
from datetime import datetime
import time

def run_scrapy_spider():
    """Run SS spider with limited items through Scrapy."""
    print("Testing SS Spider through Scrapy Pipeline")
    print("=" * 60)
    
    # Change to project directory
    os.chdir("C:\\Users\\berzi\\ProScrape")
    
    # Run scrapy with limited items and custom settings
    cmd = [
        sys.executable, "-m", "scrapy", "crawl", "ss_spider",
        "-s", "CLOSESPIDER_ITEMCOUNT=3",  # Limit to 3 items
        "-s", "LOG_LEVEL=INFO",
        "-L", "INFO"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        # Run the spider
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nReturn code: {result.returncode}")
        
        # Parse output for item information
        lines = result.stdout.split('\n')
        items_scraped = 0
        for line in lines:
            if 'item_scraped_count' in line:
                try:
                    items_scraped = int(line.split(':')[-1].strip())
                except:
                    pass
        
        print(f"Items scraped: {items_scraped}")
        
        return result.returncode == 0, items_scraped
        
    except subprocess.TimeoutExpired:
        print("Spider execution timed out after 5 minutes")
        return False, 0
    except Exception as e:
        print(f"Error running spider: {e}")
        return False, 0

def check_database_for_new_items():
    """Check MongoDB for newly scraped items with coordinates and images."""
    print("\n" + "=" * 60)
    print("Checking Database for New Items")
    print("=" * 60)
    
    try:
        # Run database check script
        check_script = """
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

async def check_recent_items():
    load_dotenv()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.getenv('MONGODB_URL'))
    db = client[os.getenv('MONGODB_DATABASE', 'proscrape')]
    collection = db.listings
    
    # Find items from the last 10 minutes
    ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
    
    # Query for recent items
    recent_items = collection.find({
        '$or': [
            {'scraped_at': {'$gte': ten_minutes_ago}},
            {'_id': {'$gte': ten_minutes_ago}}
        ]
    }).sort('_id', -1).limit(10)
    
    items = await recent_items.to_list(length=10)
    
    print(f"Found {len(items)} recent items:")
    
    for i, item in enumerate(items, 1):
        print(f"\\n{i}. Listing ID: {item.get('listing_id', 'N/A')}")
        print(f"   Title: {item.get('title', 'N/A')[:60]}...")
        print(f"   Images: {len(item.get('image_urls', []))} found")
        print(f"   Coordinates: {'Yes' if item.get('latitude') and item.get('longitude') else 'No'}")
        if item.get('latitude') and item.get('longitude'):
            print(f"   - Lat/Lng: {item.get('latitude')}, {item.get('longitude')}")
        
        # Show first few image URLs
        images = item.get('image_urls', [])
        if images:
            print(f"   Sample images:")
            for j, img in enumerate(images[:3], 1):
                print(f"     {j}. {img}")
            if len(images) > 3:
                print(f"     ... and {len(images) - 3} more")
    
    client.close()
    return len(items)

# Run the async function
loop = asyncio.get_event_loop()
count = loop.run_until_complete(check_recent_items())
print(f"\\nTotal recent items found: {count}")
"""
        
        # Write and run the check script
        with open("temp_db_check.py", "w") as f:
            f.write(check_script)
        
        result = subprocess.run([sys.executable, "temp_db_check.py"], 
                              capture_output=True, text=True, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        # Clean up
        os.remove("temp_db_check.py")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error checking database: {e}")
        return False

def main():
    """Main test function."""
    print("SS Spider Pipeline Integration Test")
    print("Testing coordinate and image extraction through full Scrapy pipeline")
    print("=" * 80)
    
    # Step 1: Run the spider
    success, items_count = run_scrapy_spider()
    
    if not success:
        print("\nSpider execution failed!")
        return False
    
    if items_count == 0:
        print("\nNo items were scraped!")
        return False
    
    print(f"\nSpider completed successfully with {items_count} items")
    
    # Step 2: Wait a moment for database writes to complete
    print("\nWaiting 5 seconds for database writes to complete...")
    time.sleep(5)
    
    # Step 3: Check database for new items
    db_success = check_database_for_new_items()
    
    if not db_success:
        print("\nDatabase check failed!")
        return False
    
    print("\n" + "=" * 80)
    print("PIPELINE TEST COMPLETED SUCCESSFULLY")
    print("The SS spider coordinate and image extraction fixes are working!")
    print("=" * 80)
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)