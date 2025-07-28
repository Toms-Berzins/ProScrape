"""
Internationalization utilities for the ProScrape API.
Provides language detection, formatting, and locale-specific utilities.
"""

import re
import json
import locale
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, List, Union, Any
from enum import Enum
from contextvars import ContextVar
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Context variable to store current language per request
current_language: ContextVar[str] = ContextVar('current_language', default='lv')
current_request_id: ContextVar[str] = ContextVar('current_request_id', default='')


class SupportedLanguage(str, Enum):
    """Enumeration of supported languages."""
    ENGLISH = "en"
    LATVIAN = "lv"
    RUSSIAN = "ru"


class LocaleFormat:
    """Locale-specific formatting configurations."""
    
    FORMATS = {
        'en': {
            'currency_symbol': '€',
            'currency_position': 'after',  # €1,500 vs 1,500€
            'decimal_separator': '.',
            'thousands_separator': ',',
            'date_format': '%m/%d/%Y',
            'datetime_format': '%m/%d/%Y %I:%M %p',
            'number_format': '{:,.2f}',
            'area_unit': 'sqm',
            'area_unit_display': 'sq.m.',
            'room_singular': 'room',
            'room_plural': 'rooms',
            'floor_suffix': 'th',
            'direction_abbrev': {'north': 'N', 'south': 'S', 'east': 'E', 'west': 'W'}
        },
        'lv': {
            'currency_symbol': '€',
            'currency_position': 'before',  # €1 500 vs 1 500€
            'decimal_separator': ',',
            'thousands_separator': ' ',
            'date_format': '%d.%m.%Y',
            'datetime_format': '%d.%m.%Y %H:%M',
            'number_format': '{:,.2f}',
            'area_unit': 'sqm',
            'area_unit_display': 'm²',
            'room_singular': 'istaba',
            'room_plural': 'istabas',
            'floor_suffix': '.',
            'direction_abbrev': {'north': 'Z', 'south': 'D', 'east': 'A', 'west': 'R'}
        },
        'ru': {
            'currency_symbol': '€',
            'currency_position': 'after',  # 1 500 €
            'decimal_separator': ',',
            'thousands_separator': ' ',
            'date_format': '%d.%m.%Y',
            'datetime_format': '%d.%m.%Y %H:%M',
            'number_format': '{:,.2f}',
            'area_unit': 'sqm',
            'area_unit_display': 'кв.м.',
            'room_singular': 'комната',
            'room_plural': 'комнат',
            'floor_suffix': '-й',
            'direction_abbrev': {'north': 'С', 'south': 'Ю', 'east': 'В', 'west': 'З'}
        }
    }


class LanguageDetector:
    """Language detection utilities."""
    
    @staticmethod
    def detect_from_accept_language(accept_language: str) -> str:
        """
        Detect language from Accept-Language header.
        
        Args:
            accept_language: HTTP Accept-Language header value
            
        Returns:
            Language code ('en', 'lv', 'ru') or default 'lv'
        """
        if not accept_language:
            return SupportedLanguage.LATVIAN
            
        # Parse Accept-Language header (e.g., "en-US,en;q=0.9,lv;q=0.8,ru;q=0.7")
        languages = []
        for part in accept_language.split(','):
            if ';q=' in part:
                lang, quality = part.split(';q=')
                try:
                    quality = float(quality)
                except ValueError:
                    quality = 1.0
            else:
                lang = part
                quality = 1.0
            
            # Extract primary language code
            lang = lang.strip().split('-')[0].lower()
            if lang in [e.value for e in SupportedLanguage]:
                languages.append((lang, quality))
        
        # Sort by quality and return the highest supported language
        if languages:
            languages.sort(key=lambda x: x[1], reverse=True)
            return languages[0][0]
        
        return SupportedLanguage.LATVIAN
    
    @staticmethod
    def detect_from_text(text: str) -> str:
        """
        Detect language from text content using simple heuristics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code ('en', 'lv', 'ru') or 'lv' if uncertain
        """
        if not text:
            return SupportedLanguage.LATVIAN
        
        text = text.lower()
        
        # Cyrillic characters indicate Russian
        if re.search(r'[а-я]', text):
            return SupportedLanguage.RUSSIAN
        
        # Latvian-specific characters and common words
        latvian_indicators = [
            r'[āēīōū]',  # Latvian diacritics
            r'\b(un|ir|ar|par|no|uz|pie|pēc|pirms|līdz|caur|bez|dēļ|labad)\b',  # Common Latvian prepositions
            r'\b(māja|dzīvoklis|istaba|eiro|cena|stāvs|metros)\b'  # Property-related terms
        ]
        
        for pattern in latvian_indicators:
            if re.search(pattern, text):
                return SupportedLanguage.LATVIAN
        
        # English indicators
        english_indicators = [
            r'\b(the|and|with|for|from|to|at|by|of|in|on|is|are|was|were)\b',
            r'\b(house|apartment|room|euro|price|floor|meters|property)\b'
        ]
        
        english_count = sum(1 for pattern in english_indicators if re.search(pattern, text))
        
        # If significant English content detected
        if english_count >= 2:
            return SupportedLanguage.ENGLISH
        
        # Default to Latvian for local real estate
        return SupportedLanguage.LATVIAN


class CurrencyFormatter:
    """Currency formatting utilities."""
    
    @staticmethod
    def format_price(amount: Union[float, Decimal, str, None], language: str = None) -> str:
        """
        Format price according to locale conventions.
        
        Args:
            amount: Price amount
            language: Language code
            
        Returns:
            Formatted price string
        """
        if amount is None or amount == '':
            return ''
        
        if language is None:
            language = current_language.get()
        
        try:
            # Convert to float
            if isinstance(amount, str):
                amount = float(amount.replace(',', '').replace('€', '').strip())
            elif isinstance(amount, Decimal):
                amount = float(amount)
            
            if amount <= 0:
                return ''
            
            format_config = LocaleFormat.FORMATS.get(language, LocaleFormat.FORMATS['lv'])
            
            # Format number with proper separators
            if language == 'en':
                formatted = f"{amount:,.0f}"
            else:
                # For LV and RU, use space as thousands separator
                formatted = f"{amount:,.0f}".replace(',', ' ')
            
            # Add currency symbol
            currency = format_config['currency_symbol']
            if format_config['currency_position'] == 'before':
                return f"{currency}{formatted}"
            else:
                return f"{formatted} {currency}"
                
        except (ValueError, TypeError):
            return str(amount) if amount else ''
    
    @staticmethod
    def format_price_per_sqm(amount: Union[float, Decimal, str, None], language: str = None) -> str:
        """Format price per square meter."""
        if not amount:
            return ''
        
        if language is None:
            language = current_language.get()
        
        base_price = CurrencyFormatter.format_price(amount, language)
        if not base_price:
            return ''
        
        format_config = LocaleFormat.FORMATS.get(language, LocaleFormat.FORMATS['lv'])
        area_unit = format_config['area_unit_display']
        
        return f"{base_price}/{area_unit}"


class DateTimeFormatter:
    """Date and time formatting utilities."""
    
    @staticmethod
    def format_date(date: Union[datetime, str, None], language: str = None) -> str:
        """Format date according to locale conventions."""
        if not date:
            return ''
        
        if language is None:
            language = current_language.get()
        
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except ValueError:
                return str(date)
        
        format_config = LocaleFormat.FORMATS.get(language, LocaleFormat.FORMATS['lv'])
        return date.strftime(format_config['date_format'])
    
    @staticmethod
    def format_datetime(date: Union[datetime, str, None], language: str = None) -> str:
        """Format datetime according to locale conventions."""
        if not date:
            return ''
        
        if language is None:
            language = current_language.get()
        
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except ValueError:
                return str(date)
        
        format_config = LocaleFormat.FORMATS.get(language, LocaleFormat.FORMATS['lv'])
        return date.strftime(format_config['datetime_format'])
    
    @staticmethod
    def format_relative_date(date: Union[datetime, str, None], language: str = None) -> str:
        """Format date as relative time (e.g., '2 days ago')."""
        if not date:
            return ''
        
        if language is None:
            language = current_language.get()
        
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except ValueError:
                return str(date)
        
        now = datetime.utcnow()
        diff = now - date
        
        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                if language == 'en':
                    return f"{minutes} minutes ago" if minutes != 1 else "1 minute ago"
                elif language == 'lv':
                    return f"pirms {minutes} minūtēm" if minutes != 1 else "pirms 1 minūtes"
                else:  # ru
                    return f"{minutes} минут назад" if minutes != 1 else "1 минуту назад"
            else:
                if language == 'en':
                    return f"{hours} hours ago" if hours != 1 else "1 hour ago"
                elif language == 'lv':
                    return f"pirms {hours} stundām" if hours != 1 else "pirms 1 stundas"
                else:  # ru
                    return f"{hours} часов назад" if hours != 1 else "1 час назад"
        elif diff.days == 1:
            if language == 'en':
                return "1 day ago"
            elif language == 'lv':
                return "pirms 1 dienas"
            else:  # ru
                return "1 день назад"
        else:
            if language == 'en':
                return f"{diff.days} days ago"
            elif language == 'lv':
                return f"pirms {diff.days} dienām"
            else:  # ru
                return f"{diff.days} дней назад"


class NumberFormatter:
    """Number formatting utilities."""
    
    @staticmethod
    def format_area(area: Union[float, int, str, None], language: str = None) -> str:
        """Format area with proper units."""
        if not area:
            return ''
        
        if language is None:
            language = current_language.get()
        
        try:
            area_num = float(area)
            format_config = LocaleFormat.FORMATS.get(language, LocaleFormat.FORMATS['lv'])
            
            if language == 'en':
                formatted = f"{area_num:,.1f}"
            else:
                formatted = f"{area_num:,.1f}".replace(',', ' ')
            
            return f"{formatted} {format_config['area_unit_display']}"
            
        except (ValueError, TypeError):
            return str(area) if area else ''
    
    @staticmethod
    def format_rooms(rooms: Union[int, str, None], language: str = None) -> str:
        """Format room count with proper plural forms."""
        if not rooms:
            return ''
        
        if language is None:
            language = current_language.get()
        
        try:
            room_count = int(rooms)
            format_config = LocaleFormat.FORMATS.get(language, LocaleFormat.FORMATS['lv'])
            
            if room_count == 1:
                room_word = format_config['room_singular']
            else:
                room_word = format_config['room_plural']
            
            return f"{room_count} {room_word}"
            
        except (ValueError, TypeError):
            return str(rooms) if rooms else ''
    
    @staticmethod
    def format_floor(floor: Union[int, str, None], language: str = None) -> str:
        """Format floor number with proper suffix."""
        if not floor:
            return ''
        
        if language is None:
            language = current_language.get()
        
        try:
            floor_num = int(floor)
            format_config = LocaleFormat.FORMATS.get(language, LocaleFormat.FORMATS['lv'])
            
            if language == 'en':
                # English ordinal suffixes
                if 10 <= floor_num % 100 <= 20:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(floor_num % 10, 'th')
                return f"{floor_num}{suffix} floor"
            elif language == 'lv':
                return f"{floor_num}. stāvs"
            else:  # ru
                return f"{floor_num}-й этаж"
                
        except (ValueError, TypeError):
            return str(floor) if floor else ''


@lru_cache(maxsize=128)
def get_language_name(language_code: str, in_language: str = None) -> str:
    """
    Get the display name of a language.
    
    Args:
        language_code: Language code to get name for
        in_language: Language to display the name in (default: same as language_code)
        
    Returns:
        Language display name
    """
    if in_language is None:
        in_language = language_code
    
    names = {
        'en': {'en': 'English', 'lv': 'Angļu valoda', 'ru': 'Английский'},
        'lv': {'en': 'Latvian', 'lv': 'Latviešu valoda', 'ru': 'Латышский'},
        'ru': {'en': 'Russian', 'lv': 'Krievu valoda', 'ru': 'Русский'}
    }
    
    return names.get(language_code, {}).get(in_language, language_code)


def get_current_language() -> str:
    """Get the current request language."""
    return current_language.get()


def set_current_language(language: str) -> None:
    """Set the current request language."""
    if language in [e.value for e in SupportedLanguage]:
        current_language.set(language)
    else:
        logger.warning(f"Unsupported language '{language}', falling back to Latvian")
        current_language.set(SupportedLanguage.LATVIAN)


def get_current_request_id() -> str:
    """Get the current request ID."""
    return current_request_id.get()


def set_current_request_id(request_id: str) -> None:
    """Set the current request ID."""
    current_request_id.set(request_id)


class LocalizedFormatter:
    """Main formatter class that combines all formatting utilities."""
    
    def __init__(self, language: str = None):
        self.language = language or get_current_language()
    
    def format_listing_data(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format all applicable fields in a listing according to locale conventions.
        
        Args:
            listing: Listing data dictionary
            
        Returns:
            Dictionary with formatted fields
        """
        formatted = listing.copy()
        
        # Format price fields
        if 'price' in formatted:
            formatted['price_formatted'] = CurrencyFormatter.format_price(
                formatted.get('price'), self.language
            )
        
        if 'price_per_sqm' in formatted:
            formatted['price_per_sqm_formatted'] = CurrencyFormatter.format_price_per_sqm(
                formatted.get('price_per_sqm'), self.language
            )
        
        # Format area
        if 'area_sqm' in formatted:
            formatted['area_formatted'] = NumberFormatter.format_area(
                formatted.get('area_sqm'), self.language
            )
        
        # Format rooms
        if 'rooms' in formatted:
            formatted['rooms_formatted'] = NumberFormatter.format_rooms(
                formatted.get('rooms'), self.language
            )
        
        # Format floor
        if 'floor' in formatted:
            formatted['floor_formatted'] = NumberFormatter.format_floor(
                formatted.get('floor'), self.language
            )
        
        # Format dates
        if 'posted_date' in formatted:
            formatted['posted_date_formatted'] = DateTimeFormatter.format_date(
                formatted.get('posted_date'), self.language
            )
            formatted['posted_date_relative'] = DateTimeFormatter.format_relative_date(
                formatted.get('posted_date'), self.language
            )
        
        if 'scraped_at' in formatted:
            formatted['scraped_at_formatted'] = DateTimeFormatter.format_datetime(
                formatted.get('scraped_at'), self.language
            )
        
        return formatted