#!/usr/bin/env python3
"""
Migration Script for ProScrape i18n Implementation

This script migrates existing real estate data to the new multilingual format,
including language detection, content normalization, and database schema updates.
"""

import sys
import os
import asyncio
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.i18n_database import I18nDatabaseManager, I18nDatabaseMigrator
from utils.language_detection import analyze_listing_languages, SupportedLanguage
from utils.i18n_normalization import I18nNormalizationPipeline, NormalizationConfig
from utils.translation_service import TranslationServiceManager, TranslationConfig
from utils.i18n_performance_optimization import I18nPerformanceOptimizer
from utils.i18n_error_handling import I18nErrorHandler, handle_i18n_errors
from models.i18n_models import (
    convert_legacy_listing, MultilingualListingCreate,
    TranslationRequest, SupportedLanguage
)
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class I18nMigrationManager:
    """Manages the migration process from legacy to i18n format."""
    
    def __init__(
        self,
        mongodb_url: str,
        database_name: str,
        translation_config: Optional[TranslationConfig] = None,
        dry_run: bool = False
    ):
        self.mongodb_url = mongodb_url
        self.database_name = database_name
        self.dry_run = dry_run
        
        # Initialize components
        self.db_manager = I18nDatabaseManager(mongodb_url, database_name)
        self.migrator = I18nDatabaseMigrator(self.db_manager)
        self.normalization_pipeline = I18nNormalizationPipeline()
        self.error_handler = I18nErrorHandler(settings.redis_url, self.db_manager)
        
        # Performance optimizer
        self.performance_optimizer = I18nPerformanceOptimizer(
            settings.redis_url, translation_config=translation_config
        )
        
        # Migration statistics
        self.stats = {
            'total_processed': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'language_detections': 0,
            'normalizations': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
    
    def connect(self):
        """Connect to database and initialize components."""
        try:
            self.db_manager.connect()
            logger.info(f"Connected to MongoDB: {self.database_name}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from database."""
        try:
            self.db_manager.disconnect()
            logger.info("Disconnected from MongoDB")
        except Exception as e:
            logger.warning(f"Error disconnecting from database: {e}")
    
    @handle_i18n_errors("migration_analyze_legacy_data")
    def analyze_legacy_data(
        self,
        legacy_collection: str = "listings",
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze legacy data to understand migration requirements.
        
        Args:
            legacy_collection: Name of the legacy collection
            sample_size: Number of documents to sample for analysis
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"Analyzing legacy data from collection: {legacy_collection}")
        
        try:
            legacy_col = self.db_manager.db[legacy_collection]
            
            # Get total count
            total_count = legacy_col.count_documents({})
            
            # Sample documents for analysis
            pipeline = [{"$sample": {"size": min(sample_size, total_count)}}]
            sample_docs = list(legacy_col.aggregate(pipeline))
            
            # Analyze schema and content
            field_analysis = {}
            language_distribution = {}
            data_quality_issues = []
            
            for doc in sample_docs:
                # Analyze fields
                for field, value in doc.items():
                    if field not in field_analysis:
                        field_analysis[field] = {
                            'present_count': 0,
                            'data_types': set(),
                            'sample_values': []
                        }
                    
                    field_analysis[field]['present_count'] += 1
                    field_analysis[field]['data_types'].add(type(value).__name__)
                    
                    if len(field_analysis[field]['sample_values']) < 3:
                        field_analysis[field]['sample_values'].append(str(value)[:100])
                
                # Analyze language content
                try:
                    language_analysis = analyze_listing_languages(doc)
                    primary_lang = language_analysis.get('primary_language', 'unknown')
                    language_distribution[primary_lang] = language_distribution.get(primary_lang, 0) + 1
                except Exception as e:
                    logger.warning(f"Language analysis failed for document {doc.get('_id')}: {e}")
                    language_distribution['unknown'] = language_distribution.get('unknown', 0) + 1
                
                # Check for data quality issues
                if not doc.get('title'):
                    data_quality_issues.append('missing_title')
                if not doc.get('listing_id'):
                    data_quality_issues.append('missing_listing_id')
                if not doc.get('source_site'):
                    data_quality_issues.append('missing_source_site')
            
            # Convert sets to lists for JSON serialization
            for field_info in field_analysis.values():
                field_info['data_types'] = list(field_info['data_types'])
            
            analysis_results = {
                'legacy_collection': legacy_collection,
                'total_documents': total_count,
                'analyzed_sample_size': len(sample_docs),
                'field_analysis': field_analysis,
                'language_distribution': language_distribution,
                'data_quality_issues': {
                    issue: data_quality_issues.count(issue)
                    for issue in set(data_quality_issues)
                },
                'migration_readiness': self._assess_migration_readiness(
                    field_analysis, data_quality_issues
                ),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Legacy data analysis completed: {total_count} total documents")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Legacy data analysis failed: {e}")
            raise
    
    def _assess_migration_readiness(
        self,
        field_analysis: Dict[str, Any],
        quality_issues: List[str]
    ) -> Dict[str, Any]:
        """Assess readiness for migration based on analysis."""
        required_fields = ['listing_id', 'source_site', 'title']
        missing_required = []
        
        for field in required_fields:
            if field not in field_analysis:
                missing_required.append(field)
        
        # Calculate readiness score
        readiness_score = 1.0
        
        if missing_required:
            readiness_score -= 0.4  # Missing required fields is critical
        
        quality_issue_count = len(quality_issues)
        if quality_issue_count > 0:
            readiness_score -= min(0.4, quality_issue_count * 0.1)
        
        readiness_score = max(0.0, readiness_score)
        
        # Determine readiness level
        if readiness_score >= 0.8:
            readiness_level = "ready"
        elif readiness_score >= 0.6:
            readiness_level = "mostly_ready"
        elif readiness_score >= 0.4:
            readiness_level = "needs_cleanup"
        else:
            readiness_level = "not_ready"
        
        return {
            'readiness_score': readiness_score,
            'readiness_level': readiness_level,
            'missing_required_fields': missing_required,
            'quality_issue_count': quality_issue_count,
            'recommendations': self._get_migration_recommendations(
                readiness_level, missing_required, quality_issues
            )
        }
    
    def _get_migration_recommendations(
        self,
        readiness_level: str,
        missing_fields: List[str],
        quality_issues: List[str]
    ) -> List[str]:
        """Get recommendations for migration preparation."""
        recommendations = []
        
        if readiness_level == "not_ready":
            recommendations.append("Data requires significant cleanup before migration")
        
        if missing_fields:
            recommendations.append(f"Add missing required fields: {', '.join(missing_fields)}")
        
        if 'missing_title' in quality_issues:
            recommendations.append("Clean up missing titles before migration")
        
        if 'missing_listing_id' in quality_issues:
            recommendations.append("Ensure all listings have unique IDs")
        
        if quality_issues:
            recommendations.append("Consider running data quality checks and cleanup")
        
        if readiness_level in ["ready", "mostly_ready"]:
            recommendations.append("Data is ready for migration - proceed with batch processing")
        
        return recommendations
    
    @handle_i18n_errors("migration_migrate_batch")
    async def migrate_batch(
        self,
        legacy_documents: List[Dict[str, Any]],
        enable_translation: bool = False,
        target_languages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Migrate a batch of legacy documents to i18n format.
        
        Args:
            legacy_documents: List of legacy document dictionaries
            enable_translation: Whether to enable automatic translation
            target_languages: List of target language codes for translation
            
        Returns:
            Migration results dictionary
        """
        batch_stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        logger.info(f"Starting batch migration of {len(legacy_documents)} documents")
        
        try:
            # Process documents through optimization pipeline
            if enable_translation and target_languages:
                # Use performance optimizer for translation
                target_langs = []
                for lang_code in target_languages:
                    try:
                        target_langs.append(SupportedLanguage(lang_code))
                    except ValueError:
                        logger.warning(f"Invalid language code: {lang_code}")
                
                if target_langs:
                    optimized_docs, performance_metrics = await self.performance_optimizer.optimize_translation_pipeline(
                        legacy_documents, target_langs, "migration_batch"
                    )
                else:
                    optimized_docs = legacy_documents
            else:
                optimized_docs = legacy_documents
            
            # Convert and save each document
            for i, doc in enumerate(optimized_docs):
                batch_stats['processed'] += 1
                
                try:
                    # Convert to multilingual format
                    multilingual_listing = convert_legacy_listing(doc)
                    
                    # Skip if dry run
                    if self.dry_run:
                        logger.info(f"DRY RUN: Would migrate listing {multilingual_listing.listing_id}")
                        batch_stats['successful'] += 1
                        continue
                    
                    # Save to database
                    new_id = self.db_manager.insert_listing(multilingual_listing)
                    
                    batch_stats['successful'] += 1
                    
                    if (i + 1) % 100 == 0:
                        logger.info(f"Migrated {i + 1}/{len(optimized_docs)} documents")
                
                except Exception as e:
                    batch_stats['failed'] += 1
                    error_msg = f"Failed to migrate document {doc.get('_id', 'unknown')}: {e}"
                    batch_stats['errors'].append(error_msg)
                    logger.error(error_msg)
                    
                    # Handle error through error handler
                    self.error_handler.handle_error(
                        e,
                        {'operation': 'batch_migration', 'document_id': str(doc.get('_id'))},
                        doc,
                        'migrate_batch'
                    )
            
            logger.info(
                f"Batch migration completed: {batch_stats['successful']} successful, "
                f"{batch_stats['failed']} failed"
            )
            
            return batch_stats
            
        except Exception as e:
            logger.error(f"Batch migration error: {e}")
            batch_stats['errors'].append(f"Batch migration error: {e}")
            raise
    
    async def migrate_full_collection(
        self,
        legacy_collection: str = "listings",
        batch_size: int = 100,
        enable_translation: bool = False,
        target_languages: Optional[List[str]] = None,
        start_from_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Migrate an entire collection from legacy to i18n format.
        
        Args:
            legacy_collection: Name of the legacy collection
            batch_size: Number of documents to process per batch
            enable_translation: Whether to enable automatic translation
            target_languages: List of target language codes
            start_from_id: ObjectId to start migration from (for resuming)
            
        Returns:
            Migration results dictionary
        """
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info(f"Starting full collection migration: {legacy_collection}")
        
        try:
            legacy_col = self.db_manager.db[legacy_collection]
            
            # Build query
            query = {}
            if start_from_id:
                from bson import ObjectId
                query['_id'] = {'$gte': ObjectId(start_from_id)}
            
            # Get total count
            total_count = legacy_col.count_documents(query)
            logger.info(f"Total documents to migrate: {total_count}")
            
            # Process in batches
            processed = 0
            cursor = legacy_col.find(query).batch_size(batch_size)
            
            current_batch = []
            
            async for doc in cursor:  # Note: This would need async cursor support
                current_batch.append(doc)
                
                if len(current_batch) >= batch_size:
                    # Process batch
                    batch_results = await self.migrate_batch(
                        current_batch, enable_translation, target_languages
                    )
                    
                    # Update statistics
                    self.stats['total_processed'] += batch_results['processed']
                    self.stats['successful_migrations'] += batch_results['successful']
                    self.stats['failed_migrations'] += batch_results['failed']
                    self.stats['errors'].extend(batch_results['errors'])
                    
                    processed += len(current_batch)
                    current_batch = []
                    
                    # Progress logging
                    progress = (processed / total_count) * 100
                    logger.info(f"Migration progress: {progress:.1f}% ({processed}/{total_count})")
                    
                    # Small delay to prevent overwhelming the system
                    await asyncio.sleep(0.1)
            
            # Process remaining documents
            if current_batch:
                batch_results = await self.migrate_batch(
                    current_batch, enable_translation, target_languages
                )
                
                self.stats['total_processed'] += batch_results['processed']
                self.stats['successful_migrations'] += batch_results['successful']
                self.stats['failed_migrations'] += batch_results['failed']
                self.stats['errors'].extend(batch_results['errors'])
            
            self.stats['end_time'] = datetime.utcnow()
            
            # Generate final report
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            final_results = {
                'migration_completed': True,
                'total_processed': self.stats['total_processed'],
                'successful_migrations': self.stats['successful_migrations'],
                'failed_migrations': self.stats['failed_migrations'],
                'success_rate': (
                    self.stats['successful_migrations'] / self.stats['total_processed']
                    if self.stats['total_processed'] > 0 else 0.0
                ),
                'duration_seconds': duration,
                'documents_per_second': self.stats['total_processed'] / duration if duration > 0 else 0,
                'error_count': len(self.stats['errors']),
                'completed_at': self.stats['end_time'].isoformat()
            }
            
            logger.info(f"Full migration completed: {final_results}")
            return final_results
            
        except Exception as e:
            self.stats['end_time'] = datetime.utcnow()
            logger.error(f"Full migration failed: {e}")
            raise
    
    def validate_migration(
        self,
        sample_size: int = 100,
        legacy_collection: str = "listings"
    ) -> Dict[str, Any]:
        """
        Validate the migration by comparing legacy and migrated data.
        
        Args:
            sample_size: Number of documents to validate
            legacy_collection: Name of the legacy collection
            
        Returns:
            Validation results dictionary
        """
        logger.info(f"Starting migration validation with {sample_size} samples")
        
        validation_results = {
            'validated_count': 0,
            'matching_count': 0,
            'missing_count': 0,
            'content_issues': [],
            'validation_errors': []
        }
        
        try:
            legacy_col = self.db_manager.db[legacy_collection]
            i18n_col = self.db_manager.get_listings_collection()
            
            # Sample legacy documents
            pipeline = [{"$sample": {"size": sample_size}}]
            sample_docs = list(legacy_col.aggregate(pipeline))
            
            for legacy_doc in sample_docs:
                validation_results['validated_count'] += 1
                
                try:
                    listing_id = legacy_doc.get('listing_id')
                    source_site = legacy_doc.get('source_site')
                    
                    if not listing_id or not source_site:
                        validation_results['validation_errors'].append(
                            f"Missing listing_id or source_site in legacy doc {legacy_doc.get('_id')}"
                        )
                        continue
                    
                    # Find corresponding i18n document
                    i18n_doc = i18n_col.find_one({
                        'listing_id': listing_id,
                        'source_site': source_site
                    })
                    
                    if not i18n_doc:
                        validation_results['missing_count'] += 1
                        validation_results['content_issues'].append(
                            f"Missing i18n document for {source_site}:{listing_id}"
                        )
                        continue
                    
                    validation_results['matching_count'] += 1
                    
                    # Validate content integrity
                    content_issues = self._validate_content_integrity(legacy_doc, i18n_doc)
                    validation_results['content_issues'].extend(content_issues)
                
                except Exception as e:
                    validation_results['validation_errors'].append(
                        f"Validation error for document {legacy_doc.get('_id')}: {e}"
                    )
            
            # Calculate validation metrics
            validation_results['match_rate'] = (
                validation_results['matching_count'] / validation_results['validated_count']
                if validation_results['validated_count'] > 0 else 0.0
            )
            
            validation_results['content_issue_rate'] = (
                len(validation_results['content_issues']) / validation_results['validated_count']
                if validation_results['validated_count'] > 0 else 0.0
            )
            
            logger.info(f"Migration validation completed: {validation_results['match_rate']:.1%} match rate")
            return validation_results
            
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            validation_results['validation_errors'].append(f"Validation failed: {e}")
            return validation_results
    
    def _validate_content_integrity(
        self,
        legacy_doc: Dict[str, Any],
        i18n_doc: Dict[str, Any]
    ) -> List[str]:
        """Validate content integrity between legacy and i18n documents."""
        issues = []
        
        # Check key fields
        key_fields = ['listing_id', 'source_site', 'price', 'area_sqm']
        
        for field in key_fields:
            legacy_value = legacy_doc.get(field)
            i18n_value = i18n_doc.get(field)
            
            # Handle nested price field in i18n format
            if field == 'price' and isinstance(i18n_value, dict):
                i18n_value = i18n_value.get('amount')
            
            if legacy_value != i18n_value:
                issues.append(
                    f"Field mismatch in {field}: legacy={legacy_value}, i18n={i18n_value}"
                )
        
        # Check multilingual content
        title_field = i18n_doc.get('title', {})
        if isinstance(title_field, dict):
            # Check if original title is preserved in any language
            legacy_title = legacy_doc.get('title', '')
            found_title = False
            
            for lang in ['en', 'lv', 'ru']:
                if title_field.get(lang) == legacy_title:
                    found_title = True
                    break
            
            if not found_title and legacy_title:
                issues.append(f"Original title not found in multilingual format")
        
        return issues
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate a comprehensive migration report."""
        duration = 0
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # Get error handler statistics
        error_stats = self.error_handler.get_error_statistics()
        
        # Get performance report
        performance_report = self.performance_optimizer.get_performance_report()
        
        return {
            'migration_report': {
                'generated_at': datetime.utcnow().isoformat(),
                'migration_statistics': self.stats,
                'duration_seconds': duration,
                'throughput': {
                    'documents_per_second': (
                        self.stats['total_processed'] / duration
                        if duration > 0 else 0
                    ),
                    'success_rate': (
                        self.stats['successful_migrations'] / self.stats['total_processed']
                        if self.stats['total_processed'] > 0 else 0
                    )
                }
            },
            'error_statistics': error_stats,
            'performance_metrics': performance_report
        }


async def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(description='Migrate ProScrape data to i18n format')
    
    parser.add_argument(
        '--action',
        choices=['analyze', 'migrate', 'validate', 'report'],
        required=True,
        help='Action to perform'
    )
    
    parser.add_argument(
        '--legacy-collection',
        default='listings',
        help='Name of the legacy collection (default: listings)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for processing (default: 100)'
    )
    
    parser.add_argument(
        '--enable-translation',
        action='store_true',
        help='Enable automatic translation during migration'
    )
    
    parser.add_argument(
        '--target-languages',
        nargs='+',
        default=['en', 'lv', 'ru'],
        help='Target languages for translation (default: en lv ru)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without making changes'
    )
    
    parser.add_argument(
        '--start-from-id',
        help='ObjectId to start migration from (for resuming)'
    )
    
    parser.add_argument(
        '--sample-size',
        type=int,
        default=100,
        help='Sample size for analysis/validation (default: 100)'
    )
    
    args = parser.parse_args()
    
    # Initialize migration manager
    translation_config = None
    if args.enable_translation:
        translation_config = TranslationConfig(
            google_api_key=settings.google_translate_api_key,
            deepl_api_key=settings.deepl_api_key,
            redis_url=settings.redis_url
        )
    
    migration_manager = I18nMigrationManager(
        settings.mongodb_url,
        settings.mongodb_database,
        translation_config,
        args.dry_run
    )
    
    try:
        # Connect to database
        migration_manager.connect()
        
        if args.action == 'analyze':
            logger.info("Starting legacy data analysis...")
            analysis_results = migration_manager.analyze_legacy_data(
                args.legacy_collection,
                args.sample_size
            )
            
            print("\n" + "="*50)
            print("LEGACY DATA ANALYSIS RESULTS")
            print("="*50)
            print(f"Total documents: {analysis_results['total_documents']}")
            print(f"Analyzed samples: {analysis_results['analyzed_sample_size']}")
            print(f"Language distribution: {analysis_results['language_distribution']}")
            print(f"Migration readiness: {analysis_results['migration_readiness']['readiness_level']}")
            print(f"Readiness score: {analysis_results['migration_readiness']['readiness_score']:.2f}")
            
            if analysis_results['migration_readiness']['recommendations']:
                print("\nRecommendations:")
                for rec in analysis_results['migration_readiness']['recommendations']:
                    print(f"  - {rec}")
        
        elif args.action == 'migrate':
            logger.info("Starting full collection migration...")
            
            if args.dry_run:
                print("DRY RUN MODE - No changes will be made")
            
            migration_results = await migration_manager.migrate_full_collection(
                args.legacy_collection,
                args.batch_size,
                args.enable_translation,
                args.target_languages,
                args.start_from_id
            )
            
            print("\n" + "="*50)
            print("MIGRATION RESULTS")
            print("="*50)
            print(f"Total processed: {migration_results['total_processed']}")
            print(f"Successful: {migration_results['successful_migrations']}")
            print(f"Failed: {migration_results['failed_migrations']}")
            print(f"Success rate: {migration_results['success_rate']:.1%}")
            print(f"Duration: {migration_results['duration_seconds']:.1f} seconds")
            print(f"Throughput: {migration_results['documents_per_second']:.1f} docs/sec")
        
        elif args.action == 'validate':
            logger.info("Starting migration validation...")
            validation_results = migration_manager.validate_migration(
                args.sample_size,
                args.legacy_collection
            )
            
            print("\n" + "="*50)
            print("MIGRATION VALIDATION RESULTS")
            print("="*50)
            print(f"Validated: {validation_results['validated_count']}")
            print(f"Matching: {validation_results['matching_count']}")
            print(f"Missing: {validation_results['missing_count']}")
            print(f"Match rate: {validation_results['match_rate']:.1%}")
            print(f"Content issues: {len(validation_results['content_issues'])}")
            
            if validation_results['content_issues']:
                print("\nContent Issues:")
                for issue in validation_results['content_issues'][:10]:  # Show first 10
                    print(f"  - {issue}")
        
        elif args.action == 'report':
            logger.info("Generating migration report...")
            report = migration_manager.generate_migration_report()
            
            print("\n" + "="*50)
            print("MIGRATION REPORT")
            print("="*50)
            print(f"Report generated at: {report['migration_report']['generated_at']}")
            
            # Save report to file
            import json
            report_filename = f"migration_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"Detailed report saved to: {report_filename}")
    
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        print("\nMigration interrupted by user")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\nMigration failed: {e}")
        sys.exit(1)
    
    finally:
        # Disconnect from database
        migration_manager.disconnect()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())