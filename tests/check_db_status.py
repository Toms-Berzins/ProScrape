#!/usr/bin/env python3
"""Check database status and recent listings."""

from utils.database import Database
from datetime import datetime

def main():
    print("=== ProScrape Database Status ===")
    
    db = Database()
    db.connect()
    
    try:
        collection = db.get_collection('listings')
        
        # Get total count
        total_count = collection.count_documents({})
        print(f"Total listings in database: {total_count}")
        
        # Get count by source site
        pipeline = [
            {"$group": {"_id": "$source_site", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        site_counts = list(collection.aggregate(pipeline))
        print("\nListings by source site:")
        for site in site_counts:
            print(f"  {site['_id']}: {site['count']} listings")
        
        # Get recent listings
        recent_listings = list(collection.find().sort('scraped_at', -1).limit(5))
        print(f"\nRecent listings ({len(recent_listings)}):")
        
        for listing in recent_listings:
            title = listing.get('title', 'No title')[:50] + '...' if listing.get('title', '') else 'No title'
            source = listing.get('source_site', 'Unknown')
            price = listing.get('price', 'No price')
            scraped_at = listing.get('scraped_at', 'Unknown time')
            
            print(f"  - {title}")
            print(f"    Source: {source} | Price: {price} | Scraped: {scraped_at}")
            print()
        
        # Check for today's listings
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = collection.count_documents({
            'scraped_at': {'$gte': today}
        })
        print(f"Listings scraped today: {today_count}")
        
    finally:
        db.disconnect()

if __name__ == "__main__":
    main()