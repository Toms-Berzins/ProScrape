#!/usr/bin/env python3
"""
Database seeding script for ProScrape development
Creates sample real estate listings for testing and development
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import random

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.listing import Listing
from utils.database import get_database
from utils.logging_config import setup_logging

# Setup logging
logger = setup_logging()

# Sample data for generating realistic listings
SAMPLE_TITLES = [
    "Modern 2-bedroom apartment in city center",
    "Spacious family house with garden",
    "Luxury penthouse with panoramic views",
    "Cozy studio apartment near university",
    "Renovated 3-bedroom flat with balcony",
    "Traditional house in quiet neighborhood",
    "New development apartment with parking",
    "Charming cottage with mountain views",
    "Contemporary loft in arts district",
    "Family home with swimming pool",
    "Bright apartment with river views",
    "Historic building conversion",
    "Modern villa with private garden",
    "Student-friendly shared accommodation",
    "Executive apartment in business district"
]

SAMPLE_AREAS = [
    "Riga Center", "Vecriga", "Agenskalns", "Tornakalns", "Purvciems",
    "Imanta", "Jugla", "Mezciems", "Ziepniekkalns", "Kengarags",
    "Daugavgriva", "Bolderaja", "Marupe", "Jurmala", "Ogre"
]

SAMPLE_FEATURES = [
    "balcony", "parking", "elevator", "renovated", "furnished",
    "garden", "terrace", "fireplace", "air_conditioning", "swimming_pool",
    "garage", "basement", "attic", "security_system", "internet",
    "cable_tv", "dishwasher", "washing_machine", "gym", "playground"
]

SAMPLE_COORDINATES = [
    (56.9496, 24.1052),  # Riga center
    (56.9459, 24.1059),  # Old Town
    (56.9418, 24.0732),  # Agenskalns
    (56.9392, 24.0901),  # Tornakalns
    (56.9912, 24.1618),  # Purvciems
    (56.9187, 24.0430),  # Imanta
    (57.0167, 24.1833),  # Jugla
    (56.9833, 24.1667),  # Mezciems
    (56.9000, 24.0667),  # Ziepniekkalns
    (56.9167, 24.1833),  # Kengarags
]

async def create_sample_listing(source: str, index: int) -> Listing:
    """Create a sample listing with realistic data"""
    
    # Generate realistic listing ID
    listing_id = f"{source}_{index:06d}"
    
    # Random title and area
    title = random.choice(SAMPLE_TITLES)
    area = random.choice(SAMPLE_AREAS)
    
    # Random price based on realistic ranges
    if "apartment" in title.lower() or "studio" in title.lower():
        base_price = random.randint(300, 1200)
    elif "house" in title.lower() or "villa" in title.lower():
        base_price = random.randint(800, 3000)
    else:
        base_price = random.randint(400, 1500)
    
    price = Decimal(str(base_price))
    
    # Random coordinates
    lat, lon = random.choice(SAMPLE_COORDINATES)
    # Add some random variation
    lat += random.uniform(-0.01, 0.01)
    lon += random.uniform(-0.01, 0.01)
    coordinates = [lon, lat]  # GeoJSON format [longitude, latitude]
    
    # Random features
    num_features = random.randint(2, 8)
    features = random.sample(SAMPLE_FEATURES, num_features)
    
    # Random posted date (within last 30 days)
    days_ago = random.randint(1, 30)
    posted_date = datetime.utcnow() - timedelta(days=days_ago)
    
    # Generate image URLs
    num_images = random.randint(1, 5)
    image_urls = [
        f"https://example.com/images/{listing_id}_{i}.jpg" 
        for i in range(num_images)
    ]
    
    return Listing(
        listing_id=listing_id,
        source=source,
        title=title,
        price=price,
        area=area,
        coordinates=coordinates,
        features=features,
        posted_date=posted_date,
        image_urls=image_urls,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

async def seed_database(num_listings_per_source: int = 50):
    """Seed the database with sample listings"""
    
    logger.info("Starting database seeding process...")
    
    try:
        # Get database connection
        db = await get_database()
        collection = db.listings
        
        # Clear existing seed data (optional)
        existing_count = await collection.count_documents({})
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing listings")
            response = input("Clear existing data? (y/N): ")
            if response.lower() == 'y':
                await collection.delete_many({})
                logger.info("Cleared existing listings")
        
        # Generate sample listings for each source
        sources = ["ss.com", "city24.lv", "pp.lv"]
        all_listings = []
        
        for source in sources:
            logger.info(f"Generating {num_listings_per_source} listings for {source}")
            for i in range(num_listings_per_source):
                listing = await create_sample_listing(source, i + 1)
                all_listings.append(listing)
        
        # Insert listings in batches
        batch_size = 20
        total_inserted = 0
        
        for i in range(0, len(all_listings), batch_size):
            batch = all_listings[i:i + batch_size]
            batch_data = [listing.model_dump() for listing in batch]
            
            try:
                result = await collection.insert_many(batch_data)
                total_inserted += len(result.inserted_ids)
                logger.info(f"Inserted batch {i//batch_size + 1}: {len(result.inserted_ids)} listings")
            except Exception as e:
                logger.error(f"Error inserting batch {i//batch_size + 1}: {e}")
        
        logger.info(f"Seeding completed! Inserted {total_inserted} listings total")
        
        # Create indexes for better performance
        await create_indexes(collection)
        
        # Show summary statistics
        await show_summary_stats(collection)
        
    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        raise

async def create_indexes(collection):
    """Create database indexes for better query performance"""
    
    logger.info("Creating database indexes...")
    
    try:
        # Create indexes
        await collection.create_index("listing_id", unique=True)
        await collection.create_index("source")
        await collection.create_index("posted_date")
        await collection.create_index("price")
        await collection.create_index("area")
        await collection.create_index([("coordinates", "2dsphere")])  # Geospatial index
        await collection.create_index("created_at")
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Error creating indexes (may already exist): {e}")

async def show_summary_stats(collection):
    """Show summary statistics of seeded data"""
    
    logger.info("Generating summary statistics...")
    
    try:
        # Total count
        total = await collection.count_documents({})
        
        # Count by source
        pipeline = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        source_stats = await collection.aggregate(pipeline).to_list(None)
        
        # Price statistics
        price_pipeline = [
            {"$group": {
                "_id": None,
                "avg_price": {"$avg": "$price"},
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"}
            }}
        ]
        price_stats = await collection.aggregate(price_pipeline).to_list(None)
        
        # Date range
        date_pipeline = [
            {"$group": {
                "_id": None,
                "oldest": {"$min": "$posted_date"},
                "newest": {"$max": "$posted_date"}
            }}
        ]
        date_stats = await collection.aggregate(date_pipeline).to_list(None)
        
        print("\n" + "="*50)
        print("DATABASE SEEDING SUMMARY")
        print("="*50)
        print(f"Total listings: {total}")
        print("\nListings by source:")
        for stat in source_stats:
            print(f"  {stat['_id']}: {stat['count']}")
        
        if price_stats:
            stats = price_stats[0]
            print(f"\nPrice statistics:")
            print(f"  Average: €{stats['avg_price']:.2f}")
            print(f"  Range: €{stats['min_price']:.2f} - €{stats['max_price']:.2f}")
        
        if date_stats:
            stats = date_stats[0]
            print(f"\nDate range:")
            print(f"  Oldest: {stats['oldest'].strftime('%Y-%m-%d')}")
            print(f"  Newest: {stats['newest'].strftime('%Y-%m-%d')}")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error generating summary stats: {e}")

async def validate_seeded_data():
    """Validate that seeded data is correct"""
    
    logger.info("Validating seeded data...")
    
    try:
        db = await get_database()
        collection = db.listings
        
        # Test basic queries
        sample_listing = await collection.find_one()
        if sample_listing:
            listing = Listing(**sample_listing)
            logger.info(f"Sample listing validation passed: {listing.listing_id}")
        
        # Test geospatial query
        geo_query = {
            "coordinates": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [24.1052, 56.9496]},
                    "$maxDistance": 5000  # 5km radius
                }
            }
        }
        nearby_count = await collection.count_documents(geo_query)
        logger.info(f"Geospatial query test: found {nearby_count} listings near Riga center")
        
        logger.info("Data validation completed successfully")
        
    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise

def main():
    """Main function to run the seeding process"""
    
    print("ProScrape Database Seeding Tool")
    print("===============================")
    
    # Get number of listings from command line or use default
    num_listings = 50
    if len(sys.argv) > 1:
        try:
            num_listings = int(sys.argv[1])
        except ValueError:
            print("Invalid number of listings. Using default: 50")
    
    print(f"Will create {num_listings} listings per source (total: {num_listings * 3})")
    
    # Run async seeding process
    try:
        asyncio.run(seed_database(num_listings))
        asyncio.run(validate_seeded_data())
        print("\nSeeding completed successfully!")
        
    except KeyboardInterrupt:
        print("\nSeeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nSeeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()