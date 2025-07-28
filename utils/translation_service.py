"""
Translation Service Integration for ProScrape i18n Pipeline

This module provides comprehensive translation services integration supporting
Google Translate, DeepL, and other translation APIs with caching, quality
assessment, and error handling.
"""

import asyncio
import aiohttp
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from urllib.parse import urlencode
import redis
from decimal import Decimal

from models.i18n_models import (
    SupportedLanguage, TranslationResult, TranslationQuality,
    TranslationStatus, ContentMetadata
)

logger = logging.getLogger(__name__)


@dataclass
class TranslationConfig:
    """Configuration for translation services."""
    google_api_key: Optional[str] = None
    deepl_api_key: Optional[str] = None
    azure_translator_key: Optional[str] = None
    azure_translator_region: Optional[str] = None
    
    # Rate limiting
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    max_text_length: int = 5000
    
    # Caching
    cache_enabled: bool = True
    cache_ttl_hours: int = 24 * 7  # 1 week
    redis_url: str = "redis://localhost:6379/1"
    
    # Quality assessment
    quality_check_enabled: bool = True
    confidence_threshold: float = 0.7
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class RateLimitError(TranslationError):
    """Exception raised when rate limit is exceeded."""
    pass


class TranslationServiceError(TranslationError):
    """Exception raised when translation service fails."""
    pass


class TranslationCache:
    """Redis-based cache for translation results."""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.redis_client = None
        
        if config.cache_enabled:
            try:
                self.redis_client = redis.from_url(config.redis_url)
                self.redis_client.ping()
                logger.info("Translation cache connected to Redis")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis cache: {e}")
                self.redis_client = None
    
    def _get_cache_key(
        self, 
        text: str, 
        source_lang: SupportedLanguage, 
        target_lang: SupportedLanguage,
        service: str
    ) -> str:
        """Generate cache key for translation."""
        content = f"{service}:{source_lang.value}:{target_lang.value}:{text}"
        return f"translation:{hashlib.md5(content.encode()).hexdigest()}"
    
    def get(
        self, 
        text: str, 
        source_lang: SupportedLanguage, 
        target_lang: SupportedLanguage,
        service: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached translation result."""
        if not self.redis_client:
            return None
        
        try:
            key = self._get_cache_key(text, source_lang, target_lang, service)
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        
        return None
    
    def set(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage,
        service: str,
        translation_data: Dict[str, Any]
    ):
        """Cache translation result."""
        if not self.redis_client:
            return
        
        try:
            key = self._get_cache_key(text, source_lang, target_lang, service)
            ttl = self.config.cache_ttl_hours * 3600
            
            # Add cache metadata
            cache_data = {
                **translation_data,
                'cached_at': datetime.utcnow().isoformat(),
                'cache_version': '1.0'
            }
            
            self.redis_client.setex(key, ttl, json.dumps(cache_data))
        except Exception as e:
            logger.debug(f"Cache set error: {e}")
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        if not self.redis_client:
            return
        
        try:
            keys = self.redis_client.keys(f"translation:{pattern}")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")


class RateLimiter:
    """Rate limiter for translation API calls."""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.call_history = []
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding rate limits."""
        now = datetime.utcnow()
        
        # Clean old entries
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        self.call_history = [t for t in self.call_history if t > hour_ago]
        
        # Check limits
        recent_calls = [t for t in self.call_history if t > minute_ago]
        
        if len(recent_calls) >= self.config.requests_per_minute:
            return False
        
        if len(self.call_history) >= self.config.requests_per_hour:
            return False
        
        return True
    
    def record_request(self):
        """Record a request timestamp."""
        self.call_history.append(datetime.utcnow())
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request can be made."""
        if self.can_make_request():
            return 0.0
        
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Find the oldest request in the last minute
        recent_calls = [t for t in self.call_history if t > minute_ago]
        if recent_calls:
            oldest_recent = min(recent_calls)
            wait_until = oldest_recent + timedelta(minutes=1)
            return max(0.0, (wait_until - now).total_seconds())
        
        return 0.0


class BaseTranslationService(ABC):
    """Abstract base class for translation services."""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config)
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def translate_text(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage
    ) -> Dict[str, Any]:
        """Translate text from source to target language."""
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Get the name of the translation service."""
        pass
    
    def _validate_text_length(self, text: str):
        """Validate text length doesn't exceed service limits."""
        if len(text) > self.config.max_text_length:
            raise TranslationError(
                f"Text length {len(text)} exceeds maximum {self.config.max_text_length}"
            )
    
    async def _wait_for_rate_limit(self):
        """Wait if rate limit would be exceeded."""
        wait_time = self.rate_limiter.get_wait_time()
        if wait_time > 0:
            logger.info(f"Rate limit wait: {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
    
    def _assess_translation_quality(
        self,
        original_text: str,
        translated_text: str,
        confidence: Optional[float] = None
    ) -> TranslationQuality:
        """Assess the quality of a translation."""
        if not self.config.quality_check_enabled:
            return TranslationQuality.UNKNOWN
        
        # Basic quality checks
        if not translated_text or not translated_text.strip():
            return TranslationQuality.LOW
        
        # Check if translation is just the original text
        if original_text.strip().lower() == translated_text.strip().lower():
            return TranslationQuality.LOW
        
        # Check confidence score if provided
        if confidence is not None:
            if confidence >= 0.9:
                return TranslationQuality.HIGH
            elif confidence >= self.config.confidence_threshold:
                return TranslationQuality.MEDIUM
            else:
                return TranslationQuality.LOW
        
        # Length-based quality assessment
        original_len = len(original_text.split())
        translated_len = len(translated_text.split())
        
        if translated_len == 0:
            return TranslationQuality.LOW
        
        # Check for extreme length differences (might indicate poor translation)
        length_ratio = translated_len / original_len
        if length_ratio < 0.3 or length_ratio > 3.0:
            return TranslationQuality.LOW
        
        # Default to medium quality if no issues detected
        return TranslationQuality.MEDIUM


class GoogleTranslateService(BaseTranslationService):
    """Google Translate API service implementation."""
    
    BASE_URL = "https://translation.googleapis.com/language/translate/v2"
    
    def get_service_name(self) -> str:
        return "google_translate"
    
    def _map_language_code(self, lang: SupportedLanguage) -> str:
        """Map internal language codes to Google Translate codes."""
        mapping = {
            SupportedLanguage.ENGLISH: "en",
            SupportedLanguage.LATVIAN: "lv", 
            SupportedLanguage.RUSSIAN: "ru"
        }
        return mapping.get(lang, lang.value)
    
    async def translate_text(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage
    ) -> Dict[str, Any]:
        """Translate text using Google Translate API."""
        if not self.config.google_api_key:
            raise TranslationServiceError("Google Translate API key not configured")
        
        self._validate_text_length(text)
        await self._wait_for_rate_limit()
        
        params = {
            'key': self.config.google_api_key,
            'q': text,
            'source': self._map_language_code(source_lang),
            'target': self._map_language_code(target_lang),
            'format': 'text'
        }
        
        start_time = time.time()
        
        try:
            async with self.session.post(self.BASE_URL, data=params) as response:
                self.rate_limiter.record_request()
                
                if response.status == 429:
                    raise RateLimitError("Google Translate rate limit exceeded")
                
                if response.status != 200:
                    error_text = await response.text()
                    raise TranslationServiceError(
                        f"Google Translate API error {response.status}: {error_text}"
                    )
                
                data = await response.json()
                
                if 'data' not in data or 'translations' not in data['data']:
                    raise TranslationServiceError("Invalid response from Google Translate API")
                
                translation = data['data']['translations'][0]
                translated_text = translation['translatedText']
                
                # Google doesn't provide confidence scores in basic API
                quality = self._assess_translation_quality(text, translated_text)
                
                return {
                    'translated_text': translated_text,
                    'confidence': None,
                    'quality': quality,
                    'translation_time': time.time() - start_time,
                    'detected_source_language': translation.get('detectedSourceLanguage'),
                    'service_response': data
                }
                
        except aiohttp.ClientError as e:
            raise TranslationServiceError(f"Google Translate network error: {e}")


class DeepLTranslateService(BaseTranslationService):
    """DeepL API service implementation."""
    
    BASE_URL = "https://api-free.deepl.com/v2/translate"
    PRO_BASE_URL = "https://api.deepl.com/v2/translate"
    
    def get_service_name(self) -> str:
        return "deepl"
    
    def _map_language_code(self, lang: SupportedLanguage) -> str:
        """Map internal language codes to DeepL codes."""
        mapping = {
            SupportedLanguage.ENGLISH: "EN",
            SupportedLanguage.LATVIAN: "LV",
            SupportedLanguage.RUSSIAN: "RU"
        }
        return mapping.get(lang, lang.value.upper())
    
    async def translate_text(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage
    ) -> Dict[str, Any]:
        """Translate text using DeepL API."""
        if not self.config.deepl_api_key:
            raise TranslationServiceError("DeepL API key not configured")
        
        self._validate_text_length(text)
        await self._wait_for_rate_limit()
        
        # Use pro URL if API key ends with :fx (pro account indicator)
        url = self.PRO_BASE_URL if self.config.deepl_api_key.endswith(':fx') else self.BASE_URL
        
        headers = {
            'Authorization': f'DeepL-Auth-Key {self.config.deepl_api_key}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'text': text,
            'source_lang': self._map_language_code(source_lang),
            'target_lang': self._map_language_code(target_lang)
        }
        
        start_time = time.time()
        
        try:
            async with self.session.post(url, headers=headers, data=data) as response:
                self.rate_limiter.record_request()
                
                if response.status == 429:
                    raise RateLimitError("DeepL rate limit exceeded")
                
                if response.status == 456:
                    raise TranslationError("DeepL quota exceeded")
                
                if response.status != 200:
                    error_text = await response.text()
                    raise TranslationServiceError(
                        f"DeepL API error {response.status}: {error_text}"
                    )
                
                data = await response.json()
                
                if 'translations' not in data or not data['translations']:
                    raise TranslationServiceError("Invalid response from DeepL API")
                
                translation = data['translations'][0]
                translated_text = translation['text']
                
                # DeepL provides good quality translations, assess based on content
                quality = self._assess_translation_quality(text, translated_text, 0.85)
                
                return {
                    'translated_text': translated_text,
                    'confidence': 0.85,  # DeepL generally provides high quality
                    'quality': quality,
                    'translation_time': time.time() - start_time,
                    'detected_source_language': translation.get('detected_source_language'),
                    'service_response': data
                }
                
        except aiohttp.ClientError as e:
            raise TranslationServiceError(f"DeepL network error: {e}")


class TranslationServiceManager:
    """Manager for multiple translation services with fallback and caching."""
    
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.cache = TranslationCache(config)
        
        # Initialize available services
        self.services = {}
        
        if config.google_api_key:
            self.services['google'] = GoogleTranslateService(config)
        
        if config.deepl_api_key:
            self.services['deepl'] = DeepLTranslateService(config)
        
        # Default service priority
        self.service_priority = ['deepl', 'google']  # DeepL generally has better quality
        
        if not self.services:
            logger.warning("No translation services configured")
    
    async def translate_text(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage,
        preferred_service: Optional[str] = None,
        use_cache: bool = True
    ) -> TranslationResult:
        """
        Translate text with automatic service selection and caching.
        
        Args:
            text: Text to translate
            source_lang: Source language
            target_lang: Target language
            preferred_service: Preferred translation service
            use_cache: Whether to use caching
            
        Returns:
            TranslationResult object
        """
        if not text or not text.strip():
            raise TranslationError("Empty text cannot be translated")
        
        if source_lang == target_lang:
            # No translation needed
            return TranslationResult(
                request_id=hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:8],
                listing_id="",  # Will be set by caller
                field_name="",  # Will be set by caller
                source_language=source_lang,
                target_language=target_lang,
                original_text=text,
                translated_text=text,
                translation_service="none",
                confidence_score=1.0,
                quality_assessment=TranslationQuality.HIGH,
                translation_time=0.0
            )
        
        text = text.strip()
        
        # Check cache first
        if use_cache:
            cached_result = await self._get_cached_translation(
                text, source_lang, target_lang, preferred_service
            )
            if cached_result:
                return cached_result
        
        # Determine service order
        service_order = self._get_service_order(preferred_service)
        
        last_error = None
        
        for service_name in service_order:
            if service_name not in self.services:
                continue
            
            service = self.services[service_name]
            
            try:
                async with service:
                    result_data = await service.translate_text(text, source_lang, target_lang)
                
                # Create result object
                result = TranslationResult(
                    request_id=hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:8],
                    listing_id="",  # Will be set by caller
                    field_name="",  # Will be set by caller
                    source_language=source_lang,
                    target_language=target_lang,
                    original_text=text,
                    translated_text=result_data['translated_text'],
                    translation_service=service_name,
                    confidence_score=result_data.get('confidence'),
                    quality_assessment=result_data['quality'],
                    translation_time=result_data['translation_time']
                )
                
                # Cache successful result
                if use_cache:
                    await self._cache_translation_result(result, result_data)
                
                return result
                
            except (RateLimitError, TranslationServiceError) as e:
                logger.warning(f"Translation service {service_name} failed: {e}")
                last_error = e
                continue
        
        # All services failed
        raise TranslationError(f"All translation services failed. Last error: {last_error}")
    
    async def translate_batch(
        self,
        texts: List[Tuple[str, SupportedLanguage, SupportedLanguage]],
        preferred_service: Optional[str] = None,
        use_cache: bool = True,
        max_concurrent: int = 5
    ) -> List[TranslationResult]:
        """
        Translate multiple texts concurrently.
        
        Args:
            texts: List of (text, source_lang, target_lang) tuples
            preferred_service: Preferred translation service
            use_cache: Whether to use caching
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of TranslationResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def translate_single(text_data):
            async with semaphore:
                text, source_lang, target_lang = text_data
                try:
                    return await self.translate_text(
                        text, source_lang, target_lang, preferred_service, use_cache
                    )
                except Exception as e:
                    logger.error(f"Batch translation failed for text: {text[:50]}... Error: {e}")
                    # Return error result
                    return TranslationResult(
                        request_id=hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:8],
                        listing_id="",
                        field_name="",
                        source_language=source_lang,
                        target_language=target_lang,
                        original_text=text,
                        translated_text=text,  # Fallback to original
                        translation_service="failed",
                        quality_assessment=TranslationQuality.LOW,
                        translation_time=0.0,
                        error_message=str(e)
                    )
        
        # Execute all translations concurrently
        tasks = [translate_single(text_data) for text_data in texts]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        return results
    
    def _get_service_order(self, preferred_service: Optional[str]) -> List[str]:
        """Get ordered list of services to try."""
        if preferred_service and preferred_service in self.services:
            # Put preferred service first, then others
            order = [preferred_service]
            order.extend([s for s in self.service_priority if s != preferred_service and s in self.services])
            return order
        
        # Use default priority
        return [s for s in self.service_priority if s in self.services]
    
    async def _get_cached_translation(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage,
        preferred_service: Optional[str]
    ) -> Optional[TranslationResult]:
        """Get cached translation result."""
        service_order = self._get_service_order(preferred_service)
        
        for service_name in service_order:
            cached = self.cache.get(text, source_lang, target_lang, service_name)
            if cached:
                return TranslationResult(
                    request_id=cached.get('request_id', 'cached'),
                    listing_id="",
                    field_name="",
                    source_language=source_lang,
                    target_language=target_lang,
                    original_text=text,
                    translated_text=cached['translated_text'],
                    translation_service=service_name,
                    confidence_score=cached.get('confidence'),
                    quality_assessment=TranslationQuality(cached.get('quality', 'unknown')),
                    translation_time=0.0  # Cached, so no translation time
                )
        
        return None
    
    async def _cache_translation_result(
        self, 
        result: TranslationResult, 
        service_data: Dict[str, Any]
    ):
        """Cache translation result."""
        cache_data = {
            'translated_text': result.translated_text,
            'confidence': result.confidence_score,
            'quality': result.quality_assessment.value,
            'service_response': service_data.get('service_response', {})
        }
        
        self.cache.set(
            result.original_text,
            result.source_language,
            result.target_language,
            result.translation_service,
            cache_data
        )
    
    def get_available_services(self) -> List[str]:
        """Get list of available translation services."""
        return list(self.services.keys())
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get statistics about service usage and performance."""
        # This would typically be implemented with persistent storage
        # For now, return basic information
        return {
            'available_services': self.get_available_services(),
            'cache_enabled': self.config.cache_enabled,
            'rate_limit_config': {
                'requests_per_minute': self.config.requests_per_minute,
                'requests_per_hour': self.config.requests_per_hour
            }
        }


# Convenience functions for easy integration
async def translate_text(
    text: str,
    source_lang: SupportedLanguage,
    target_lang: SupportedLanguage,
    config: TranslationConfig,
    preferred_service: Optional[str] = None
) -> TranslationResult:
    """Convenience function for single text translation."""
    manager = TranslationServiceManager(config)
    return await manager.translate_text(text, source_lang, target_lang, preferred_service)


async def translate_multilingual_text(
    text: str,
    source_lang: SupportedLanguage,
    target_languages: List[SupportedLanguage],
    config: TranslationConfig,
    preferred_service: Optional[str] = None
) -> Dict[SupportedLanguage, TranslationResult]:
    """Translate text into multiple target languages."""
    manager = TranslationServiceManager(config)
    
    # Prepare batch data
    batch_data = [(text, source_lang, target_lang) for target_lang in target_languages]
    
    results = await manager.translate_batch(batch_data, preferred_service)
    
    # Map results by target language
    result_map = {}
    for result, target_lang in zip(results, target_languages):
        result_map[target_lang] = result
    
    return result_map