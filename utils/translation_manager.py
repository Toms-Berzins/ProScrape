"""
Translation management service for the ProScrape API.
Handles loading, caching, and serving translations with fallback support.
"""

import json
import os
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any, List, Union
from datetime import datetime, timedelta
from functools import lru_cache
import logging
from dataclasses import dataclass, asdict
import aiofiles

from config.settings import settings
from utils.i18n import SupportedLanguage, get_current_language

logger = logging.getLogger(__name__)


@dataclass
class TranslationMetadata:
    """Metadata for translation entries."""
    created_at: str
    updated_at: str
    source: str = "manual"  # manual, auto, api
    confidence: float = 1.0
    version: str = "1.0"


@dataclass
class TranslationEntry:
    """Individual translation entry with metadata."""
    text: str
    metadata: TranslationMetadata


class TranslationCache:
    """In-memory translation cache with TTL support."""
    
    def __init__(self, ttl_hours: int = 168):  # 1 week default
        self._cache: Dict[str, Dict[str, TranslationEntry]] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._last_cleanup = datetime.utcnow()
    
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        if datetime.utcnow() - self._last_cleanup < timedelta(hours=1):
            return  # Only cleanup every hour
        
        now = datetime.utcnow()
        expired_keys = []
        
        for lang_code, translations in self._cache.items():
            expired_translations = []
            for key, entry in translations.items():
                created_at = datetime.fromisoformat(entry.metadata.created_at)
                if now - created_at > self._ttl:
                    expired_translations.append(key)
            
            for key in expired_translations:
                del translations[key]
                logger.debug(f"Expired translation cache entry: {lang_code}.{key}")
            
            if not translations:
                expired_keys.append(lang_code)
        
        for key in expired_keys:
            del self._cache[key]
        
        self._last_cleanup = now
    
    def get(self, language: str, key: str) -> Optional[TranslationEntry]:
        """Get translation from cache."""
        self._cleanup_expired()
        return self._cache.get(language, {}).get(key)
    
    def set(self, language: str, key: str, entry: TranslationEntry):
        """Set translation in cache."""
        if language not in self._cache:
            self._cache[language] = {}
        self._cache[language][key] = entry
    
    def clear(self, language: str = None):
        """Clear cache for specific language or all languages."""
        if language:
            self._cache.pop(language, None)
        else:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        stats = {
            "total_languages": len(self._cache),
            "total_entries": sum(len(translations) for translations in self._cache.values()),
            "by_language": {
                lang: len(translations) for lang, translations in self._cache.items()
            },
            "last_cleanup": self._last_cleanup.isoformat(),
            "ttl_hours": self._ttl.total_seconds() / 3600
        }
        return stats


class TranslationManager:
    """
    Main translation management service.
    Handles loading, caching, and serving translations with fallback support.
    """
    
    def __init__(
        self,
        translations_dir: str = "translations",
        default_language: str = "lv",
        fallback_language: str = "en"
    ):
        self.translations_dir = Path(translations_dir)
        self.default_language = default_language
        self.fallback_language = fallback_language
        self.cache = TranslationCache(ttl_hours=settings.translation_cache_ttl_hours)
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._loaded_files: Dict[str, float] = {}  # file -> last_modified
        
        # Create translations directory if it doesn't exist
        self.translations_dir.mkdir(exist_ok=True)
        
        # Initialize with empty translations
        for lang in SupportedLanguage:
            self._translations[lang.value] = {}
    
    async def initialize(self):
        """Initialize the translation manager by loading all translation files."""
        logger.info("Initializing translation manager...")
        await self._load_all_translations()
        logger.info(f"Translation manager initialized with {len(self._translations)} languages")
    
    async def _load_all_translations(self):
        """Load all translation files from the translations directory."""
        if not self.translations_dir.exists():
            logger.warning(f"Translations directory does not exist: {self.translations_dir}")
            return
        
        tasks = []
        for lang in SupportedLanguage:
            file_path = self.translations_dir / f"{lang.value}.json"
            if file_path.exists():
                tasks.append(self._load_translation_file(lang.value, file_path))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _load_translation_file(self, language: str, file_path: Path):
        """Load a single translation file."""
        try:
            stat = file_path.stat()
            last_modified = stat.st_mtime
            
            # Check if file was already loaded and hasn't been modified
            if str(file_path) in self._loaded_files:
                if self._loaded_files[str(file_path)] >= last_modified:
                    return  # File hasn't been modified
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                
                # Flatten nested JSON structure
                flattened_data = self._flatten_json(data)
                
                # Validate and process translations
                processed_translations = {}
                for key, value in flattened_data.items():
                    if isinstance(value, str):
                        # Simple string translation
                        processed_translations[key] = TranslationEntry(
                            text=value,
                            metadata=TranslationMetadata(
                                created_at=datetime.utcnow().isoformat(),
                                updated_at=datetime.utcnow().isoformat(),
                                source="file"
                            )
                        )
                    elif isinstance(value, dict) and 'text' in value:
                        # Translation with metadata
                        metadata_dict = value.get('metadata', {})
                        processed_translations[key] = TranslationEntry(
                            text=value['text'],
                            metadata=TranslationMetadata(
                                created_at=metadata_dict.get('created_at', datetime.utcnow().isoformat()),
                                updated_at=metadata_dict.get('updated_at', datetime.utcnow().isoformat()),
                                source=metadata_dict.get('source', 'file'),
                                confidence=metadata_dict.get('confidence', 1.0),
                                version=metadata_dict.get('version', '1.0')
                            )
                        )
                
                # Store in both cache and main dictionary
                for key, entry in processed_translations.items():
                    self.cache.set(language, key, entry)
                    if language not in self._translations:
                        self._translations[language] = {}
                    self._translations[language][key] = entry.text
                
                self._loaded_files[str(file_path)] = last_modified
                logger.info(f"Loaded {len(processed_translations)} translations for {language}")
                
        except Exception as e:
            logger.error(f"Error loading translation file {file_path}: {e}")
    
    def _flatten_json(self, data: Dict[str, Any], parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
        """
        Flatten nested JSON structure into dot-separated keys.
        
        Args:
            data: Nested dictionary to flatten
            parent_key: Parent key prefix
            separator: Key separator (default: '.')
            
        Returns:
            Flattened dictionary with dot-separated keys
        """
        items = []
        
        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                items.extend(self._flatten_json(value, new_key, separator).items())
            else:
                # Keep the value as-is (string, number, boolean, etc.)
                items.append((new_key, value))
        
        return dict(items)
    
    def get_translation(
        self,
        key: str,
        language: str = None,
        fallback: str = None,
        interpolation: Dict[str, Any] = None
    ) -> str:
        """
        Get a translation for the given key and language.
        
        Args:
            key: Translation key (e.g., 'api.error.not_found')
            language: Target language code
            fallback: Custom fallback text if translation not found
            interpolation: Variables to interpolate into the translation
            
        Returns:
            Translated text or fallback
        """
        if language is None:
            language = get_current_language()
        
        # Try cache first
        cached_entry = self.cache.get(language, key)
        if cached_entry:
            translation = cached_entry.text
        else:
            # Try main translations dictionary
            translation = self._translations.get(language, {}).get(key)
        
        # If not found in target language, try fallback language
        if not translation and language != self.fallback_language:
            cached_entry = self.cache.get(self.fallback_language, key)
            if cached_entry:
                translation = cached_entry.text
            else:
                translation = self._translations.get(self.fallback_language, {}).get(key)
        
        # Use custom fallback or key as last resort
        if not translation:
            translation = fallback or key
        
        # Apply interpolation if provided
        if interpolation and translation:
            try:
                translation = translation.format(**interpolation)
            except (KeyError, ValueError) as e:
                logger.warning(f"Translation interpolation failed for key '{key}': {e}")
        
        return translation
    
    def get_translations(self, language: str = None) -> Dict[str, str]:
        """
        Get all translations for a specific language.
        
        Args:
            language: Target language code
            
        Returns:
            Dictionary of all translations for the language
        """
        if language is None:
            language = get_current_language()
        
        # Merge cache and main translations
        all_translations = {}
        
        # Add from main translations
        all_translations.update(self._translations.get(language, {}))
        
        # Add from cache (may override file translations)
        cache_translations = self.cache._cache.get(language, {})
        for key, entry in cache_translations.items():
            all_translations[key] = entry.text
        
        return all_translations
    
    async def add_translation(
        self,
        key: str,
        text: str,
        language: str,
        source: str = "manual",
        confidence: float = 1.0,
        save_to_file: bool = True
    ):
        """
        Add or update a translation.
        
        Args:
            key: Translation key
            text: Translation text
            language: Target language
            source: Source of translation (manual, auto, api)
            confidence: Confidence score (0.0 - 1.0)
            save_to_file: Whether to persist to file
        """
        entry = TranslationEntry(
            text=text,
            metadata=TranslationMetadata(
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                source=source,
                confidence=confidence
            )
        )
        
        # Add to cache
        self.cache.set(language, key, entry)
        
        # Add to main dictionary
        if language not in self._translations:
            self._translations[language] = {}
        self._translations[language][key] = text
        
        # Save to file if requested
        if save_to_file:
            await self._save_translations_to_file(language)
        
        logger.info(f"Added translation for {language}.{key}")
    
    async def _save_translations_to_file(self, language: str):
        """Save translations for a language to file."""
        try:
            file_path = self.translations_dir / f"{language}.json"
            
            # Prepare data for saving (include metadata from cache)
            save_data = {}
            cache_translations = self.cache._cache.get(language, {})
            
            for key, text in self._translations.get(language, {}).items():
                if key in cache_translations:
                    entry = cache_translations[key]
                    save_data[key] = {
                        "text": text,
                        "metadata": asdict(entry.metadata)
                    }
                else:
                    save_data[key] = text
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(save_data, indent=2, ensure_ascii=False))
            
            logger.info(f"Saved translations to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving translations for {language}: {e}")
    
    def translate_dict(
        self,
        data: Dict[str, Any],
        language: str = None,
        key_prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Translate all translatable keys in a dictionary.
        
        Args:
            data: Dictionary to translate
            language: Target language
            key_prefix: Prefix for translation keys
            
        Returns:
            Dictionary with translated values
        """
        if language is None:
            language = get_current_language()
        
        translated = {}
        
        for key, value in data.items():
            translation_key = f"{key_prefix}.{key}" if key_prefix else key
            
            if isinstance(value, str):
                # Try to translate string values
                translated_value = self.get_translation(translation_key, language, fallback=value)
                translated[key] = translated_value
            elif isinstance(value, dict):
                # Recursively translate nested dictionaries
                translated[key] = self.translate_dict(value, language, translation_key)
            elif isinstance(value, list):
                # Handle lists (translate string items)
                translated_list = []
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        item_key = f"{translation_key}.{i}"
                        translated_item = self.get_translation(item_key, language, fallback=item)
                        translated_list.append(translated_item)
                    elif isinstance(item, dict):
                        translated_list.append(self.translate_dict(item, language, f"{translation_key}.{i}"))
                    else:
                        translated_list.append(item)
                translated[key] = translated_list
            else:
                # Keep non-string values as-is
                translated[key] = value
        
        return translated
    
    async def reload_translations(self):
        """Reload all translation files from disk."""
        logger.info("Reloading translations...")
        self._loaded_files.clear()
        self.cache.clear()
        await self._load_all_translations()
        logger.info("Translations reloaded")
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages with metadata."""
        from utils.i18n import get_language_name
        
        languages = []
        for lang in SupportedLanguage:
            lang_code = lang.value
            languages.append({
                "code": lang_code,
                "name": get_language_name(lang_code, lang_code),
                "name_en": get_language_name(lang_code, "en"),
                "translation_count": len(self._translations.get(lang_code, {})),
                "is_default": lang_code == self.default_language
            })
        
        return languages
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get translation statistics."""
        stats = {
            "languages": len(self._translations),
            "total_translations": sum(len(trans) for trans in self._translations.values()),
            "by_language": {
                lang: len(translations) for lang, translations in self._translations.items()
            },
            "cache_stats": self.cache.get_stats(),
            "files_loaded": len(self._loaded_files),
            "last_reload": max(self._loaded_files.values()) if self._loaded_files else None
        }
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for translation manager."""
        try:
            # Check if we have translations for all supported languages
            missing_languages = []
            for lang in SupportedLanguage:
                if not self._translations.get(lang.value):
                    missing_languages.append(lang.value)
            
            # Check if translation files exist
            missing_files = []
            for lang in SupportedLanguage:
                file_path = self.translations_dir / f"{lang.value}.json"
                if not file_path.exists():
                    missing_files.append(f"{lang.value}.json")
            
            status = "healthy"
            issues = []
            
            if missing_languages:
                issues.append(f"Missing translations for languages: {', '.join(missing_languages)}")
                status = "degraded"
            
            if missing_files:
                issues.append(f"Missing translation files: {', '.join(missing_files)}")
                if status != "degraded":
                    status = "warning"
            
            return {
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "issues": issues,
                "statistics": self.get_statistics()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }


# Global translation manager instance
translation_manager = TranslationManager(
    translations_dir="translations",
    default_language=settings.default_language,
    fallback_language="en"
)


# Convenience functions for easy access
def t(key: str, language: str = None, **kwargs) -> str:
    """
    Shorthand function for getting translations.
    
    Args:
        key: Translation key
        language: Target language (optional)
        **kwargs: Variables for interpolation
        
    Returns:
        Translated text
    """
    return translation_manager.get_translation(key, language, interpolation=kwargs)


def translate_response(data: Dict[str, Any], language: str = None) -> Dict[str, Any]:
    """
    Translate a response dictionary.
    
    Args:
        data: Response data to translate
        language: Target language
        
    Returns:
        Translated response data
    """
    return translation_manager.translate_dict(data, language)