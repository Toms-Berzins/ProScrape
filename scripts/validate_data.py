#!/usr/bin/env python3
"""
Data validation script for ProScrape
Validates data integrity and consistency in the database
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.listing import Listing
from utils.database import get_database
from utils.logging_config import setup_logging

# Setup logging
logger = setup_logging()

class DataValidator:
    """Data validation and integrity checker"""
    
    def __init__(self):
        self.db = None
        self.collection = None
        self.errors = []
        self.warnings = []
        self.stats = {}
    
    async def initialize(self):
        """Initialize database connection"""
        self.db = await get_database()
        self.collection = self.db.listings
    
    def add_error(self, error: str):
        """Add validation error"""
        self.errors.append(error)
        logger.error(f"Validation error: {error}")
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)
        logger.warning(f"Validation warning: {warning}")
    
    async def validate_basic_structure(self):
        """Validate basic data structure and required fields"""
        
        logger.info("Validating basic data structure...")
        
        # Check total count
        total_count = await self.collection.count_documents({})
        self.stats['total_listings'] = total_count
        
        if total_count == 0:
            self.add_error("No listings found in database")
            return
        
        # Check for required fields
        required_fields = [
            'listing_id', 'source', 'title', 'price', 'area',
            'coordinates', 'posted_date', 'created_at'
        ]
        
        for field in required_fields:
            missing_count = await self.collection.count_documents({field: {"$exists": False}})
            if missing_count > 0:
                self.add_error(f"Missing required field '{field}' in {missing_count} listings")
        
        # Check for empty required fields
        empty_checks = [
            ('listing_id', {"listing_id": {"$in": ["", None]}}),
            ('source', {"source": {"$in": ["", None]}}),
            ('title', {"title": {"$in": ["", None]}}),
        ]
        
        for field_name, query in empty_checks:
            empty_count = await self.collection.count_documents(query)
            if empty_count > 0:
                self.add_error(f"Empty {field_name} in {empty_count} listings")
        
        logger.info(f"Basic structure validation completed. Found {total_count} listings")
    
    async def validate_data_types(self):
        """Validate data types and formats"""
        
        logger.info("Validating data types and formats...")
        
        # Check price data types
        invalid_prices = await self.collection.count_documents({
            "$or": [
                {"price": {"$type": "string"}},
                {"price": {"$lt": 0}},
                {"price": {"$gt": 100000}}  # Unreasonably high price
            ]
        })
        
        if invalid_prices > 0:
            self.add_warning(f"Found {invalid_prices} listings with invalid prices")
        
        # Check coordinates format
        invalid_coords = await self.collection.count_documents({
            "$or": [
                {"coordinates": {"$not": {"$type": "array"}}},
                {"coordinates": {"$size": {"$ne": 2}}},
                {"coordinates.0": {"$not": {"$type": "number"}}},
                {"coordinates.1": {"$not": {"$type": "number"}}}
            ]
        })
        
        if invalid_coords > 0:
            self.add_error(f"Found {invalid_coords} listings with invalid coordinates")
        
        # Check date formats
        invalid_dates = await self.collection.count_documents({
            "$or": [
                {"posted_date": {"$not": {"$type": "date"}}},
                {"created_at": {"$not": {"$type": "date"}}},
                {"updated_at": {"$not": {"$type": "date"}}}
            ]
        })
        
        if invalid_dates > 0:
            self.add_error(f"Found {invalid_dates} listings with invalid date formats")
    
    async def validate_business_logic(self):
        """Validate business logic and data consistency"""
        
        logger.info("Validating business logic...")
        
        # Check for duplicate listing IDs
        pipeline = [
            {"$group": {"_id": "$listing_id", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = await self.collection.aggregate(pipeline).to_list(None)
        if duplicates:
            self.add_error(f"Found {len(duplicates)} duplicate listing IDs")
            for dup in duplicates[:5]:  # Show first 5
                self.add_error(f"  Duplicate ID: {dup['_id']} ({dup['count']} times)")
        
        # Check for future posted dates
        future_dates = await self.collection.count_documents({
            "posted_date": {"$gt": datetime.utcnow()}
        })
        
        if future_dates > 0:
            self.add_warning(f"Found {future_dates} listings with future posted dates")
        
        # Check for very old listings (more than 1 year old)
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        old_listings = await self.collection.count_documents({
            "posted_date": {"$lt": one_year_ago}
        })
        
        if old_listings > 0:
            self.add_warning(f"Found {old_listings} listings older than 1 year")
        
        # Check coordinate boundaries (Latvia approximate bounds)
        # Latvia: 55.67-58.08°N, 20.97-28.24°E
        invalid_coords_bounds = await self.collection.count_documents({
            "$or": [
                {"coordinates.0": {"$lt": 20.0}},  # longitude too west
                {"coordinates.0": {"$gt": 29.0}},  # longitude too east
                {"coordinates.1": {"$lt": 55.0}},  # latitude too south
                {"coordinates.1": {"$gt": 59.0}}   # latitude too north
            ]
        })
        
        if invalid_coords_bounds > 0:
            self.add_warning(f"Found {invalid_coords_bounds} listings with coordinates outside Latvia")
    
    async def validate_sources(self):
        """Validate source-specific data"""
        
        logger.info("Validating source-specific data...")
        
        # Get source statistics
        pipeline = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        source_stats = await self.collection.aggregate(pipeline).to_list(None)
        self.stats['source_distribution'] = {s['_id']: s['count'] for s in source_stats}
        
        # Check for valid sources
        valid_sources = ["ss.com", "city24.lv", "pp.lv"]
        for stat in source_stats:
            if stat['_id'] not in valid_sources:
                self.add_warning(f"Unknown source: {stat['_id']} ({stat['count']} listings)")
        
        # Check for missing sources
        found_sources = {s['_id'] for s in source_stats}
        missing_sources = set(valid_sources) - found_sources
        if missing_sources:
            self.add_warning(f"No listings found for sources: {', '.join(missing_sources)}")
        
        # Check source-specific patterns
        for source in valid_sources:
            if source in found_sources:
                await self._validate_source_patterns(source)
    
    async def _validate_source_patterns(self, source: str):
        """Validate patterns specific to each source"""
        
        source_query = {"source": source}
        source_count = await self.collection.count_documents(source_query)
        
        # Check listing ID patterns
        if source == "ss.com":
            # SS.com listing IDs should start with "ss_"
            invalid_ids = await self.collection.count_documents({
                "source": source,
                "listing_id": {"$not": {"$regex": r"^ss_"}}
            })
            if invalid_ids > 0:
                self.add_warning(f"Found {invalid_ids} SS.com listings with non-standard IDs")
        
        elif source == "city24.lv":
            # City24 listing IDs should start with "city24_"
            invalid_ids = await self.collection.count_documents({
                "source": source,
                "listing_id": {"$not": {"$regex": r"^city24_"}}
            })
            if invalid_ids > 0:
                self.add_warning(f"Found {invalid_ids} City24.lv listings with non-standard IDs")
        
        elif source == "pp.lv":
            # PP.lv listing IDs should start with "pp_"
            invalid_ids = await self.collection.count_documents({
                "source": source,
                "listing_id": {"$not": {"$regex": r"^pp_"}}
            })
            if invalid_ids > 0:
                self.add_warning(f"Found {invalid_ids} PP.lv listings with non-standard IDs")
    
    async def validate_indexes(self):
        """Validate database indexes"""
        
        logger.info("Validating database indexes...")
        
        # Get existing indexes
        indexes = await self.collection.list_indexes().to_list(None)
        index_names = {idx['name'] for idx in indexes}
        
        # Required indexes
        required_indexes = [
            'listing_id_1',  # Unique index on listing_id
            'source_1',      # Index on source
            'posted_date_1', # Index on posted_date
            'coordinates_2dsphere'  # Geospatial index
        ]
        
        missing_indexes = []
        for req_idx in required_indexes:
            if req_idx not in index_names:
                missing_indexes.append(req_idx)
        
        if missing_indexes:
            self.add_warning(f"Missing recommended indexes: {', '.join(missing_indexes)}")
        
        self.stats['indexes'] = list(index_names)
    
    async def generate_quality_metrics(self):
        """Generate data quality metrics"""
        
        logger.info("Generating data quality metrics...")
        
        # Completeness metrics
        total_count = self.stats['total_listings']
        
        # Check optional field completeness
        optional_fields = ['features', 'image_urls', 'updated_at']
        completeness = {}
        
        for field in optional_fields:
            non_empty_count = await self.collection.count_documents({
                field: {"$exists": True, "$ne": [], "$ne": None, "$ne": ""}
            })
            completeness[field] = (non_empty_count / total_count * 100) if total_count > 0 else 0
        
        self.stats['field_completeness'] = completeness
        
        # Price distribution
        price_pipeline = [
            {"$group": {
                "_id": None,
                "avg_price": {"$avg": "$price"},
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"},
                "count": {"$sum": 1}
            }}
        ]
        
        price_stats = await self.collection.aggregate(price_pipeline).to_list(None)
        if price_stats:
            self.stats['price_stats'] = price_stats[0]
        
        # Recent data ratio (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = await self.collection.count_documents({
            "posted_date": {"$gte": thirty_days_ago}
        })
        
        self.stats['recent_data_ratio'] = (recent_count / total_count * 100) if total_count > 0 else 0
    
    async def run_full_validation(self):
        """Run complete validation suite"""
        
        logger.info("Starting full data validation...")
        
        await self.initialize()
        
        # Run all validation checks
        await self.validate_basic_structure()
        await self.validate_data_types()
        await self.validate_business_logic()
        await self.validate_sources()
        await self.validate_indexes()
        await self.generate_quality_metrics()
        
        # Generate report
        self.generate_report()
        
        return len(self.errors) == 0
    
    def generate_report(self):
        """Generate validation report"""
        
        print("\n" + "="*60)
        print("PROSCRAPE DATA VALIDATION REPORT")
        print("="*60)
        
        # Summary
        print(f"Total listings: {self.stats.get('total_listings', 0)}")
        print(f"Validation errors: {len(self.errors)}")
        print(f"Validation warnings: {len(self.warnings)}")
        
        # Source distribution
        if 'source_distribution' in self.stats:
            print("\nSource distribution:")
            for source, count in self.stats['source_distribution'].items():
                print(f"  {source}: {count}")
        
        # Data quality metrics
        if 'field_completeness' in self.stats:
            print("\nField completeness:")
            for field, percentage in self.stats['field_completeness'].items():
                print(f"  {field}: {percentage:.1f}%")
        
        # Price statistics
        if 'price_stats' in self.stats:
            stats = self.stats['price_stats']
            print(f"\nPrice statistics:")
            print(f"  Average: €{stats['avg_price']:.2f}")
            print(f"  Range: €{stats['min_price']:.2f} - €{stats['max_price']:.2f}")
        
        # Recent data
        if 'recent_data_ratio' in self.stats:
            print(f"\nRecent data (last 30 days): {self.stats['recent_data_ratio']:.1f}%")
        
        # Indexes
        if 'indexes' in self.stats:
            print(f"\nDatabase indexes: {len(self.stats['indexes'])}")
            for idx in sorted(self.stats['indexes']):
                print(f"  {idx}")
        
        # Errors
        if self.errors:
            print(f"\nERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ❌ {error}")
        
        # Warnings
        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        
        # Overall status
        print("\n" + "="*60)
        if self.errors:
            print("❌ VALIDATION FAILED - Critical errors found")
        elif self.warnings:
            print("⚠️  VALIDATION PASSED - Warnings present")
        else:
            print("✅ VALIDATION PASSED - All checks successful")
        print("="*60)

async def main():
    """Main validation function"""
    
    print("ProScrape Data Validation Tool")
    print("==============================")
    
    validator = DataValidator()
    
    try:
        success = await validator.run_full_validation()
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        print(f"\n❌ Validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)