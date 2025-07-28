"""
Multilingual Database Schema and Operations for ProScrape i18n Pipeline

This module provides database schema design, indexing strategies, and operations
for efficient storage and retrieval of multilingual real estate content.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId

from models.i18n_models import (
    MultilingualListing, MultilingualListingCreate, MultilingualListingUpdate,
    TranslationResult, BatchTranslationJob, LanguageAnalysisReport,
    SupportedLanguage, TranslationStatus, TranslationQuality
)
from utils.language_detection import SupportedLanguage

logger = logging.getLogger(__name__)


class I18nDatabaseManager:
    """Database manager for multilingual content operations."""
    
    def __init__(self, mongodb_url: str, database_name: str):
        self.mongodb_url = mongodb_url
        self.database_name = database_name
        self.client = None
        self.db = None
        
        # Collection names
        self.LISTINGS_COLLECTION = "multilingual_listings"
        self.TRANSLATIONS_COLLECTION = "translation_results"
        self.TRANSLATION_JOBS_COLLECTION = "translation_jobs"
        self.LANGUAGE_ANALYSIS_COLLECTION = "language_analysis"
        self.QUALITY_METRICS_COLLECTION = "quality_metrics"
    
    def connect(self):
        """Connect to MongoDB and initialize collections."""
        try:
            self.client = MongoClient(self.mongodb_url)
            self.db = self.client[self.database_name]
            
            # Test connection
            self.client.admin.command('ping')
            
            # Create collections and indexes
            self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {self.database_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def _create_indexes(self):
        """Create indexes for efficient multilingual data operations."""
        
        # Multilingual Listings Collection Indexes
        listings_collection = self.db[self.LISTINGS_COLLECTION]
        
        try:
            # Unique index on listing_id + source_site
            listings_collection.create_index(
                [("listing_id", ASCENDING), ("source_site", ASCENDING)],
                unique=True,
                name="unique_listing"
            )
            
            # Language-based indexes
            listings_collection.create_index(
                [("language_analysis.primary_language", ASCENDING)],
                name="primary_language_idx"
            )
            
            # Content availability indexes (for finding missing translations)
            listings_collection.create_index(
                [("title.en", ASCENDING)],
                sparse=True,
                name="title_en_idx"
            )
            listings_collection.create_index(
                [("title.lv", ASCENDING)],
                sparse=True,
                name="title_lv_idx"
            )
            listings_collection.create_index(
                [("title.ru", ASCENDING)],
                sparse=True,
                name="title_ru_idx"
            )
            
            listings_collection.create_index(
                [("description.en", ASCENDING)],
                sparse=True,
                name="description_en_idx"
            )
            listings_collection.create_index(
                [("description.lv", ASCENDING)],
                sparse=True,
                name="description_lv_idx"
            )
            listings_collection.create_index(
                [("description.ru", ASCENDING)],
                sparse=True,
                name="description_ru_idx"
            )
            
            # Translation status indexes
            listings_collection.create_index(
                [("needs_translation", ASCENDING)],
                name="needs_translation_idx"
            )
            listings_collection.create_index(
                [("needs_verification", ASCENDING)],
                name="needs_verification_idx"
            )
            
            # Quality score index
            listings_collection.create_index(
                [("quality_score", DESCENDING)],
                sparse=True,
                name="quality_score_idx"
            )
            
            # Property search indexes
            listings_collection.create_index(
                [("property_type", ASCENDING)],
                name="property_type_idx"
            )
            listings_collection.create_index(
                [("listing_type", ASCENDING)],
                name="listing_type_idx"
            )
            listings_collection.create_index(
                [("price.amount", ASCENDING)],
                sparse=True,
                name="price_idx"
            )
            listings_collection.create_index(
                [("area_sqm", ASCENDING)],
                sparse=True,
                name="area_idx"
            )
            
            # Geographic indexes
            listings_collection.create_index(
                [("address.latitude", ASCENDING), ("address.longitude", ASCENDING)],
                sparse=True,
                name="coordinates_idx"
            )
            
            # Temporal indexes
            listings_collection.create_index(
                [("scraped_at", DESCENDING)],
                name="scraped_at_idx"
            )
            listings_collection.create_index(
                [("posted_date", DESCENDING)],
                sparse=True,
                name="posted_date_idx"
            )
            
            # Text search indexes for multilingual content
            listings_collection.create_index(
                [
                    ("title.en", TEXT),
                    ("title.lv", TEXT),
                    ("title.ru", TEXT),
                    ("description.en", TEXT),
                    ("description.lv", TEXT),
                    ("description.ru", TEXT)
                ],
                name="multilingual_text_search",
                default_language="english"
            )
            
            # Translation Results Collection Indexes
            translations_collection = self.db[self.TRANSLATIONS_COLLECTION]
            
            translations_collection.create_index(
                [("listing_id", ASCENDING), ("field_name", ASCENDING), 
                 ("target_language", ASCENDING)],
                name="translation_lookup_idx"
            )
            
            translations_collection.create_index(
                [("translation_service", ASCENDING)],
                name="translation_service_idx"
            )
            
            translations_collection.create_index(
                [("quality_assessment", ASCENDING)],
                name="quality_assessment_idx"
            )
            
            translations_collection.create_index(
                [("completed_at", DESCENDING)],
                name="completed_at_idx"
            )
            
            # Translation Jobs Collection Indexes
            jobs_collection = self.db[self.TRANSLATION_JOBS_COLLECTION]
            
            jobs_collection.create_index(
                [("status", ASCENDING)],
                name="job_status_idx"
            )
            
            jobs_collection.create_index(
                [("created_at", DESCENDING)],
                name="job_created_at_idx"
            )
            
            # Compound index for efficient job queries
            jobs_collection.create_index(
                [("status", ASCENDING), ("created_at", DESCENDING)],
                name="job_status_created_idx"
            )
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Some indexes may already exist: {e}")
    
    def get_listings_collection(self) -> Collection:
        """Get the multilingual listings collection."""
        return self.db[self.LISTINGS_COLLECTION]
    
    def get_translations_collection(self) -> Collection:
        """Get the translation results collection."""
        return self.db[self.TRANSLATIONS_COLLECTION]
    
    def get_translation_jobs_collection(self) -> Collection:
        """Get the translation jobs collection."""
        return self.db[self.TRANSLATION_JOBS_COLLECTION]
    
    # Listing Operations
    
    def insert_listing(self, listing: MultilingualListingCreate) -> str:
        """Insert a new multilingual listing."""
        try:
            collection = self.get_listings_collection()
            
            # Convert Pydantic model to dict
            listing_dict = listing.model_dump()
            
            # Convert Decimal fields to float for MongoDB
            self._convert_decimals_to_float(listing_dict)
            
            result = collection.insert_one(listing_dict)
            logger.info(f"Inserted listing: {listing.listing_id}")
            
            return str(result.inserted_id)
            
        except DuplicateKeyError:
            logger.warning(f"Duplicate listing: {listing.listing_id}")
            raise
        except Exception as e:
            logger.error(f"Error inserting listing: {e}")
            raise
    
    def update_listing(self, listing_id: str, source_site: str, 
                      update_data: MultilingualListingUpdate) -> bool:
        """Update an existing multilingual listing."""
        try:
            collection = self.get_listings_collection()
            
            # Convert update data to dict, excluding None values
            update_dict = update_data.model_dump(exclude_none=True)
            
            # Convert Decimal fields to float
            self._convert_decimals_to_float(update_dict)
            
            result = collection.update_one(
                {"listing_id": listing_id, "source_site": source_site},
                {"$set": update_dict}
            )
            
            if result.matched_count > 0:
                logger.info(f"Updated listing: {listing_id}")
                return True
            else:
                logger.warning(f"Listing not found for update: {listing_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating listing: {e}")
            raise
    
    def get_listing(self, listing_id: str, source_site: str) -> Optional[Dict[str, Any]]:
        """Get a listing by ID and source site."""
        try:
            collection = self.get_listings_collection()
            
            listing = collection.find_one({
                "listing_id": listing_id,
                "source_site": source_site
            })
            
            return listing
            
        except Exception as e:
            logger.error(f"Error getting listing: {e}")
            raise
    
    def find_listings(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        language: Optional[SupportedLanguage] = None,
        limit: int = 100,
        skip: int = 0,
        sort_by: str = "scraped_at",
        sort_order: int = DESCENDING
    ) -> List[Dict[str, Any]]:
        """Find listings with optional filtering and language preference."""
        try:
            collection = self.get_listings_collection()
            
            # Build query
            query = filter_dict or {}
            
            # Language-based filtering can be added here
            if language:
                # Example: Find listings that have content in specific language
                lang_key = language.value
                query[f"$or"] = [
                    {f"title.{lang_key}": {"$exists": True, "$ne": None}},
                    {f"description.{lang_key}": {"$exists": True, "$ne": None}}
                ]
            
            # Execute query
            cursor = collection.find(query).sort(sort_by, sort_order).skip(skip).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error finding listings: {e}")
            raise
    
    def find_listings_needing_translation(
        self, 
        target_language: SupportedLanguage,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find listings that need translation to target language."""
        try:
            collection = self.get_listings_collection()
            
            lang_key = target_language.value
            
            # Find listings where target language content is missing or low quality
            query = {
                "$or": [
                    # No content in target language
                    {f"title.{lang_key}": {"$exists": False}},
                    {f"title.{lang_key}": None},
                    {f"description.{lang_key}": {"$exists": False}},
                    {f"description.{lang_key}": None},
                    # Low quality translations
                    {f"title.metadata.{lang_key}.translation_quality": "low"},
                    {f"description.metadata.{lang_key}.translation_quality": "low"},
                    # Marked as needing translation
                    {"needs_translation": True}
                ]
            }
            
            cursor = collection.find(query).limit(limit)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error finding listings needing translation: {e}")
            raise
    
    def search_multilingual_listings(
        self,
        search_text: str,
        language: Optional[SupportedLanguage] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search listings using full-text search across multiple languages."""
        try:
            collection = self.get_listings_collection()
            
            # Build text search query
            query = {"$text": {"$search": search_text}}
            
            # Add language filter if specified
            if language:
                lang_key = language.value
                query[f"$or"] = [
                    {f"title.{lang_key}": {"$regex": search_text, "$options": "i"}},
                    {f"description.{lang_key}": {"$regex": search_text, "$options": "i"}}
                ]
            
            # Execute search with text score sorting
            cursor = collection.find(
                query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error searching listings: {e}")
            raise
    
    # Translation Operations
    
    def save_translation_result(self, result: TranslationResult):
        """Save a translation result to the database."""
        try:
            collection = self.get_translations_collection()
            
            result_dict = result.model_dump()
            collection.insert_one(result_dict)
            
            logger.debug(f"Saved translation result: {result.request_id}")
            
        except Exception as e:
            logger.error(f"Error saving translation result: {e}")
            raise
    
    def get_translation_results(
        self,
        listing_id: str,
        field_name: Optional[str] = None,
        target_language: Optional[SupportedLanguage] = None
    ) -> List[Dict[str, Any]]:
        """Get translation results for a listing."""
        try:
            collection = self.get_translations_collection()
            
            query = {"listing_id": listing_id}
            
            if field_name:
                query["field_name"] = field_name
            
            if target_language:
                query["target_language"] = target_language.value
            
            cursor = collection.find(query).sort("completed_at", DESCENDING)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error getting translation results: {e}")
            raise
    
    def save_translation_job(self, job: BatchTranslationJob):
        """Save a batch translation job."""
        try:
            collection = self.get_translation_jobs_collection()
            
            job_dict = job.model_dump()
            collection.insert_one(job_dict)
            
            logger.info(f"Saved translation job: {job.job_id}")
            
        except Exception as e:
            logger.error(f"Error saving translation job: {e}")
            raise
    
    def update_translation_job(
        self,
        job_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update a translation job."""
        try:
            collection = self.get_translation_jobs_collection()
            
            result = collection.update_one(
                {"job_id": job_id},
                {"$set": update_data}
            )
            
            return result.matched_count > 0
            
        except Exception as e:
            logger.error(f"Error updating translation job: {e}")
            raise
    
    def get_translation_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a translation job by ID."""
        try:
            collection = self.get_translation_jobs_collection()
            return collection.find_one({"job_id": job_id})
            
        except Exception as e:
            logger.error(f"Error getting translation job: {e}")
            raise
    
    # Analytics and Reporting
    
    def get_language_distribution(self) -> Dict[str, int]:
        """Get distribution of primary languages across all listings."""
        try:
            collection = self.get_listings_collection()
            
            pipeline = [
                {"$group": {
                    "_id": "$language_analysis.primary_language",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            
            results = collection.aggregate(pipeline)
            distribution = {}
            
            for result in results:
                lang = result["_id"] or "unknown"
                distribution[lang] = result["count"]
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting language distribution: {e}")
            raise
    
    def get_translation_coverage_stats(self) -> Dict[str, Any]:
        """Get statistics about translation coverage across languages."""
        try:
            collection = self.get_listings_collection()
            
            # Count listings with content in each language
            stats = {}
            
            for lang in ['en', 'lv', 'ru']:
                # Count listings with title in this language
                title_count = collection.count_documents({
                    f"title.{lang}": {"$exists": True, "$ne": None}
                })
                
                # Count listings with description in this language
                desc_count = collection.count_documents({
                    f"description.{lang}": {"$exists": True, "$ne": None}
                })
                
                stats[lang] = {
                    "title_count": title_count,
                    "description_count": desc_count,
                    "total_count": max(title_count, desc_count)
                }
            
            # Total listings
            total_listings = collection.count_documents({})
            
            # Calculate coverage percentages
            for lang in stats:
                stats[lang]["title_coverage"] = (
                    stats[lang]["title_count"] / total_listings * 100 
                    if total_listings > 0 else 0
                )
                stats[lang]["description_coverage"] = (
                    stats[lang]["description_count"] / total_listings * 100 
                    if total_listings > 0 else 0
                )
            
            return {
                "total_listings": total_listings,
                "language_stats": stats
            }
            
        except Exception as e:
            logger.error(f"Error getting translation coverage stats: {e}")
            raise
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics for translations."""
        try:
            translations_collection = self.get_translations_collection()
            
            # Quality distribution
            quality_pipeline = [
                {"$group": {
                    "_id": "$quality_assessment",
                    "count": {"$sum": 1}
                }}
            ]
            
            quality_results = translations_collection.aggregate(quality_pipeline)
            quality_distribution = {}
            
            for result in quality_results:
                quality = result["_id"] or "unknown"
                quality_distribution[quality] = result["count"]
            
            # Service usage statistics
            service_pipeline = [
                {"$group": {
                    "_id": "$translation_service",
                    "count": {"$sum": 1},
                    "avg_time": {"$avg": "$translation_time"}
                }},
                {"$sort": {"count": -1}}
            ]
            
            service_results = translations_collection.aggregate(service_pipeline)
            service_stats = {}
            
            for result in service_results:
                service = result["_id"] or "unknown"
                service_stats[service] = {
                    "usage_count": result["count"],
                    "average_time": result["avg_time"]
                }
            
            return {
                "quality_distribution": quality_distribution,
                "service_statistics": service_stats,
                "total_translations": sum(quality_distribution.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting quality metrics: {e}")
            raise
    
    # Utility methods
    
    def _convert_decimals_to_float(self, data: Dict[str, Any]):
        """Recursively convert Decimal fields to float for MongoDB compatibility."""
        from decimal import Decimal
        
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
            elif isinstance(value, dict):
                self._convert_decimals_to_float(value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, Decimal):
                        value[i] = float(item)
                    elif isinstance(item, dict):
                        self._convert_decimals_to_float(item)
    
    def create_backup(self) -> str:
        """Create a backup of multilingual data."""
        # This would implement database backup functionality
        # For now, return a placeholder
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"i18n_backup_{timestamp}"
        logger.info(f"Backup created: {backup_name}")
        return backup_name
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get general database statistics."""
        try:
            stats = {
                "database_name": self.database_name,
                "collections": {}
            }
            
            # Get stats for each collection
            collection_names = [
                self.LISTINGS_COLLECTION,
                self.TRANSLATIONS_COLLECTION,
                self.TRANSLATION_JOBS_COLLECTION
            ]
            
            for collection_name in collection_names:
                collection = self.db[collection_name]
                count = collection.count_documents({})
                
                # Get collection stats
                try:
                    db_stats = self.db.command("collStats", collection_name)
                    size = db_stats.get("size", 0)
                    avg_obj_size = db_stats.get("avgObjSize", 0)
                except:
                    size = 0
                    avg_obj_size = 0
                
                stats["collections"][collection_name] = {
                    "document_count": count,
                    "size_bytes": size,
                    "average_document_size": avg_obj_size
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            raise


# Global database manager instance
_db_manager = None

def get_i18n_db_manager(mongodb_url: str, database_name: str) -> I18nDatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = I18nDatabaseManager(mongodb_url, database_name)
        _db_manager.connect()
    
    return _db_manager


def close_i18n_db_connection():
    """Close global database connection."""
    global _db_manager
    
    if _db_manager:
        _db_manager.disconnect()
        _db_manager = None


# Database migration utilities
class I18nDatabaseMigrator:
    """Utilities for migrating legacy data to multilingual format."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
    
    def migrate_legacy_listings(self, legacy_collection_name: str = "listings") -> Dict[str, int]:
        """Migrate legacy listings to multilingual format."""
        from models.i18n_models import convert_legacy_listing
        
        try:
            legacy_collection = self.db_manager.db[legacy_collection_name]
            multilingual_collection = self.db_manager.get_listings_collection()
            
            # Get all legacy listings
            legacy_listings = legacy_collection.find({})
            
            migrated_count = 0
            error_count = 0
            
            for legacy_listing in legacy_listings:
                try:
                    # Convert to multilingual format
                    multilingual_listing = convert_legacy_listing(legacy_listing)
                    
                    # Insert into multilingual collection
                    listing_dict = multilingual_listing.model_dump()
                    self.db_manager._convert_decimals_to_float(listing_dict)
                    
                    multilingual_collection.insert_one(listing_dict)
                    migrated_count += 1
                    
                    if migrated_count % 100 == 0:
                        logger.info(f"Migrated {migrated_count} listings...")
                    
                except Exception as e:
                    logger.error(f"Error migrating listing {legacy_listing.get('listing_id')}: {e}")
                    error_count += 1
            
            logger.info(f"Migration completed: {migrated_count} migrated, {error_count} errors")
            
            return {
                "migrated": migrated_count,
                "errors": error_count,
                "total_processed": migrated_count + error_count
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise