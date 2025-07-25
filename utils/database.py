from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    def __init__(self):
        self.client = None
        self.database = None
    
    def connect(self):
        """Connect to MongoDB (synchronous)."""
        try:
            self.client = MongoClient(settings.mongodb_url)
            self.database = self.client[settings.mongodb_database]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {settings.mongodb_url}")
            
            # Create indexes
            self.create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def create_indexes(self):
        """Create database indexes for optimal performance."""
        try:
            listings_collection = self.database.listings
            
            # Unique index for preventing duplicates
            listings_collection.create_index(
                [("listing_id", 1), ("source_site", 1)], 
                unique=True,
                name="unique_listing"
            )
            
            # Indexes for common queries
            listings_collection.create_index("scraped_at", name="scraped_at_idx")
            listings_collection.create_index("city", name="city_idx")
            listings_collection.create_index("property_type", name="property_type_idx")
            listings_collection.create_index("price", name="price_idx")
            listings_collection.create_index("area_sqm", name="area_idx")
            listings_collection.create_index("posted_date", name="posted_date_idx")
            
            # Compound indexes for complex queries
            listings_collection.create_index(
                [("city", 1), ("property_type", 1), ("price", 1)],
                name="city_type_price_idx"
            )
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def get_collection(self, name):
        """Get a collection from the database."""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database[name]


class AsyncDatabase:
    """Async database connection manager for FastAPI."""
    
    def __init__(self):
        self.client = None
        self.database = None
    
    async def connect(self):
        """Connect to MongoDB (asynchronous)."""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.database = self.client[settings.mongodb_database]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB (async): {settings.mongodb_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB (async): {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB (async)")
    
    def get_collection(self, name):
        """Get a collection from the database."""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database[name]


# Global database instances
db = Database()
async_db = AsyncDatabase()