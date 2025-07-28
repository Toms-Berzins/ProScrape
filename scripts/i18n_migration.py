"""
Migration utilities for adding i18n support to existing ProScrape data.

This script provides tools to:
1. Analyze existing data for language detection
2. Migrate listings to i18n format
3. Create multilingual indexes
4. Validate migration results
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import json

from motor.motor_asyncio import AsyncIOMotorClient
from models.i18n_listing import ListingMigration, MultilingualText, MultilingualFeatures, GeoLocation
from utils.database import async_db
from utils.i18n import i18n_manager, SUPPORTED_LANGUAGES
from config.settings import settings

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detect language of text content."""
    
    def __init__(self):
        # Language patterns for basic detection
        self.language_patterns = {
            'lv': [
                r'\b(dzīvoklis|māja|istaba|euro|eur|cena|platība|stāvs)\b',
                r'\b(pārdod|īrē|centrs|rajons|iela|bulvāris)\b',
                r'\b(rīga|jūrmala|liepāja|daugavpils|jelgava)\b',
                r'[ā|ē|ī|ō|ū|č|ģ|ķ|ļ|ņ|š|ž]+'
            ],
            'ru': [
                r'\b(квартира|дом|комната|евро|цена|площадь|этаж)\b',
                r'\b(продам|сдам|центр|район|улица|проспект)\b',
                r'\b(рига|юрмала|лиепая|даугавпилс|елгава)\b',
                r'[а-я]+'
            ],
            'en': [
                r'\b(apartment|house|room|euro|eur|price|area|floor)\b',
                r'\b(sell|rent|centre|center|district|street|avenue)\b',
                r'\b(riga|jurmala|liepaja|daugavpils|jelgava)\b'
            ]
        }
    
    def detect_language(self, text: str) -> str:
        """
        Detect the primary language of text content.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code ('en', 'lv', 'ru')
        """
        if not text:
            return 'en'  # Default fallback
        
        text_lower = text.lower()
        scores = {lang: 0 for lang in self.language_patterns.keys()}
        
        # Score based on pattern matches
        for lang, patterns in self.language_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                scores[lang] += matches
        
        # Additional scoring based on character frequency
        # Latvian has diacritics
        if re.search(r'[āēīōūčģķļņšž]', text_lower):
            scores['lv'] += 5
        
        # Russian has Cyrillic characters
        if re.search(r'[а-я]', text_lower):
            scores['ru'] += 10
        
        # English is default if no strong indicators
        if max(scores.values()) == 0:
            return 'en'
        
        # Return language with highest score
        detected_lang = max(scores, key=lambda x: scores[x])
        logger.debug(f"Detected language: {detected_lang} with scores: {scores}")
        
        return detected_lang
    
    def detect_languages_batch(self, texts: List[str]) -> List[str]:
        """Detect languages for a batch of texts."""
        return [self.detect_language(text) for text in texts]


class I18nMigrator:
    """Main migration class for i18n support."""
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.migration_stats = {
            'total_processed': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'language_distribution': {'en': 0, 'lv': 0, 'ru': 0},
            'start_time': None,
            'end_time': None
        }
    
    async def analyze_existing_data(self) -> Dict[str, Any]:
        """
        Analyze existing data to understand migration scope.
        
        Returns:
            Analysis report with statistics and recommendations
        """
        logger.info("Starting data analysis for i18n migration...")
        
        collection = async_db.get_collection("listings")
        
        # Get total count
        total_count = await collection.count_documents({})
        
        # Sample data for analysis
        sample_size = min(1000, total_count)
        sample_cursor = collection.aggregate([
            {"$sample": {"size": sample_size}}
        ])
        
        sample_listings = await sample_cursor.to_list(length=sample_size)
        
        # Analyze language distribution
        language_counts = {'en': 0, 'lv': 0, 'ru': 0}
        field_analysis = {
            'has_title': 0,
            'has_description': 0,
            'has_features': 0,
            'has_city': 0,
            'has_district': 0,
            'has_coordinates': 0
        }
        
        for listing in sample_listings:
            # Detect language from title and description
            text_content = f"{listing.get('title', '')} {listing.get('description', '')}"
            detected_lang = self.language_detector.detect_language(text_content)
            language_counts[detected_lang] += 1
            
            # Analyze field coverage
            if listing.get('title'):
                field_analysis['has_title'] += 1
            if listing.get('description'):
                field_analysis['has_description'] += 1
            if listing.get('features'):
                field_analysis['has_features'] += 1
            if listing.get('city'):
                field_analysis['has_city'] += 1
            if listing.get('district'):
                field_analysis['has_district'] += 1
            if listing.get('latitude') and listing.get('longitude'):
                field_analysis['has_coordinates'] += 1
        
        # Calculate field coverage percentages
        field_coverage = {
            field: round((count / sample_size) * 100, 2)
            for field, count in field_analysis.items()
        }
        
        # Language distribution percentages
        language_distribution = {
            lang: round((count / sample_size) * 100, 2)
            for lang, count in language_counts.items()
        }
        
        analysis_report = {
            "total_listings": total_count,
            "sample_size": sample_size,
            "language_distribution": language_distribution,
            "field_coverage": field_coverage,
            "migration_recommendations": self._generate_recommendations(
                language_distribution, field_coverage, total_count
            ),
            "estimated_migration_time": self._estimate_migration_time(total_count),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Data analysis completed. Language distribution: {language_distribution}")
        return analysis_report
    
    def _generate_recommendations(
        self, 
        language_dist: Dict[str, float], 
        field_coverage: Dict[str, float],
        total_count: int
    ) -> List[str]:
        """Generate migration recommendations based on analysis."""
        recommendations = []
        
        # Language-based recommendations
        if language_dist['lv'] > 50:
            recommendations.append("High Latvian content detected - prioritize LV translations")
        if language_dist['ru'] > 30:
            recommendations.append("Significant Russian content - ensure RU translation quality")
        if language_dist['en'] < 20:
            recommendations.append("Low English content - consider auto-translation to EN")
        
        # Field coverage recommendations
        if field_coverage['has_description'] < 50:
            recommendations.append("Low description coverage - migration will be faster")
        if field_coverage['has_features'] > 80:
            recommendations.append("High feature coverage - ensure feature translation dictionary is complete")
        if field_coverage['has_coordinates'] < 70:
            recommendations.append("Consider geocoding addresses during migration")
        
        # Scale recommendations
        if total_count > 100000:
            recommendations.append("Large dataset - use batch migration with progress tracking")
            recommendations.append("Consider running migration during low-traffic periods")
        elif total_count > 10000:
            recommendations.append("Medium dataset - batch size of 500-1000 recommended")
        else:
            recommendations.append("Small dataset - can migrate in single batch")
        
        return recommendations
    
    def _estimate_migration_time(self, total_count: int) -> Dict[str, Any]:
        """Estimate migration time based on data size."""
        # Assume ~100-200 records per second processing time
        processing_rate = 150  # records per second
        estimated_seconds = total_count / processing_rate
        
        hours = int(estimated_seconds // 3600)
        minutes = int((estimated_seconds % 3600) // 60)
        seconds = int(estimated_seconds % 60)
        
        return {
            "total_seconds": round(estimated_seconds, 2),
            "formatted_time": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "processing_rate_per_second": processing_rate
        }
    
    async def migrate_listings_batch(
        self, 
        batch_size: int = 1000,
        start_offset: int = 0,
        max_batches: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Migrate listings to i18n format in batches.
        
        Args:
            batch_size: Number of listings to process per batch
            start_offset: Starting offset for resuming migration
            max_batches: Maximum number of batches to process (None for all)
            
        Returns:
            Migration results and statistics
        """
        logger.info(f"Starting i18n migration with batch size {batch_size}")
        self.migration_stats['start_time'] = datetime.utcnow()
        
        collection = async_db.get_collection("listings")
        
        # Get total count
        total_count = await collection.count_documents({})
        total_batches = (total_count + batch_size - 1) // batch_size
        
        if max_batches:
            total_batches = min(total_batches, max_batches)
        
        logger.info(f"Processing {total_batches} batches of {batch_size} records each")
        
        current_offset = start_offset
        
        for batch_num in range(total_batches):
            try:
                # Get batch of listings
                cursor = collection.find({}).skip(current_offset).limit(batch_size)
                batch_listings = await cursor.to_list(length=batch_size)
                
                if not batch_listings:
                    break
                
                logger.info(f"Processing batch {batch_num + 1}/{total_batches} "
                           f"(records {current_offset} to {current_offset + len(batch_listings)})")
                
                # Migrate batch
                batch_results = await self._migrate_listings_batch_internal(batch_listings)
                
                # Update statistics
                self.migration_stats['total_processed'] += batch_results['processed']
                self.migration_stats['successful_migrations'] += batch_results['successful']
                self.migration_stats['failed_migrations'] += batch_results['failed']
                
                for lang in batch_results['language_distribution']:
                    self.migration_stats['language_distribution'][lang] += batch_results['language_distribution'][lang]
                
                # Log progress
                if (batch_num + 1) % 10 == 0:
                    logger.info(f"Progress: {self.migration_stats['total_processed']}/{total_count} "
                               f"({(self.migration_stats['total_processed']/total_count)*100:.1f}%)")
                
                current_offset += len(batch_listings)
                
                # Brief pause to avoid overwhelming the database
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                self.migration_stats['failed_migrations'] += len(batch_listings)
                continue
        
        self.migration_stats['end_time'] = datetime.utcnow()
        
        # Generate final report
        return self._generate_migration_report()
    
    async def _migrate_listings_batch_internal(self, listings: List[Dict]) -> Dict[str, Any]:
        """Migrate a single batch of listings."""
        processed = 0
        successful = 0
        failed = 0
        language_distribution = {'en': 0, 'lv': 0, 'ru': 0}
        
        collection = async_db.get_collection("listings")
        
        for listing in listings:
            try:
                processed += 1
                
                # Detect primary language
                text_content = f"{listing.get('title', '')} {listing.get('description', '')}"
                detected_lang = self.language_detector.detect_language(text_content)
                language_distribution[detected_lang] += 1
                
                # Migrate to i18n format
                migrated_data = ListingMigration.migrate_listing_to_i18n(listing, detected_lang)
                
                # Update the document
                result = await collection.update_one(
                    {"_id": listing["_id"]},
                    {"$set": migrated_data}
                )
                
                if result.modified_count > 0:
                    successful += 1
                else:
                    failed += 1
                    logger.warning(f"Failed to update listing {listing.get('listing_id', 'unknown')}")
                
            except Exception as e:
                failed += 1
                logger.error(f"Error migrating listing {listing.get('listing_id', 'unknown')}: {e}")
        
        return {
            'processed': processed,
            'successful': successful,
            'failed': failed,
            'language_distribution': language_distribution
        }
    
    def _generate_migration_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration report."""
        duration = None
        if self.migration_stats['start_time'] and self.migration_stats['end_time']:
            duration = self.migration_stats['end_time'] - self.migration_stats['start_time']
        
        success_rate = 0
        if self.migration_stats['total_processed'] > 0:
            success_rate = (self.migration_stats['successful_migrations'] / 
                           self.migration_stats['total_processed']) * 100
        
        return {
            "migration_summary": {
                "total_processed": self.migration_stats['total_processed'],
                "successful_migrations": self.migration_stats['successful_migrations'],
                "failed_migrations": self.migration_stats['failed_migrations'],
                "success_rate_percent": round(success_rate, 2)
            },
            "language_distribution": self.migration_stats['language_distribution'],
            "timing": {
                "start_time": self.migration_stats['start_time'].isoformat() if self.migration_stats['start_time'] else None,
                "end_time": self.migration_stats['end_time'].isoformat() if self.migration_stats['end_time'] else None,
                "duration_seconds": duration.total_seconds() if duration else None,
                "records_per_second": (self.migration_stats['total_processed'] / duration.total_seconds()) if duration and duration.total_seconds() > 0 else None
            },
            "recommendations": self._generate_post_migration_recommendations()
        }
    
    def _generate_post_migration_recommendations(self) -> List[str]:
        """Generate recommendations after migration."""
        recommendations = []
        
        if self.migration_stats['failed_migrations'] > 0:
            recommendations.append("Review failed migrations and retry if necessary")
        
        if self.migration_stats['language_distribution']['lv'] > self.migration_stats['language_distribution']['en']:
            recommendations.append("Consider creating English translations for Latvian content")
        
        recommendations.extend([
            "Create database indexes for i18n fields",
            "Test API endpoints with different language parameters", 
            "Update frontend to support language switching",
            "Configure Redis caching for translation performance",
            "Set up monitoring for translation cache hit rates"
        ])
        
        return recommendations
    
    async def create_i18n_indexes(self):
        """Create database indexes optimized for i18n queries."""
        logger.info("Creating i18n database indexes...")
        
        collection = async_db.get_collection("listings")
        
        indexes_to_create = [
            # Language-based indexes
            [("detected_language", 1)],
            [("available_languages", 1)],
            
            # Multilingual content indexes
            [("title_i18n.en", "text"), ("title_i18n.lv", "text"), ("title_i18n.ru", "text")],
            [("description_i18n.en", "text"), ("description_i18n.lv", "text"), ("description_i18n.ru", "text")],
            
            # Location indexes with language support
            [("location.city_i18n.en", 1)],
            [("location.city_i18n.lv", 1)],
            [("location.city_i18n.ru", 1)],
            
            # Compound indexes for common queries
            [("detected_language", 1), ("property_type", 1), ("listing_type", 1)],
            [("location.city_i18n.en", 1), ("property_type", 1)],
            [("location.city_i18n.lv", 1), ("property_type", 1)],
            [("location.city_i18n.ru", 1), ("property_type", 1)]
        ]
        
        created_indexes = []
        
        for index_spec in indexes_to_create:
            try:
                index_name = await collection.create_index(index_spec)
                created_indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_spec}: {e}")
        
        logger.info(f"Created {len(created_indexes)} i18n indexes")
        return created_indexes
    
    async def validate_migration(self, sample_size: int = 100) -> Dict[str, Any]:
        """
        Validate migration results by checking a sample of migrated data.
        
        Args:
            sample_size: Number of records to validate
            
        Returns:
            Validation report
        """
        logger.info(f"Validating migration with sample size {sample_size}")
        
        collection = async_db.get_collection("listings")
        
        # Get sample of migrated records
        sample_cursor = collection.aggregate([
            {"$match": {"detected_language": {"$exists": True}}},
            {"$sample": {"size": sample_size}}
        ])
        
        sample_records = await sample_cursor.to_list(length=sample_size)
        
        validation_results = {
            'total_validated': len(sample_records),
            'valid_migrations': 0,
            'issues_found': [],
            'field_validation': {
                'has_detected_language': 0,
                'has_available_languages': 0,
                'has_i18n_title': 0,
                'has_i18n_description': 0,
                'has_i18n_location': 0
            }
        }
        
        for record in sample_records:
            issues = []
            
            # Check required i18n fields
            if 'detected_language' not in record:
                issues.append("Missing detected_language field")
            else:
                validation_results['field_validation']['has_detected_language'] += 1
            
            if 'available_languages' not in record:
                issues.append("Missing available_languages field")
            else:
                validation_results['field_validation']['has_available_languages'] += 1
            
            # Check i18n content structure
            if 'title_i18n' in record:
                validation_results['field_validation']['has_i18n_title'] += 1
            
            if 'description_i18n' in record:
                validation_results['field_validation']['has_i18n_description'] += 1
            
            if 'location' in record and isinstance(record['location'], dict):
                validation_results['field_validation']['has_i18n_location'] += 1
            
            if not issues:
                validation_results['valid_migrations'] += 1
            else:
                validation_results['issues_found'].extend(issues)
        
        # Calculate validation percentages
        validation_percentages = {
            field: round((count / len(sample_records)) * 100, 2)
            for field, count in validation_results['field_validation'].items()
        }
        
        validation_results['field_validation_percentages'] = validation_percentages
        validation_results['migration_success_rate'] = round(
            (validation_results['valid_migrations'] / len(sample_records)) * 100, 2
        )
        
        logger.info(f"Migration validation completed. Success rate: {validation_results['migration_success_rate']}%")
        
        return validation_results


async def main():
    """Main migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ProScrape i18n Migration Tool")
    parser.add_argument("--action", choices=["analyze", "migrate", "validate", "indexes"], 
                       required=True, help="Action to perform")
    parser.add_argument("--batch-size", type=int, default=1000, 
                       help="Batch size for migration (default: 1000)")
    parser.add_argument("--max-batches", type=int, 
                       help="Maximum number of batches to process")
    parser.add_argument("--start-offset", type=int, default=0,
                       help="Starting offset for resuming migration")
    parser.add_argument("--output-file", type=str,
                       help="Output file for reports (JSON format)")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Connect to database
    await async_db.connect()
    
    migrator = I18nMigrator()
    
    try:
        if args.action == "analyze":
            logger.info("Starting data analysis...")
            report = await migrator.analyze_existing_data()
            
        elif args.action == "migrate":
            logger.info("Starting migration...")
            report = await migrator.migrate_listings_batch(
                batch_size=args.batch_size,
                start_offset=args.start_offset,
                max_batches=args.max_batches
            )
            
        elif args.action == "validate":
            logger.info("Starting validation...")
            report = await migrator.validate_migration()
            
        elif args.action == "indexes":
            logger.info("Creating i18n indexes...")
            indexes = await migrator.create_i18n_indexes()
            report = {"created_indexes": indexes}
        
        # Output report
        print(json.dumps(report, indent=2, default=str))
        
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str, ensure_ascii=False)
            logger.info(f"Report saved to {args.output_file}")
        
    finally:
        await async_db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())