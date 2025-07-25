from datetime import datetime
from itemadapter import ItemAdapter
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import logging
from models.listing import ListingCreate
from utils.normalization import normalize_listing_data


class ValidationPipeline:
    """Pipeline to validate item data."""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Validate required fields
        required_fields = ['listing_id', 'source_site', 'title', 'source_url']
        for field in required_fields:
            if not adapter.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults
        if not adapter.get('scraped_at'):
            adapter['scraped_at'] = datetime.utcnow()
        
        if not adapter.get('price_currency'):
            adapter['price_currency'] = 'EUR'
        
        return item


class NormalizationPipeline:
    """Pipeline to normalize and standardize item data."""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        try:
            # Convert to dict for normalization
            raw_data = dict(adapter)
            
            # Apply normalization
            normalized_data = normalize_listing_data(raw_data)
            
            # Update adapter with normalized data
            for key, value in normalized_data.items():
                adapter[key] = value
            
            # Log normalization results
            changes = []
            if raw_data.get('price') != normalized_data.get('price'):
                changes.append(f"price: {raw_data.get('price')} -> {normalized_data.get('price')}")
            if raw_data.get('area_sqm') != normalized_data.get('area_sqm'):
                changes.append(f"area: {raw_data.get('area_sqm')} -> {normalized_data.get('area_sqm')}")
            if raw_data.get('property_type') != normalized_data.get('property_type'):
                changes.append(f"type: {raw_data.get('property_type')} -> {normalized_data.get('property_type')}")
            
            if changes:
                spider.logger.debug(f"Normalized {adapter['listing_id']}: {', '.join(changes)}")
            
            # Add calculated fields
            if normalized_data.get('price_per_sqm'):
                spider.logger.debug(f"Added price_per_sqm: {normalized_data['price_per_sqm']} EUR/m²")
            
        except Exception as e:
            spider.logger.error(f"Error normalizing item {adapter.get('listing_id', 'unknown')}: {e}")
            # Continue with original data if normalization fails
        
        return item


class DuplicatesPipeline:
    """Pipeline to filter out duplicate items."""
    
    def __init__(self):
        self.seen_ids = set()
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Create unique key from listing_id and source_site
        unique_key = f"{adapter['source_site']}:{adapter['listing_id']}"
        
        if unique_key in self.seen_ids:
            spider.logger.warning(f"Duplicate item found: {unique_key}")
            raise ValueError(f"Duplicate item: {unique_key}")
        else:
            self.seen_ids.add(unique_key)
            return item


class MongoPipeline:
    """Pipeline to save items to MongoDB."""
    
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = None
        self.db = None
        self.collection = None
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGODB_URL", "mongodb://localhost:27017"),
            mongo_db=crawler.settings.get("MONGODB_DATABASE", "proscrape"),
        )
    
    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.collection = self.db.listings
        
        # Create indexes
        self.collection.create_index([("listing_id", 1), ("source_site", 1)], unique=True)
        self.collection.create_index("scraped_at")
        self.collection.create_index("city")
        self.collection.create_index("property_type")
        self.collection.create_index("price")
        
        spider.logger.info(f"Connected to MongoDB: {self.mongo_uri}/{self.mongo_db}")
    
    def close_spider(self, spider):
        if self.client:
            self.client.close()
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        try:
            # Convert item to dict and validate with Pydantic model
            item_dict = dict(adapter)
            listing = ListingCreate(**item_dict)
            
            # Insert or update document
            filter_query = {
                "listing_id": listing.listing_id,
                "source_site": listing.source_site
            }
            
            update_data = listing.dict()
            
            result = self.collection.update_one(
                filter_query,
                {"$set": update_data},
                upsert=True
            )
            
            if result.upserted_id:
                spider.logger.info(f"Inserted new listing: {listing.listing_id}")
            else:
                spider.logger.info(f"Updated existing listing: {listing.listing_id}")
            
        except DuplicateKeyError:
            spider.logger.warning(f"Duplicate key error for listing: {adapter['listing_id']}")
        except Exception as e:
            spider.logger.error(f"Error processing item {adapter.get('listing_id', 'unknown')}: {e}")
            raise
        
        return item


class LoggingPipeline:
    """Pipeline for detailed logging."""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        spider.logger.info(
            f"Processed item: {adapter['source_site']}:{adapter['listing_id']} - "
            f"{adapter.get('title', 'No title')[:50]}..."
        )
        
        return item