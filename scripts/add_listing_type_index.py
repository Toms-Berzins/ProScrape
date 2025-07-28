#!/usr/bin/env python3
"""
Script to add database indexes for efficient listing_type sorting and filtering.
This script creates the necessary indexes for optimized queries on listing_type.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import async_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_listing_type_indexes():
    """Create database indexes for efficient listing_type sorting and filtering."""
    try:
        # Connect to the database
        await async_db.connect()
        collection = async_db.get_collection("listings")
        
        logger.info("Creating indexes for listing_type field...")
        
        # Create single field index on listing_type
        await collection.create_index("listing_type")
        logger.info("✓ Created index on listing_type")
        
        # Create compound indexes for common query patterns
        # listing_type + city (for location-based filtering)
        await collection.create_index([("listing_type", 1), ("city", 1)])
        logger.info("✓ Created compound index on listing_type + city")
        
        # listing_type + property_type (for property type filtering)
        await collection.create_index([("listing_type", 1), ("property_type", 1)])
        logger.info("✓ Created compound index on listing_type + property_type")
        
        # listing_type + price (for price-based sorting and filtering)
        await collection.create_index([("listing_type", 1), ("price", 1)])
        logger.info("✓ Created compound index on listing_type + price")
        
        # listing_type + scraped_at (for chronological sorting)
        await collection.create_index([("listing_type", 1), ("scraped_at", -1)])
        logger.info("✓ Created compound index on listing_type + scraped_at")
        
        # listing_type + coordinates (for map-based queries)
        await collection.create_index([
            ("listing_type", 1), 
            ("latitude", 1), 
            ("longitude", 1)
        ])
        logger.info("✓ Created compound index on listing_type + coordinates")
        
        # List all indexes to verify creation
        logger.info("\nCurrent indexes on listings collection:")
        indexes = await collection.list_indexes().to_list(length=None)
        for idx in indexes:
            logger.info(f"  - {idx['name']}: {idx.get('key', {})}")
        
        logger.info("\n✅ All listing_type indexes created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        raise
    finally:
        await async_db.disconnect()


async def check_existing_indexes():
    """Check what indexes already exist on the listings collection."""
    try:
        await async_db.connect()
        collection = async_db.get_collection("listings")
        
        logger.info("Checking existing indexes...")
        indexes = await collection.list_indexes().to_list(length=None)
        
        logger.info(f"Found {len(indexes)} existing indexes:")
        for idx in indexes:
            logger.info(f"  - {idx['name']}: {idx.get('key', {})}")
        
        return indexes
        
    except Exception as e:
        logger.error(f"Error checking indexes: {e}")
        return []
    finally:
        await async_db.disconnect()


async def main():
    """Main function to create database indexes."""
    logger.info("=== ProScrape Database Indexing Script ===")
    logger.info("Adding indexes for efficient listing_type sorting and filtering")
    
    # Check existing indexes first
    await check_existing_indexes()
    
    # Create new indexes
    await create_listing_type_indexes()
    
    logger.info("=== Indexing complete ===")


if __name__ == "__main__":
    asyncio.run(main())