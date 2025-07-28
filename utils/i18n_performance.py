"""
Performance optimization utilities for i18n functionality.

Includes caching strategies, batch processing, and performance monitoring
for internationalization operations.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from functools import wraps, lru_cache
from collections import defaultdict
import hashlib
import json

from utils.i18n import i18n_manager, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)


class I18nPerformanceMonitor:
    """Monitor and track i18n performance metrics."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.cache_hits = 0
        self.cache_misses = 0
        self.translation_times = defaultdict(list)
    
    def record_translation_time(self, operation: str, language: str, duration: float):
        """Record translation operation timing."""
        self.translation_times[f"{operation}_{language}"].append(duration)
        self.metrics["translation_times"].append({
            "operation": operation,
            "language": language,
            "duration": duration,
            "timestamp": time.time()
        })
    
    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses += 1
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        cache_stats = self.get_cache_stats()
        
        # Calculate average translation times
        avg_times = {}
        for operation, times in self.translation_times.items():
            if times:
                avg_times[operation] = {
                    "average_ms": round(sum(times) * 1000 / len(times), 2),
                    "min_ms": round(min(times) * 1000, 2),
                    "max_ms": round(max(times) * 1000, 2),
                    "count": len(times)
                }
        
        return {
            "cache_performance": cache_stats,
            "translation_performance": avg_times,
            "total_metrics": len(self.metrics["translation_times"])
        }


# Global performance monitor
perf_monitor = I18nPerformanceMonitor()


def performance_tracked(operation_name: str):
    """Decorator to track performance of i18n operations."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Extract language from kwargs if available
                language = kwargs.get('lang', kwargs.get('language', DEFAULT_LANGUAGE))
                perf_monitor.record_translation_time(operation_name, language, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                language = kwargs.get('lang', kwargs.get('language', DEFAULT_LANGUAGE))
                perf_monitor.record_translation_time(operation_name, language, duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class I18nCacheManager:
    """Advanced caching manager for i18n operations."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.local_cache = {}
        self.cache_ttl = 3600  # 1 hour
        self.max_local_cache_size = 1000
        
        # Cache for different types of translations
        self.translation_cache = {}
        self.formatted_cache = {}
        self.localized_listing_cache = {}
    
    def _generate_cache_key(self, operation: str, *args, **kwargs) -> str:
        """Generate a cache key for the operation."""
        # Create a deterministic hash of the arguments
        key_data = f"{operation}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get_cached_translation(self, key: str, language: str) -> Optional[str]:
        """Get cached translation with fallback to local cache."""
        cache_key = f"i18n_trans:{language}:{key}"
        
        # Try Redis first
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    perf_monitor.record_cache_hit()
                    return cached.decode('utf-8')
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
        
        # Try local cache
        if cache_key in self.local_cache:
            perf_monitor.record_cache_hit()
            return self.local_cache[cache_key]
        
        perf_monitor.record_cache_miss()
        return None
    
    async def set_cached_translation(self, key: str, language: str, value: str):
        """Set cached translation in both Redis and local cache."""
        cache_key = f"i18n_trans:{language}:{key}"
        
        # Set in Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(cache_key, self.cache_ttl, value)
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        
        # Set in local cache with size limit
        if len(self.local_cache) >= self.max_local_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self.local_cache.keys())[:100]
            for old_key in oldest_keys:
                del self.local_cache[old_key]
        
        self.local_cache[cache_key] = value
    
    @performance_tracked("formatted_price_cache")
    async def get_cached_formatted_price(self, price: float, language: str, currency: str) -> Optional[str]:
        """Get cached formatted price."""
        cache_key = self._generate_cache_key("format_price", price, language, currency)
        
        if cache_key in self.formatted_cache:
            perf_monitor.record_cache_hit()
            return self.formatted_cache[cache_key]
        
        perf_monitor.record_cache_miss()
        return None
    
    async def set_cached_formatted_price(self, price: float, language: str, currency: str, formatted: str):
        """Set cached formatted price."""
        cache_key = self._generate_cache_key("format_price", price, language, currency)
        self.formatted_cache[cache_key] = formatted
    
    @performance_tracked("localized_listing_cache")
    async def get_cached_localized_listing(self, listing_id: str, language: str) -> Optional[Dict]:
        """Get cached localized listing."""
        cache_key = f"listing:{listing_id}:{language}"
        
        if cache_key in self.localized_listing_cache:
            perf_monitor.record_cache_hit()
            return self.localized_listing_cache[cache_key]
        
        perf_monitor.record_cache_miss()
        return None
    
    async def set_cached_localized_listing(self, listing_id: str, language: str, data: Dict):
        """Set cached localized listing."""
        cache_key = f"listing:{listing_id}:{language}"
        
        # Limit listing cache size
        if len(self.localized_listing_cache) >= 100:
            # Remove oldest entries
            oldest_keys = list(self.localized_listing_cache.keys())[:20]
            for old_key in oldest_keys:
                del self.localized_listing_cache[old_key]
        
        self.localized_listing_cache[cache_key] = data
    
    def clear_cache(self, cache_type: str = "all"):
        """Clear specific cache or all caches."""
        if cache_type == "all" or cache_type == "local":
            self.local_cache.clear()
        if cache_type == "all" or cache_type == "translation":
            self.translation_cache.clear()
        if cache_type == "all" or cache_type == "formatted":
            self.formatted_cache.clear()
        if cache_type == "all" or cache_type == "listing":
            self.localized_listing_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "local_cache_size": len(self.local_cache),
            "translation_cache_size": len(self.translation_cache),
            "formatted_cache_size": len(self.formatted_cache),
            "listing_cache_size": len(self.localized_listing_cache),
            "performance_stats": perf_monitor.get_cache_stats()
        }


# Global cache manager
cache_manager = I18nCacheManager()


class BatchI18nProcessor:
    """Batch processor for i18n operations to improve performance."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
    
    @performance_tracked("batch_translate_features")
    async def batch_translate_features(
        self, 
        features_list: List[List[str]], 
        language: str
    ) -> List[List[str]]:
        """Batch translate multiple feature lists."""
        # Collect all unique features
        unique_features = set()
        for features in features_list:
            unique_features.update(features)
        
        # Translate unique features once
        feature_translations = {}
        for feature in unique_features:
            translated = i18n_manager.translate_features([feature], language)
            if translated:
                feature_translations[feature] = translated[0]
            else:
                feature_translations[feature] = feature
        
        # Apply translations to all lists
        translated_lists = []
        for features in features_list:
            translated_features = [
                feature_translations.get(feature, feature) 
                for feature in features
            ]
            translated_lists.append(translated_features)
        
        return translated_lists
    
    @performance_tracked("batch_translate_cities")
    async def batch_translate_cities(
        self, 
        cities: List[str], 
        language: str
    ) -> Dict[str, str]:
        """Batch translate city names."""
        translations = {}
        for city in set(cities):  # Remove duplicates
            translated = i18n_manager.translate_city_name(city, language)
            translations[city] = translated
        return translations
    
    @performance_tracked("batch_format_prices")
    async def batch_format_prices(
        self, 
        prices: List[Tuple[float, str]], 
        language: str
    ) -> List[str]:
        """Batch format prices."""
        formatted_prices = []
        for price, currency in prices:
            # Check cache first
            cached = await cache_manager.get_cached_formatted_price(price, language, currency)
            if cached:
                formatted_prices.append(cached)
            else:
                formatted = i18n_manager.format_price(price, language, currency)
                formatted_prices.append(formatted)
                await cache_manager.set_cached_formatted_price(price, language, currency, formatted)
        
        return formatted_prices
    
    @performance_tracked("batch_localize_listings")
    async def batch_localize_listings(
        self, 
        listings: List[Dict], 
        language: str
    ) -> List[Dict]:
        """Batch localize multiple listings."""
        # Pre-process for batch operations
        cities = [listing.get('city', '') for listing in listings if listing.get('city')]
        features_lists = [listing.get('features', []) for listing in listings]
        prices = [
            (float(listing['price']), str(listing.get('price_currency', 'EUR')))
            for listing in listings 
            if listing.get('price') is not None
        ]
        
        # Batch translate
        city_translations = await self.batch_translate_cities(cities, language)
        feature_translations = await self.batch_translate_features(features_lists, language)
        price_formats = await self.batch_format_prices(prices, language)
        
        # Apply to listings
        localized_listings = []
        price_index = 0
        
        for i, listing in enumerate(listings):
            localized = listing.copy()
            
            # Apply city translation
            if listing.get('city') and listing['city'] in city_translations:
                localized['city_localized'] = city_translations[listing['city']]
            
            # Apply feature translation
            if i < len(feature_translations):
                localized['features_localized'] = feature_translations[i]
            
            # Apply price formatting
            if listing.get('price') is not None and price_index < len(price_formats):
                localized['price_formatted'] = price_formats[price_index]
                price_index += 1
            
            # Apply other translations
            if listing.get('property_type'):
                localized['property_type_localized'] = i18n_manager.translate_property_type(
                    listing['property_type'], language
                )
            
            if listing.get('listing_type'):
                localized['listing_type_localized'] = i18n_manager.translate_listing_type(
                    listing['listing_type'], language
                )
            
            # Format dates
            for date_field in ['posted_date', 'updated_date', 'scraped_at']:
                if listing.get(date_field):
                    localized[f"{date_field}_formatted"] = i18n_manager.format_datetime(
                        listing[date_field], language
                    )
            
            localized_listings.append(localized)
        
        return localized_listings


# Global batch processor
batch_processor = BatchI18nProcessor()


@lru_cache(maxsize=1000)
def cached_translate_property_type(property_type: str, language: str) -> str:
    """LRU cached property type translation."""
    return i18n_manager.translate_property_type(property_type, language)


@lru_cache(maxsize=1000)
def cached_translate_city_name(city: str, language: str) -> str:
    """LRU cached city name translation."""
    return i18n_manager.translate_city_name(city, language)


@lru_cache(maxsize=500)
def cached_format_price(price: float, language: str, currency: str) -> str:
    """LRU cached price formatting."""
    return i18n_manager.format_price(price, language, currency)


class LazyI18nLoader:
    """Lazy loading for i18n resources to improve startup time."""
    
    def __init__(self):
        self.loaded_languages = set()
        self.loading_locks = {}
    
    async def ensure_language_loaded(self, language: str):
        """Ensure a language is loaded, loading it if necessary."""
        if language in self.loaded_languages:
            return
        
        # Use asyncio lock to prevent duplicate loading
        if language not in self.loading_locks:
            self.loading_locks[language] = asyncio.Lock()
        
        async with self.loading_locks[language]:
            if language not in self.loaded_languages:
                # Load language-specific resources
                i18n_manager._load_language_translations(language)
                self.loaded_languages.add(language)
                logger.info(f"Lazy loaded i18n resources for language: {language}")
    
    async def preload_common_languages(self):
        """Preload commonly used languages."""
        common_languages = ['en', 'lv', 'ru']
        tasks = [self.ensure_language_loaded(lang) for lang in common_languages]
        await asyncio.gather(*tasks)


# Global lazy loader
lazy_loader = LazyI18nLoader()


def get_i18n_performance_stats() -> Dict[str, Any]:
    """Get comprehensive i18n performance statistics."""
    return {
        "performance_monitor": perf_monitor.get_performance_summary(),
        "cache_manager": cache_manager.get_cache_stats(),
        "lazy_loader": {
            "loaded_languages": list(lazy_loader.loaded_languages),
            "total_loaded": len(lazy_loader.loaded_languages)
        }
    }


async def optimize_i18n_for_request(language: str, expected_operations: List[str]):
    """Optimize i18n system for an expected request pattern."""
    # Ensure language is loaded
    await lazy_loader.ensure_language_loaded(language)
    
    # Preload common translations based on expected operations
    if "listings" in expected_operations:
        # Preload common property types and cities
        common_property_types = ["apartment", "house", "land"]
        common_cities = ["riga", "jurmala", "liepaja"]
        
        for prop_type in common_property_types:
            cached_translate_property_type(prop_type, language)
        
        for city in common_cities:
            cached_translate_city_name(city, language)
    
    logger.debug(f"Optimized i18n for language {language} with operations: {expected_operations}")


async def clear_i18n_caches():
    """Clear all i18n caches for memory management."""
    cache_manager.clear_cache()
    
    # Clear LRU caches
    cached_translate_property_type.cache_clear()
    cached_translate_city_name.cache_clear() 
    cached_format_price.cache_clear()
    
    logger.info("Cleared all i18n caches")