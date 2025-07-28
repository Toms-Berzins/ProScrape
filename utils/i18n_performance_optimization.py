"""
Performance Optimization for ProScrape i18n Pipeline

This module provides comprehensive performance optimization for multilingual data
processing, including intelligent caching, batch processing, async operations,
and memory management for high-throughput translation pipelines.
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref
import gc

# Redis for caching
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

# Memory profiling
import sys
import psutil
import os

from models.i18n_models import (
    SupportedLanguage, TranslationResult, MultilingualText,
    TranslationQuality, TranslationStatus
)
from utils.translation_service import TranslationServiceManager, TranslationConfig
from utils.language_detection import LanguageDetector, SupportedLanguage
from config.settings import settings

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level priorities."""
    L1_MEMORY = "l1_memory"      # In-process memory cache
    L2_REDIS = "l2_redis"        # Redis cache
    L3_DATABASE = "l3_database"  # Database cache


class OptimizationType(Enum):
    """Types of performance optimizations."""
    CACHING = "caching"
    BATCHING = "batching"
    ASYNC_PROCESSING = "async_processing"
    MEMORY_MANAGEMENT = "memory_management"
    CONNECTION_POOLING = "connection_pooling"


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    cache_hits: int = 0
    cache_misses: int = 0
    items_processed: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    errors: int = 0
    optimizations_applied: List[OptimizationType] = field(default_factory=list)
    
    def finish(self):
        """Mark operation as finished and calculate metrics."""
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        
        # Get current memory and CPU usage
        process = psutil.Process()
        self.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        self.cpu_usage_percent = process.cpu_percent()
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def get_throughput_per_second(self) -> float:
        """Calculate items processed per second."""
        if self.duration_ms and self.duration_ms > 0:
            return self.items_processed / (self.duration_ms / 1000)
        return 0.0


class MultiLevelCache:
    """Multi-level caching system with L1 memory and L2 Redis."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        l1_max_size: int = 1000,
        l1_ttl_seconds: int = 300,  # 5 minutes
        l2_ttl_seconds: int = 3600  # 1 hour
    ):
        self.l1_max_size = l1_max_size
        self.l1_ttl_seconds = l1_ttl_seconds
        self.l2_ttl_seconds = l2_ttl_seconds
        
        # L1 Cache (In-memory)
        self.l1_cache = {}
        self.l1_timestamps = {}
        self.l1_access_count = {}
        self.l1_lock = threading.RLock()
        
        # L2 Cache (Redis)
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Connected to Redis for L2 cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        
        # Cache statistics
        self.stats = {
            'l1_hits': 0,
            'l1_misses': 0,
            'l2_hits': 0,
            'l2_misses': 0,
            'l1_evictions': 0
        }
    
    def _generate_cache_key(self, key_parts: List[str]) -> str:
        """Generate a cache key from parts."""
        key_string = ":".join(str(part) for part in key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _cleanup_l1_cache(self):
        """Clean up expired L1 cache entries."""
        with self.l1_lock:
            current_time = time.time()
            expired_keys = []
            
            for key, timestamp in self.l1_timestamps.items():
                if current_time - timestamp > self.l1_ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._evict_l1_entry(key)
    
    def _evict_l1_entry(self, key: str):
        """Evict an entry from L1 cache."""
        if key in self.l1_cache:
            del self.l1_cache[key]
            del self.l1_timestamps[key]
            del self.l1_access_count[key]
            self.stats['l1_evictions'] += 1
    
    def _evict_lru_l1_entry(self):
        """Evict least recently used entry from L1 cache."""
        if not self.l1_access_count:
            return
        
        # Find least recently used key
        lru_key = min(self.l1_access_count.keys(), key=lambda k: self.l1_access_count[k])
        self._evict_l1_entry(lru_key)
    
    def get(self, key_parts: List[str]) -> Optional[Any]:
        """Get value from cache (tries L1 then L2)."""
        cache_key = self._generate_cache_key(key_parts)
        
        # Try L1 cache first
        with self.l1_lock:
            if cache_key in self.l1_cache:
                # Check if expired
                if time.time() - self.l1_timestamps[cache_key] <= self.l1_ttl_seconds:
                    self.l1_access_count[cache_key] = time.time()
                    self.stats['l1_hits'] += 1
                    return self.l1_cache[cache_key]
                else:
                    # Expired, remove from L1
                    self._evict_l1_entry(cache_key)
            
            self.stats['l1_misses'] += 1
        
        # Try L2 cache (Redis)
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(f"i18n_cache:{cache_key}")
                if cached_data:
                    value = json.loads(cached_data)
                    self.stats['l2_hits'] += 1
                    
                    # Promote to L1 cache
                    self._set_l1(cache_key, value)
                    return value
            except Exception as e:
                logger.debug(f"L2 cache error: {e}")
        
        self.stats['l2_misses'] += 1
        return None
    
    def set(self, key_parts: List[str], value: Any):
        """Set value in both L1 and L2 cache."""
        cache_key = self._generate_cache_key(key_parts)
        
        # Set in L1 cache
        self._set_l1(cache_key, value)
        
        # Set in L2 cache (Redis)
        if self.redis_client:
            try:
                serialized_value = json.dumps(value, default=str)
                self.redis_client.setex(
                    f"i18n_cache:{cache_key}",
                    self.l2_ttl_seconds,
                    serialized_value
                )
            except Exception as e:
                logger.debug(f"L2 cache set error: {e}")
    
    def _set_l1(self, cache_key: str, value: Any):
        """Set value in L1 cache."""
        with self.l1_lock:
            # Clean up expired entries
            self._cleanup_l1_cache()
            
            # Check if we need to evict entries
            while len(self.l1_cache) >= self.l1_max_size:
                self._evict_lru_l1_entry()
            
            # Set new entry
            self.l1_cache[cache_key] = value
            self.l1_timestamps[cache_key] = time.time()
            self.l1_access_count[cache_key] = time.time()
    
    def invalidate(self, key_parts: List[str]):
        """Invalidate cache entry."""
        cache_key = self._generate_cache_key(key_parts)
        
        # Remove from L1
        with self.l1_lock:
            if cache_key in self.l1_cache:
                self._evict_l1_entry(cache_key)
        
        # Remove from L2
        if self.redis_client:
            try:
                self.redis_client.delete(f"i18n_cache:{cache_key}")
            except Exception as e:
                logger.debug(f"L2 cache invalidate error: {e}")
    
    def clear_all(self):
        """Clear all cache levels."""
        # Clear L1
        with self.l1_lock:
            self.l1_cache.clear()
            self.l1_timestamps.clear()
            self.l1_access_count.clear()
        
        # Clear L2
        if self.redis_client:
            try:
                keys = self.redis_client.keys("i18n_cache:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.debug(f"L2 cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_l1 = self.stats['l1_hits'] + self.stats['l1_misses']
        total_l2 = self.stats['l2_hits'] + self.stats['l2_misses']
        
        return {
            'l1_cache_size': len(self.l1_cache),
            'l1_max_size': self.l1_max_size,
            'l1_hit_rate': self.stats['l1_hits'] / total_l1 if total_l1 > 0 else 0.0,
            'l2_hit_rate': self.stats['l2_hits'] / total_l2 if total_l2 > 0 else 0.0,
            'l1_evictions': self.stats['l1_evictions'],
            'stats': self.stats
        }


class BatchProcessor:
    """Intelligent batch processor for optimizing bulk operations."""
    
    def __init__(
        self,
        batch_size: int = 50,
        max_concurrent_batches: int = 5,
        adaptive_sizing: bool = True
    ):
        self.batch_size = batch_size
        self.initial_batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.adaptive_sizing = adaptive_sizing
        
        # Performance tracking for adaptive sizing
        self.performance_history = []
        self.optimal_batch_size = batch_size
    
    async def process_batches(
        self,
        items: List[Any],
        processor_func: Callable,
        metrics: Optional[PerformanceMetrics] = None
    ) -> List[Any]:
        """
        Process items in optimized batches.
        
        Args:
            items: List of items to process
            processor_func: Async function to process each batch
            metrics: Optional metrics tracking object
            
        Returns:
            List of processed results
        """
        if not items:
            return []
        
        # Apply adaptive batch sizing
        if self.adaptive_sizing:
            self.batch_size = self._calculate_optimal_batch_size(len(items))
        
        # Create batches
        batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        
        # Process batches with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        results = []
        
        async def process_single_batch(batch):
            async with semaphore:
                start_time = time.time()
                try:
                    result = await processor_func(batch)
                    processing_time = time.time() - start_time
                    
                    # Record performance for adaptive sizing
                    if self.adaptive_sizing:
                        self.performance_history.append({
                            'batch_size': len(batch),
                            'processing_time': processing_time,
                            'throughput': len(batch) / processing_time if processing_time > 0 else 0
                        })
                        
                        # Keep only recent history
                        if len(self.performance_history) > 20:
                            self.performance_history = self.performance_history[-20:]
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    if metrics:
                        metrics.errors += 1
                    return []
        
        # Execute all batches concurrently
        batch_tasks = [process_single_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=False)
        
        # Flatten results
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        
        if metrics:
            metrics.items_processed += len(items)
            metrics.optimizations_applied.append(OptimizationType.BATCHING)
        
        return results
    
    def _calculate_optimal_batch_size(self, total_items: int) -> int:
        """Calculate optimal batch size based on performance history."""
        if not self.performance_history:
            return min(self.batch_size, total_items)
        
        # Find batch size with highest throughput
        best_throughput = 0
        best_batch_size = self.batch_size
        
        for record in self.performance_history[-10:]:  # Use recent history
            if record['throughput'] > best_throughput:
                best_throughput = record['throughput']
                best_batch_size = record['batch_size']
        
        # Apply constraints
        optimal_size = max(10, min(best_batch_size, total_items, 200))
        
        # Gradually adjust towards optimal
        if abs(optimal_size - self.batch_size) > 5:
            if optimal_size > self.batch_size:
                self.batch_size = min(self.batch_size + 5, optimal_size)
            else:
                self.batch_size = max(self.batch_size - 5, optimal_size)
        
        return self.batch_size


class AsyncTranslationProcessor:
    """High-performance async processor for translation operations."""
    
    def __init__(
        self,
        cache: MultiLevelCache,
        translation_config: TranslationConfig,
        max_concurrent_translations: int = 10
    ):
        self.cache = cache
        self.translation_config = translation_config
        self.max_concurrent_translations = max_concurrent_translations
        self.translation_manager = None
        self.semaphore = asyncio.Semaphore(max_concurrent_translations)
        
        # Connection pooling for translation services
        self.session_pool = {}
    
    async def _get_translation_manager(self) -> TranslationServiceManager:
        """Get or create translation manager with connection pooling."""
        if not self.translation_manager:
            self.translation_manager = TranslationServiceManager(self.translation_config)
        return self.translation_manager
    
    async def translate_text_with_cache(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage,
        field_name: str = "text",
        use_cache: bool = True
    ) -> Optional[TranslationResult]:
        """
        Translate text with intelligent caching.
        
        Args:
            text: Text to translate
            source_lang: Source language
            target_lang: Target language
            field_name: Name of the field being translated
            use_cache: Whether to use caching
            
        Returns:
            TranslationResult or None
        """
        if not text or not text.strip():
            return None
        
        # Generate cache key
        cache_key = [
            "translation",
            source_lang.value,
            target_lang.value,
            hashlib.md5(text.encode()).hexdigest()
        ]
        
        # Try cache first
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                # Reconstruct TranslationResult from cached data
                try:
                    result = TranslationResult(**cached_result)
                    result.field_name = field_name
                    return result
                except Exception as e:
                    logger.debug(f"Cache deserialization error: {e}")
        
        # Perform translation with rate limiting
        async with self.semaphore:
            try:
                manager = await self._get_translation_manager()
                result = await manager.translate_text(
                    text, source_lang, target_lang, use_cache=False
                )
                
                result.field_name = field_name
                
                # Cache the result
                if use_cache:
                    self.cache.set(cache_key, result.model_dump())
                
                return result
                
            except Exception as e:
                logger.error(f"Translation failed: {e}")
                return None
    
    async def translate_multilingual_text_batch(
        self,
        multilingual_texts: List[Tuple[MultilingualText, str]],  # (text_obj, field_name)
        target_languages: List[SupportedLanguage],
        metrics: Optional[PerformanceMetrics] = None
    ) -> List[Dict[SupportedLanguage, TranslationResult]]:
        """
        Translate a batch of multilingual texts to target languages.
        
        Args:
            multilingual_texts: List of (MultilingualText, field_name) tuples
            target_languages: List of target languages
            metrics: Optional metrics tracking
            
        Returns:
            List of translation results mapped by language
        """
        translation_tasks = []
        
        for text_obj, field_name in multilingual_texts:
            # Determine source language and content
            source_lang = text_obj.primary_language
            if source_lang == SupportedLanguage.UNKNOWN:
                # Try to find any available content
                for lang in [SupportedLanguage.ENGLISH, SupportedLanguage.LATVIAN, SupportedLanguage.RUSSIAN]:
                    content = text_obj.get_content(lang, fallback=False)
                    if content:
                        source_lang = lang
                        break
            
            source_content = text_obj.get_content(source_lang, fallback=True)
            
            if not source_content:
                continue
            
            # Create translation tasks for each target language
            for target_lang in target_languages:
                if target_lang != source_lang and not text_obj.get_content(target_lang, fallback=False):
                    task = self.translate_text_with_cache(
                        source_content, source_lang, target_lang, field_name
                    )
                    translation_tasks.append((text_obj, target_lang, task))
        
        # Execute all translation tasks
        results = []
        completed_tasks = await asyncio.gather(*[task for _, _, task in translation_tasks], return_exceptions=True)
        
        # Process results
        text_results = {}
        for i, (text_obj, target_lang, _) in enumerate(translation_tasks):
            text_id = id(text_obj)
            if text_id not in text_results:
                text_results[text_id] = {}
            
            result = completed_tasks[i]
            if isinstance(result, TranslationResult):
                text_results[text_id][target_lang] = result
                if metrics:
                    metrics.cache_hits += 1
            elif isinstance(result, Exception):
                logger.error(f"Translation task failed: {result}")
                if metrics:
                    metrics.errors += 1
            else:
                if metrics:
                    metrics.cache_misses += 1
        
        # Convert back to list format
        for text_obj, _ in multilingual_texts:
            text_id = id(text_obj)
            results.append(text_results.get(text_id, {}))
        
        if metrics:
            metrics.optimizations_applied.append(OptimizationType.ASYNC_PROCESSING)
        
        return results


class LanguageDetectionOptimizer:
    """Optimized language detection with caching and batching."""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.detector = LanguageDetector()
    
    async def detect_language_with_cache(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Detect language with caching."""
        if not text or not text.strip():
            return {'primary_language': 'unknown', 'confidence': 0.0}
        
        # Generate cache key
        context_hash = hashlib.md5(json.dumps(context or {}, sort_keys=True).encode()).hexdigest()
        cache_key = [
            "language_detection",
            hashlib.md5(text.encode()).hexdigest(),
            context_hash
        ]
        
        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Perform detection
        result = self.detector.detect_language(text, context)
        
        # Convert to serializable format
        serializable_result = {
            'primary_language': result.primary_language.value,
            'confidence': result.confidence,
            'all_probabilities': {
                lang.value: prob for lang, prob in result.all_probabilities.items()
            },
            'detected_method': result.detected_method,
            'text_length': result.text_length,
            'metadata': result.metadata
        }
        
        # Cache the result
        self.cache.set(cache_key, serializable_result)
        
        return serializable_result
    
    async def detect_batch_languages(
        self,
        texts_with_context: List[Tuple[str, Optional[Dict[str, Any]]]],
        batch_processor: BatchProcessor,
        metrics: Optional[PerformanceMetrics] = None
    ) -> List[Dict[str, Any]]:
        """Detect languages for a batch of texts."""
        
        async def process_batch(batch):
            tasks = [
                self.detect_language_with_cache(text, context)
                for text, context in batch
            ]
            return await asyncio.gather(*tasks)
        
        results = await batch_processor.process_batches(
            texts_with_context, process_batch, metrics
        )
        
        if metrics:
            metrics.optimizations_applied.append(OptimizationType.CACHING)
        
        return results


class MemoryManager:
    """Memory management and optimization utilities."""
    
    def __init__(self, max_memory_mb: int = 1000):
        self.max_memory_mb = max_memory_mb
        self.gc_threshold = max_memory_mb * 0.8  # Trigger GC at 80%
        self.monitoring_enabled = True
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    def check_memory_pressure(self) -> bool:
        """Check if memory usage is approaching limits."""
        memory_stats = self.get_memory_usage()
        return memory_stats['rss_mb'] > self.gc_threshold
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization."""
        initial_memory = self.get_memory_usage()['rss_mb']
        
        # Force garbage collection
        gc.collect()
        
        # Additional cleanup for specific objects
        import sys
        
        # Clear module caches if memory pressure is high
        if initial_memory > self.max_memory_mb:
            # Clear some internal caches
            sys.modules.clear() if hasattr(sys.modules, 'clear') else None
        
        final_memory = self.get_memory_usage()['rss_mb']
        freed_mb = initial_memory - final_memory
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'freed_memory_mb': freed_mb,
            'gc_collected': gc.collect()
        }
    
    async def monitor_memory_async(self, interval_seconds: int = 30):
        """Monitor memory usage asynchronously."""
        while self.monitoring_enabled:
            if self.check_memory_pressure():
                logger.warning("Memory pressure detected, performing optimization")
                result = self.optimize_memory()
                logger.info(f"Memory optimization: freed {result['freed_memory_mb']:.1f} MB")
            
            await asyncio.sleep(interval_seconds)


class I18nPerformanceOptimizer:
    """Main performance optimization system for i18n pipeline."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_memory_mb: int = 1000,
        translation_config: Optional[TranslationConfig] = None
    ):
        # Initialize components
        self.cache = MultiLevelCache(redis_url or settings.redis_url)
        self.memory_manager = MemoryManager(max_memory_mb)
        self.batch_processor = BatchProcessor()
        
        # Translation processor
        if translation_config:
            self.translation_processor = AsyncTranslationProcessor(
                self.cache, translation_config
            )
        else:
            self.translation_processor = None
        
        # Language detection optimizer
        self.language_detector = LanguageDetectionOptimizer(self.cache)
        
        # Performance tracking
        self.active_metrics = {}
        self.performance_history = []
    
    def start_performance_tracking(self, operation_name: str) -> PerformanceMetrics:
        """Start tracking performance for an operation."""
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.utcnow()
        )
        
        self.active_metrics[operation_name] = metrics
        return metrics
    
    def finish_performance_tracking(self, operation_name: str) -> Optional[PerformanceMetrics]:
        """Finish tracking performance for an operation."""
        if operation_name in self.active_metrics:
            metrics = self.active_metrics.pop(operation_name)
            metrics.finish()
            
            # Add to history
            self.performance_history.append(metrics)
            
            # Keep only recent history
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            return metrics
        
        return None
    
    async def optimize_translation_pipeline(
        self,
        listings_data: List[Dict[str, Any]],
        target_languages: List[SupportedLanguage],
        operation_name: str = "translation_pipeline"
    ) -> Tuple[List[Dict[str, Any]], PerformanceMetrics]:
        """
        Run an optimized translation pipeline.
        
        Args:
            listings_data: List of listing data dictionaries
            target_languages: Languages to translate to
            operation_name: Name for performance tracking
            
        Returns:
            Tuple of (processed listings, performance metrics)
        """
        metrics = self.start_performance_tracking(operation_name)
        
        try:
            # Start memory monitoring
            memory_monitor_task = asyncio.create_task(
                self.memory_manager.monitor_memory_async()
            )
            
            # Step 1: Batch language detection
            logger.info(f"Starting language detection for {len(listings_data)} listings")
            
            texts_for_detection = []
            for listing in listings_data:
                # Extract text content for language detection
                title = listing.get('title', '')
                description = listing.get('description', '')
                combined_text = f"{title} {description}".strip()
                
                context = {
                    'source_site': listing.get('source_site'),
                    'field_type': 'combined'
                }
                
                texts_for_detection.append((combined_text, context))
            
            # Detect languages in batches
            language_results = await self.language_detector.detect_batch_languages(
                texts_for_detection, self.batch_processor, metrics
            )
            
            # Step 2: Prepare translation tasks
            logger.info("Preparing translation tasks")
            
            if self.translation_processor:
                multilingual_texts = []
                
                for i, listing in enumerate(listings_data):
                    language_result = language_results[i]
                    primary_lang = SupportedLanguage(language_result['primary_language'])
                    
                    # Create multilingual text objects
                    for field_name in ['title', 'description']:
                        if field_name in listing and listing[field_name]:
                            ml_text = MultilingualText()
                            ml_text.set_content(primary_lang, listing[field_name])
                            multilingual_texts.append((ml_text, field_name))
                
                # Step 3: Batch translation
                logger.info(f"Starting translations for {len(multilingual_texts)} text objects")
                
                translation_results = await self.translation_processor.translate_multilingual_text_batch(
                    multilingual_texts, target_languages, metrics
                )
                
                # Step 4: Update listings with translations
                logger.info("Updating listings with translation results")
                
                text_index = 0
                for i, listing in enumerate(listings_data):
                    for field_name in ['title', 'description']:
                        if field_name in listing and listing[field_name]:
                            if text_index < len(translation_results):
                                translations = translation_results[text_index]
                                
                                # Update listing with translated content
                                field_data = {
                                    language_results[i]['primary_language']: listing[field_name]
                                }
                                
                                for target_lang, result in translations.items():
                                    if result and result.translated_text:
                                        field_data[target_lang.value] = result.translated_text
                                
                                listing[f"{field_name}_multilingual"] = field_data
                                text_index += 1
            
            # Step 5: Update language analysis
            for i, listing in enumerate(listings_data):
                listing['language_analysis'] = language_results[i]
                listing['optimized_at'] = datetime.utcnow().isoformat()
            
            # Stop memory monitoring
            self.memory_manager.monitoring_enabled = False
            memory_monitor_task.cancel()
            
            # Final memory optimization
            if self.memory_manager.check_memory_pressure():
                self.memory_manager.optimize_memory()
            
            metrics.optimizations_applied.extend([
                OptimizationType.CACHING,
                OptimizationType.BATCHING,
                OptimizationType.ASYNC_PROCESSING,
                OptimizationType.MEMORY_MANAGEMENT
            ])
            
            logger.info(f"Translation pipeline optimization completed for {len(listings_data)} listings")
            
        except Exception as e:
            logger.error(f"Translation pipeline optimization failed: {e}")
            metrics.errors += 1
            raise
        finally:
            self.finish_performance_tracking(operation_name)
        
        return listings_data, metrics
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        
        # Cache statistics
        cache_stats = self.cache.get_stats()
        
        # Memory statistics
        memory_stats = self.memory_manager.get_memory_usage()
        
        # Performance history analysis
        if self.performance_history:
            recent_metrics = self.performance_history[-10:]
            avg_duration = sum(m.duration_ms or 0 for m in recent_metrics) / len(recent_metrics)
            avg_throughput = sum(m.get_throughput_per_second() for m in recent_metrics) / len(recent_metrics)
            avg_cache_hit_rate = sum(m.get_cache_hit_rate() for m in recent_metrics) / len(recent_metrics)
        else:
            avg_duration = 0
            avg_throughput = 0
            avg_cache_hit_rate = 0
        
        return {
            'report_generated_at': datetime.utcnow().isoformat(),
            'cache_statistics': cache_stats,
            'memory_statistics': memory_stats,
            'performance_summary': {
                'operations_tracked': len(self.performance_history),
                'average_duration_ms': avg_duration,
                'average_throughput_per_second': avg_throughput,
                'average_cache_hit_rate': avg_cache_hit_rate
            },
            'active_operations': list(self.active_metrics.keys()),
            'recent_operations': [
                {
                    'operation_name': m.operation_name,
                    'duration_ms': m.duration_ms,
                    'items_processed': m.items_processed,
                    'cache_hit_rate': m.get_cache_hit_rate(),
                    'optimizations_applied': [opt.value for opt in m.optimizations_applied]
                }
                for m in self.performance_history[-5:]
            ]
        }
    
    def clear_all_caches(self):
        """Clear all caches for maintenance."""
        self.cache.clear_all()
        logger.info("All caches cleared")
    
    async def warmup_caches(self, sample_data: List[Dict[str, Any]]):
        """Warm up caches with sample data."""
        logger.info(f"Warming up caches with {len(sample_data)} samples")
        
        # Warm up language detection cache
        for listing in sample_data[:10]:  # Use first 10 for warmup
            title = listing.get('title', '')
            if title:
                await self.language_detector.detect_language_with_cache(title)
        
        logger.info("Cache warmup completed")


# Convenience functions
def create_performance_optimizer(
    redis_url: Optional[str] = None,
    translation_config: Optional[TranslationConfig] = None
) -> I18nPerformanceOptimizer:
    """Create a performance optimizer with default settings."""
    return I18nPerformanceOptimizer(
        redis_url=redis_url or settings.redis_url,
        translation_config=translation_config
    )


async def optimize_listing_processing(
    listings: List[Dict[str, Any]],
    target_languages: List[str],
    optimizer: Optional[I18nPerformanceOptimizer] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Convenience function for optimized listing processing."""
    if not optimizer:
        optimizer = create_performance_optimizer()
    
    # Convert string languages to SupportedLanguage enum
    supported_langs = []
    for lang_code in target_languages:
        try:
            supported_langs.append(SupportedLanguage(lang_code))
        except ValueError:
            logger.warning(f"Unsupported language code: {lang_code}")
    
    # Run optimization
    processed_listings, metrics = await optimizer.optimize_translation_pipeline(
        listings, supported_langs
    )
    
    # Generate performance report
    performance_report = optimizer.get_performance_report()
    
    return processed_listings, performance_report