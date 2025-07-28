"""
Multilingual ETL Pipeline Tasks for ProScrape i18n

This module provides Celery tasks for processing multilingual real estate data,
including language detection, translation, duplicate detection, and quality assurance.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from celery import Task, group, chord, chain
from celery.exceptions import Retry

from tasks.celery_app import celery_app
from config.settings import settings

# Import i18n components
from utils.language_detection import analyze_listing_languages, SupportedLanguage
from utils.translation_service import (
    TranslationServiceManager, TranslationConfig, TranslationResult
)
from utils.i18n_normalization import I18nNormalizationPipeline, NormalizationConfig
from utils.i18n_duplicate_detection import (
    DuplicateDetectionPipeline, DuplicateMatchConfig, MatchType
)
from utils.i18n_database import I18nDatabaseManager, I18nDatabaseMigrator
from models.i18n_models import (
    MultilingualListingCreate, TranslationRequest, BatchTranslationJob,
    convert_legacy_listing, SupportedLanguage, TranslationStatus,
    TranslationQuality
)

logger = logging.getLogger(__name__)


class I18nTask(Task):
    """Base class for i18n tasks with error handling and monitoring."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"I18n task {task_id} failed: {exc}")
        # Send notification or alert here
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"I18n task {task_id} completed successfully")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(f"I18n task {task_id} retrying due to: {exc}")


# Language Detection Tasks

@celery_app.task(base=I18nTask, bind=True, max_retries=3, default_retry_delay=60)
def detect_listing_language(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect and analyze languages in a listing.
    
    Args:
        listing_data: Raw listing data dictionary
        
    Returns:
        Updated listing data with language analysis
    """
    try:
        logger.info(f"Detecting language for listing: {listing_data.get('listing_id')}")
        
        # Perform language analysis
        language_analysis = analyze_listing_languages(listing_data)
        
        # Update listing data with analysis results
        updated_data = listing_data.copy()
        updated_data['language_analysis'] = language_analysis
        updated_data['needs_translation'] = True
        
        # Set quality score based on language confidence
        overall_confidence = language_analysis.get('overall_confidence', 0.0)
        updated_data['quality_score'] = overall_confidence
        
        logger.info(
            f"Language detected for {listing_data.get('listing_id')}: "
            f"{language_analysis.get('primary_language')} "
            f"(confidence: {overall_confidence:.2f})"
        )
        
        return updated_data
        
    except Exception as exc:
        logger.error(f"Language detection failed for {listing_data.get('listing_id')}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(base=I18nTask, bind=True)
def batch_detect_languages(self, listing_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process a batch of listings for language detection.
    
    Args:
        listing_batch: List of listing data dictionaries
        
    Returns:
        List of updated listing data with language analysis
    """
    try:
        logger.info(f"Processing language detection batch of {len(listing_batch)} listings")
        
        results = []
        for listing_data in listing_batch:
            try:
                result = detect_listing_language.apply(args=[listing_data])
                results.append(result.get())
            except Exception as e:
                logger.error(f"Failed to detect language for listing {listing_data.get('listing_id')}: {e}")
                results.append(listing_data)  # Return original data on error
        
        logger.info(f"Completed language detection batch: {len(results)} processed")
        return results
        
    except Exception as exc:
        logger.error(f"Batch language detection failed: {exc}")
        raise


# Content Normalization Tasks

@celery_app.task(base=I18nTask, bind=True, max_retries=3, default_retry_delay=30)
def normalize_listing_content(
    self, 
    listing_data: Dict[str, Any],
    config_dict: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Normalize multilingual content in a listing.
    
    Args:
        listing_data: Listing data with language analysis
        config_dict: Optional normalization configuration
        
    Returns:
        Normalized listing data
    """
    try:
        logger.info(f"Normalizing content for listing: {listing_data.get('listing_id')}")
        
        # Create normalization config
        config = NormalizationConfig(**config_dict) if config_dict else NormalizationConfig()
        
        # Initialize normalization pipeline
        pipeline = I18nNormalizationPipeline(config)
        
        # Normalize the listing data
        normalized_data = pipeline.normalize_listing_data(listing_data)
        
        logger.info(f"Content normalized for listing: {listing_data.get('listing_id')}")
        return normalized_data
        
    except Exception as exc:
        logger.error(f"Content normalization failed for {listing_data.get('listing_id')}: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(base=I18nTask, bind=True)
def batch_normalize_content(
    self,
    listing_batch: List[Dict[str, Any]],
    config_dict: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Normalize content for a batch of listings.
    
    Args:
        listing_batch: List of listing data dictionaries
        config_dict: Optional normalization configuration
        
    Returns:
        List of normalized listing data
    """
    try:
        logger.info(f"Processing content normalization batch of {len(listing_batch)} listings")
        
        results = []
        for listing_data in listing_batch:
            try:
                result = normalize_listing_content.apply(args=[listing_data, config_dict])
                results.append(result.get())
            except Exception as e:
                logger.error(f"Failed to normalize content for listing {listing_data.get('listing_id')}: {e}")
                results.append(listing_data)  # Return original data on error
        
        logger.info(f"Completed content normalization batch: {len(results)} processed")
        return results
        
    except Exception as exc:
        logger.error(f"Batch content normalization failed: {exc}")
        raise


# Translation Tasks

@celery_app.task(base=I18nTask, bind=True, max_retries=5, default_retry_delay=120)
def translate_listing_field(
    self,
    listing_id: str,
    source_site: str,
    field_name: str,
    source_language: str,
    target_language: str,
    text_content: str,
    translation_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Translate a specific field of a listing.
    
    Args:
        listing_id: Unique listing identifier
        source_site: Source website
        field_name: Name of the field being translated
        source_language: Source language code
        target_language: Target language code
        text_content: Text to translate
        translation_config: Translation service configuration
        
    Returns:
        Translation result dictionary
    """
    try:
        logger.info(
            f"Translating {field_name} for listing {listing_id} "
            f"from {source_language} to {target_language}"
        )
        
        # Create translation configuration
        config = TranslationConfig(**translation_config)
        
        # Initialize translation manager
        manager = TranslationServiceManager(config)
        
        # Convert language codes
        source_lang = SupportedLanguage(source_language)
        target_lang = SupportedLanguage(target_language)
        
        # Perform translation
        async def translate():
            return await manager.translate_text(
                text_content, source_lang, target_lang
            )
        
        # Run async translation in thread pool
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            translation_result = loop.run_until_complete(translate())
        finally:
            loop.close()
        
        # Set additional fields
        translation_result.listing_id = listing_id
        translation_result.field_name = field_name
        
        # Save translation result to database
        try:
            db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
            db_manager.connect()
            db_manager.save_translation_result(translation_result)
            db_manager.disconnect()
        except Exception as e:
            logger.warning(f"Failed to save translation result to database: {e}")
        
        logger.info(
            f"Translation completed for {field_name} in listing {listing_id} "
            f"(quality: {translation_result.quality_assessment.value})"
        )
        
        return translation_result.model_dump()
        
    except Exception as exc:
        logger.error(f"Translation failed for {listing_id}.{field_name}: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(base=I18nTask, bind=True)
def translate_listing_to_language(
    self,
    listing_id: str,
    source_site: str,
    target_language: str,
    translation_config: Dict[str, Any],
    fields_to_translate: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Translate all specified fields of a listing to a target language.
    
    Args:
        listing_id: Unique listing identifier
        source_site: Source website
        target_language: Target language code
        translation_config: Translation service configuration
        fields_to_translate: List of fields to translate (default: ['title', 'description'])
        
    Returns:
        Dictionary of field translation results
    """
    try:
        logger.info(f"Translating listing {listing_id} to {target_language}")
        
        # Get listing from database
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            listing_data = db_manager.get_listing(listing_id, source_site)
            if not listing_data:
                raise ValueError(f"Listing not found: {listing_id} from {source_site}")
            
            # Determine source language
            language_analysis = listing_data.get('language_analysis', {})
            source_language = language_analysis.get('primary_language', 'unknown')
            
            if source_language == 'unknown':
                raise ValueError(f"Unknown source language for listing {listing_id}")
            
            # Default fields to translate
            if not fields_to_translate:
                fields_to_translate = ['title', 'description']
            
            # Create translation tasks for each field
            translation_tasks = []
            
            for field_name in fields_to_translate:
                # Extract text content for the field
                text_content = None
                
                if field_name in listing_data and listing_data[field_name]:
                    field_data = listing_data[field_name]
                    
                    # Handle multilingual text fields
                    if isinstance(field_data, dict):
                        # Try to get content in source language
                        if source_language in field_data:
                            text_content = field_data[source_language]
                        else:
                            # Find any available content
                            for lang in ['en', 'lv', 'ru']:
                                if lang in field_data and field_data[lang]:
                                    text_content = field_data[lang]
                                    source_language = lang
                                    break
                    else:
                        # Legacy string field
                        text_content = str(field_data)
                
                if text_content and text_content.strip():
                    task = translate_listing_field.si(
                        listing_id, source_site, field_name,
                        source_language, target_language,
                        text_content, translation_config
                    )
                    translation_tasks.append((field_name, task))
            
            # Execute translation tasks in parallel
            results = {}
            
            for field_name, task in translation_tasks:
                try:
                    result = task.apply()
                    results[field_name] = result.get()
                except Exception as e:
                    logger.error(f"Failed to translate {field_name} for listing {listing_id}: {e}")
                    results[field_name] = {"error": str(e)}
            
            logger.info(f"Completed translation of listing {listing_id} to {target_language}")
            return results
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Listing translation failed for {listing_id}: {exc}")
        raise


@celery_app.task(base=I18nTask, bind=True)
def batch_translate_listings(
    self,
    translation_requests: List[Dict[str, Any]],
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a batch of translation requests.
    
    Args:
        translation_requests: List of translation request dictionaries
        job_id: Optional batch job identifier
        
    Returns:
        Batch translation job results
    """
    try:
        if not job_id:
            job_id = str(uuid.uuid4())
        
        logger.info(f"Starting batch translation job {job_id} with {len(translation_requests)} requests")
        
        # Create batch translation job record
        from models.i18n_models import BatchTranslationJob
        
        job = BatchTranslationJob(
            job_id=job_id,
            total_requests=len(translation_requests),
            status='running',
            started_at=datetime.utcnow()
        )
        
        # Save job to database
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            db_manager.save_translation_job(job)
            
            # Process each translation request
            completed_requests = 0
            failed_requests = 0
            
            for request_data in translation_requests:
                try:
                    # Extract request parameters
                    listing_id = request_data['listing_id']
                    source_site = request_data.get('source_site', '')
                    target_language = request_data['target_language']
                    translation_config = request_data.get('translation_config', {})
                    
                    # Execute translation
                    result = translate_listing_to_language.apply(
                        args=[listing_id, source_site, target_language, translation_config]
                    )
                    
                    translation_results = result.get()
                    completed_requests += 1
                    
                    # Update progress
                    progress = (completed_requests + failed_requests) / len(translation_requests) * 100
                    db_manager.update_translation_job(job_id, {
                        'completed_requests': completed_requests,
                        'failed_requests': failed_requests,
                        'progress_percentage': progress
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to translate listing {request_data.get('listing_id')}: {e}")
                    failed_requests += 1
            
            # Update final job status
            job_update = {
                'status': 'completed',
                'completed_at': datetime.utcnow(),
                'completed_requests': completed_requests,
                'failed_requests': failed_requests,
                'progress_percentage': 100.0
            }
            
            db_manager.update_translation_job(job_id, job_update)
            
            logger.info(
                f"Batch translation job {job_id} completed: "
                f"{completed_requests} successful, {failed_requests} failed"
            )
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'total_requests': len(translation_requests),
                'completed_requests': completed_requests,
                'failed_requests': failed_requests
            }
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Batch translation job failed: {exc}")
        
        # Update job status to failed
        try:
            db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
            db_manager.connect()
            db_manager.update_translation_job(job_id or 'unknown', {
                'status': 'failed',
                'completed_at': datetime.utcnow()
            })
            db_manager.disconnect()
        except:
            pass
        
        raise


# Duplicate Detection Tasks

@celery_app.task(base=I18nTask, bind=True, max_retries=2, default_retry_delay=300)
def detect_listing_duplicates(
    self,
    listing_id: str,
    source_site: str,
    config_dict: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Detect duplicates for a specific listing.
    
    Args:
        listing_id: Listing identifier
        source_site: Source website
        config_dict: Optional duplicate detection configuration
        
    Returns:
        List of duplicate match results
    """
    try:
        logger.info(f"Detecting duplicates for listing: {listing_id} from {source_site}")
        
        # Initialize database manager and duplicate detection pipeline
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            # Create duplicate detection config
            config = DuplicateMatchConfig(**config_dict) if config_dict else DuplicateMatchConfig()
            
            # Initialize duplicate detection pipeline
            pipeline = DuplicateDetectionPipeline(db_manager, config)
            
            # Detect duplicates
            matches = pipeline.detect_duplicates_for_listing(
                listing_id, source_site, exclude_same_source=True
            )
            
            # Convert matches to dictionaries for serialization
            match_results = []
            for match in matches:
                match_dict = {
                    'listing1_id': match.listing1_id,
                    'listing2_id': match.listing2_id,
                    'match_type': match.match_type.value,
                    'confidence_score': match.confidence_score,
                    'title_score': match.title_score,
                    'description_score': match.description_score,
                    'address_score': match.address_score,
                    'price_score': match.price_score,
                    'area_score': match.area_score,
                    'coordinate_score': match.coordinate_score,
                    'same_source': match.same_source,
                    'languages_compared': [lang.value for lang in match.languages_compared],
                    'match_reasons': match.match_reasons,
                    'created_at': match.created_at.isoformat()
                }
                match_results.append(match_dict)
            
            logger.info(f"Found {len(matches)} potential duplicates for listing {listing_id}")
            return match_results
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Duplicate detection failed for {listing_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(base=I18nTask, bind=True)
def batch_detect_duplicates(
    self,
    listing_batch: List[Tuple[str, str]],
    config_dict: Optional[Dict[str, Any]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect duplicates for a batch of listings.
    
    Args:
        listing_batch: List of (listing_id, source_site) tuples
        config_dict: Optional duplicate detection configuration
        
    Returns:
        Dictionary mapping listing keys to duplicate results
    """
    try:
        logger.info(f"Processing duplicate detection batch of {len(listing_batch)} listings")
        
        results = {}
        
        for listing_id, source_site in listing_batch:
            listing_key = f"{source_site}:{listing_id}"
            
            try:
                result = detect_listing_duplicates.apply(
                    args=[listing_id, source_site, config_dict]
                )
                duplicates = result.get()
                
                if duplicates:
                    results[listing_key] = duplicates
                    
            except Exception as e:
                logger.error(f"Failed to detect duplicates for {listing_key}: {e}")
                continue
        
        logger.info(f"Completed duplicate detection batch: {len(results)} listings have duplicates")
        return results
        
    except Exception as exc:
        logger.error(f"Batch duplicate detection failed: {exc}")
        raise


# Database Migration Tasks

@celery_app.task(base=I18nTask, bind=True)
def migrate_legacy_listing(self, legacy_listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate a single legacy listing to multilingual format.
    
    Args:
        legacy_listing_data: Legacy listing data dictionary
        
    Returns:
        Migration result dictionary
    """
    try:
        listing_id = legacy_listing_data.get('listing_id', 'unknown')
        logger.info(f"Migrating legacy listing: {listing_id}")
        
        # Convert legacy listing to multilingual format
        multilingual_listing = convert_legacy_listing(legacy_listing_data)
        
        # Save to database
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            new_id = db_manager.insert_listing(multilingual_listing)
            
            logger.info(f"Successfully migrated listing {listing_id} to multilingual format")
            return {
                'status': 'success',
                'listing_id': listing_id,
                'new_id': new_id,
                'migrated_at': datetime.utcnow().isoformat()
            }
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Failed to migrate legacy listing {legacy_listing_data.get('listing_id')}: {exc}")
        return {
            'status': 'error',
            'listing_id': legacy_listing_data.get('listing_id', 'unknown'),
            'error': str(exc)
        }


@celery_app.task(base=I18nTask, bind=True)
def batch_migrate_legacy_listings(
    self,
    legacy_collection_name: str = "listings",
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Migrate all legacy listings to multilingual format.
    
    Args:
        legacy_collection_name: Name of legacy collection
        batch_size: Number of listings to process per batch
        
    Returns:
        Migration summary dictionary
    """
    try:
        logger.info(f"Starting batch migration from collection: {legacy_collection_name}")
        
        # Initialize database manager and migrator
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            migrator = I18nDatabaseMigrator(db_manager)
            
            # Perform migration
            migration_results = migrator.migrate_legacy_listings(legacy_collection_name)
            
            logger.info(
                f"Migration completed: {migration_results['migrated']} migrated, "
                f"{migration_results['errors']} errors"
            )
            
            return {
                'status': 'completed',
                'migrated_count': migration_results['migrated'],
                'error_count': migration_results['errors'],
                'total_processed': migration_results['total_processed'],
                'completed_at': datetime.utcnow().isoformat()
            }
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Batch migration failed: {exc}")
        raise


# Workflow Orchestration Tasks

@celery_app.task(base=I18nTask, bind=True)
def process_listing_full_pipeline(
    self,
    listing_data: Dict[str, Any],
    pipeline_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a listing through the complete i18n pipeline.
    
    Args:
        listing_data: Raw listing data
        pipeline_config: Optional pipeline configuration
        
    Returns:
        Processing results dictionary
    """
    try:
        listing_id = listing_data.get('listing_id', 'unknown')
        logger.info(f"Starting full pipeline processing for listing: {listing_id}")
        
        config = pipeline_config or {}
        
        # Step 1: Language Detection
        logger.info(f"Step 1: Language detection for {listing_id}")
        language_result = detect_listing_language.apply(args=[listing_data])
        processed_data = language_result.get()
        
        # Step 2: Content Normalization
        logger.info(f"Step 2: Content normalization for {listing_id}")
        normalization_config = config.get('normalization', {})
        normalization_result = normalize_listing_content.apply(
            args=[processed_data, normalization_config]
        )
        normalized_data = normalization_result.get()
        
        # Step 3: Save to Multilingual Database
        logger.info(f"Step 3: Saving to database for {listing_id}")
        multilingual_listing = MultilingualListingCreate(**normalized_data)
        
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            new_id = db_manager.insert_listing(multilingual_listing)
            
            # Step 4: Schedule Translation Tasks (if configured)
            translation_tasks = []
            target_languages = config.get('target_languages', [])
            
            if target_languages:
                logger.info(f"Step 4: Scheduling translations for {listing_id}")
                
                translation_config = config.get('translation', {})
                source_site = listing_data.get('source_site', '')
                
                for target_lang in target_languages:
                    task = translate_listing_to_language.si(
                        listing_id, source_site, target_lang, translation_config
                    )
                    translation_tasks.append(target_lang)
                    task.apply_async()
            
            # Step 5: Schedule Duplicate Detection (if configured)
            duplicate_task_id = None
            if config.get('detect_duplicates', False):
                logger.info(f"Step 5: Scheduling duplicate detection for {listing_id}")
                
                duplicate_config = config.get('duplicate_detection', {})
                source_site = listing_data.get('source_site', '')
                
                duplicate_task = detect_listing_duplicates.si(
                    listing_id, source_site, duplicate_config
                )
                duplicate_result = duplicate_task.apply_async()
                duplicate_task_id = duplicate_result.id
            
            logger.info(f"Full pipeline processing completed for listing {listing_id}")
            
            return {
                'status': 'success',
                'listing_id': listing_id,
                'new_database_id': new_id,
                'primary_language': normalized_data.get('language_analysis', {}).get('primary_language'),
                'quality_score': normalized_data.get('quality_score', 0.0),
                'translation_tasks_scheduled': translation_tasks,
                'duplicate_detection_task': duplicate_task_id,
                'completed_at': datetime.utcnow().isoformat()
            }
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Full pipeline processing failed for {listing_data.get('listing_id')}: {exc}")
        raise


@celery_app.task(base=I18nTask, bind=True)
def create_translation_workflow(
    self,
    listing_ids: List[Tuple[str, str]],
    target_languages: List[str],
    translation_config: Dict[str, Any],
    workflow_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a translation workflow for multiple listings and languages.
    
    Args:
        listing_ids: List of (listing_id, source_site) tuples
        target_languages: List of target language codes
        translation_config: Translation service configuration
        workflow_name: Optional workflow name for tracking
        
    Returns:
        Workflow creation result
    """
    try:
        workflow_id = str(uuid.uuid4())
        workflow_name = workflow_name or f"translation_workflow_{workflow_id[:8]}"
        
        logger.info(
            f"Creating translation workflow '{workflow_name}' for "
            f"{len(listing_ids)} listings and {len(target_languages)} languages"
        )
        
        # Create translation requests
        translation_requests = []
        
        for listing_id, source_site in listing_ids:
            for target_lang in target_languages:
                request = {
                    'listing_id': listing_id,
                    'source_site': source_site,
                    'target_language': target_lang,
                    'translation_config': translation_config
                }
                translation_requests.append(request)
        
        # Create batch translation job
        job_result = batch_translate_listings.apply_async(
            args=[translation_requests, workflow_id]
        )
        
        logger.info(f"Translation workflow '{workflow_name}' created with job ID: {workflow_id}")
        
        return {
            'status': 'created',
            'workflow_id': workflow_id,
            'workflow_name': workflow_name,
            'job_task_id': job_result.id,
            'total_listings': len(listing_ids),
            'target_languages': target_languages,
            'total_requests': len(translation_requests),
            'created_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to create translation workflow: {exc}")
        raise


# Monitoring and Maintenance Tasks

@celery_app.task(base=I18nTask, bind=True)
def generate_i18n_report(self) -> Dict[str, Any]:
    """
    Generate a comprehensive i18n status report.
    
    Returns:
        I18n status report dictionary
    """
    try:
        logger.info("Generating i18n status report")
        
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            # Get language distribution
            language_distribution = db_manager.get_language_distribution()
            
            # Get translation coverage stats
            coverage_stats = db_manager.get_translation_coverage_stats()
            
            # Get quality metrics
            quality_metrics = db_manager.get_quality_metrics()
            
            # Get database stats
            db_stats = db_manager.get_database_stats()
            
            report = {
                'report_generated_at': datetime.utcnow().isoformat(),
                'language_distribution': language_distribution,
                'translation_coverage': coverage_stats,
                'quality_metrics': quality_metrics,
                'database_statistics': db_stats
            }
            
            logger.info("I18n status report generated successfully")
            return report
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Failed to generate i18n report: {exc}")
        raise


@celery_app.task(base=I18nTask, bind=True)
def cleanup_failed_translations(self, max_age_days: int = 7) -> Dict[str, Any]:
    """
    Clean up failed translation records older than specified age.
    
    Args:
        max_age_days: Maximum age of failed translations to keep
        
    Returns:
        Cleanup results dictionary
    """
    try:
        logger.info(f"Cleaning up failed translations older than {max_age_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        db_manager = I18nDatabaseManager(settings.mongodb_url, settings.mongodb_database)
        db_manager.connect()
        
        try:
            translations_collection = db_manager.get_translations_collection()
            
            # Find and delete failed translations older than cutoff
            result = translations_collection.delete_many({
                'error_message': {'$exists': True, '$ne': None},
                'completed_at': {'$lt': cutoff_date}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} failed translation records")
            
            return {
                'status': 'completed',
                'deleted_count': result.deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'completed_at': datetime.utcnow().isoformat()
            }
            
        finally:
            db_manager.disconnect()
        
    except Exception as exc:
        logger.error(f"Failed to cleanup translations: {exc}")
        raise


# Periodic Tasks (registered with Celery Beat)

@celery_app.task(base=I18nTask, bind=True)
def periodic_i18n_maintenance(self) -> Dict[str, Any]:
    """
    Perform periodic i18n maintenance tasks.
    
    Returns:
        Maintenance results dictionary
    """
    try:
        logger.info("Starting periodic i18n maintenance")
        
        maintenance_results = {}
        
        # Generate status report
        try:
            report_result = generate_i18n_report.apply()
            maintenance_results['report'] = report_result.get()
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            maintenance_results['report'] = {'error': str(e)}
        
        # Clean up failed translations
        try:
            cleanup_result = cleanup_failed_translations.apply()
            maintenance_results['cleanup'] = cleanup_result.get()
        except Exception as e:
            logger.error(f"Failed to cleanup translations: {e}")
            maintenance_results['cleanup'] = {'error': str(e)}
        
        logger.info("Periodic i18n maintenance completed")
        
        return {
            'status': 'completed',
            'maintenance_results': maintenance_results,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Periodic maintenance failed: {exc}")
        raise


# Task monitoring utilities

def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a specific task."""
    result = celery_app.AsyncResult(task_id)
    
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None,
        'traceback': result.traceback if result.failed() else None
    }


def get_active_i18n_tasks() -> Dict[str, Any]:
    """Get information about active i18n tasks."""
    inspect = celery_app.control.inspect()
    
    active_tasks = inspect.active()
    scheduled_tasks = inspect.scheduled()
    
    # Filter for i18n tasks
    i18n_task_names = [
        'tasks.i18n_tasks.detect_listing_language',
        'tasks.i18n_tasks.normalize_listing_content',
        'tasks.i18n_tasks.translate_listing_field',
        'tasks.i18n_tasks.detect_listing_duplicates',
        'tasks.i18n_tasks.batch_translate_listings'
    ]
    
    active_i18n = {}
    scheduled_i18n = {}
    
    if active_tasks:
        for worker, tasks in active_tasks.items():
            active_i18n[worker] = [
                task for task in tasks 
                if task['name'] in i18n_task_names
            ]
    
    if scheduled_tasks:
        for worker, tasks in scheduled_tasks.items():
            scheduled_i18n[worker] = [
                task for task in tasks 
                if task['name'] in i18n_task_names
            ]
    
    return {
        'active_tasks': active_i18n,
        'scheduled_tasks': scheduled_i18n,
        'timestamp': datetime.utcnow().isoformat()
    }