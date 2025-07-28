"""
Multilingual Content Normalization Pipeline for ProScrape i18n

This module provides comprehensive normalization for multilingual real estate content,
including text standardization, address parsing, currency conversion, and feature
extraction across English, Latvian, and Russian languages.
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from models.i18n_models import (
    MultilingualText, AddressComponents, PriceInformation, PropertyFeatures,
    ContentMetadata, SupportedLanguage, TranslationStatus
)
from utils.language_detection import analyze_listing_languages, SupportedLanguage
from utils.normalization import DataNormalizer

logger = logging.getLogger(__name__)


class NormalizationRule(Enum):
    """Types of normalization rules."""
    TEXT_CLEANUP = "text_cleanup"
    CURRENCY_CONVERSION = "currency_conversion"
    ADDRESS_PARSING = "address_parsing"
    FEATURE_EXTRACTION = "feature_extraction"
    DATE_NORMALIZATION = "date_normalization"


@dataclass
class NormalizationConfig:
    """Configuration for multilingual normalization."""
    
    # Text normalization settings
    remove_html: bool = True
    normalize_whitespace: bool = True
    fix_encoding: bool = True
    standardize_quotes: bool = True
    
    # Currency settings
    default_currency: str = "EUR"
    currency_conversion_rates: Dict[str, float] = None
    
    # Address normalization
    standardize_addresses: bool = True
    extract_coordinates: bool = True
    validate_postal_codes: bool = True
    
    # Feature extraction
    normalize_features: bool = True
    categorize_features: bool = True
    translate_features: bool = True
    
    # Quality settings
    min_text_length: int = 3
    max_text_length: int = 10000
    confidence_threshold: float = 0.7


class MultilingualTextNormalizer:
    """Normalizer for multilingual text content."""
    
    def __init__(self, config: NormalizationConfig):
        self.config = config
        
        # Language-specific text patterns
        self.text_patterns = {
            SupportedLanguage.LATVIAN: {
                'quotes': [('"', '"'), ('"', '"'), ('„', '"')],
                'dashes': ['–', '—', '―'],
                'spaces': ['\xa0', '\u2009', '\u200a'],
                'currency_symbols': ['€', 'EUR', 'Ls', 'LVL']
            },
            SupportedLanguage.RUSSIAN: {
                'quotes': [('"', '"'), ('«', '»'), ('„', '"')],
                'dashes': ['–', '—', '―'],
                'spaces': ['\xa0', '\u2009', '\u200a'],
                'currency_symbols': ['€', 'EUR', '₽', 'руб']
            },
            SupportedLanguage.ENGLISH: {
                'quotes': [('"', '"'), ('"', '"'), ("'", "'")],
                'dashes': ['–', '—', '―'],
                'spaces': ['\xa0', '\u2009', '\u200a'],
                'currency_symbols': ['€', 'EUR', '$', 'USD']
            }
        }
    
    def normalize_text(
        self, 
        text: str, 
        language: SupportedLanguage,
        text_type: str = "general"
    ) -> str:
        """
        Normalize text content for a specific language.
        
        Args:
            text: Raw text to normalize
            language: Target language for normalization
            text_type: Type of text (title, description, address, etc.)
            
        Returns:
            Normalized text string
        """
        if not text or not text.strip():
            return ""
        
        normalized = text.strip()
        
        # Remove HTML tags if enabled
        if self.config.remove_html:
            normalized = self._remove_html_tags(normalized)
        
        # Fix encoding issues
        if self.config.fix_encoding:
            normalized = self._fix_encoding_issues(normalized)
        
        # Normalize whitespace
        if self.config.normalize_whitespace:
            normalized = self._normalize_whitespace(normalized, language)
        
        # Standardize quotes
        if self.config.standardize_quotes:
            normalized = self._standardize_quotes(normalized, language)
        
        # Language-specific normalization
        normalized = self._apply_language_specific_rules(normalized, language, text_type)
        
        # Final cleanup
        normalized = self._final_cleanup(normalized)
        
        # Validate length
        if len(normalized) < self.config.min_text_length:
            logger.warning(f"Text too short after normalization: {len(normalized)} chars")
            return ""
        
        if len(normalized) > self.config.max_text_length:
            logger.warning(f"Text too long, truncating: {len(normalized)} chars")
            normalized = normalized[:self.config.max_text_length].rsplit(' ', 1)[0] + "..."
        
        return normalized
    
    def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags and entities."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode common HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
            '&hellip;': '...',
            '&mdash;': '—',
            '&ndash;': '–'
        }
        
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)
        
        return text
    
    def _fix_encoding_issues(self, text: str) -> str:
        """Fix common encoding issues."""
        # Fix mojibake patterns common in scraped data
        encoding_fixes = {
            'Ä€': 'ā',
            'Ä"': 'ē', 
            'Ä«': 'ī',
            'Ä·': 'ķ',
            'Ä¼': 'ļ',
            'Ä†': 'ņ',
            'Å ': 'š',
            'Å«': 'ū',
            'Å¾': 'ž',
            'Ä‡': 'č',
            'Ä£': 'ģ',
            'â€œ': '"',
            'â€': '"',
            'â€™': "'",
            'â€"': '–',
            'â€"': '—'
        }
        
        for wrong, correct in encoding_fixes.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _normalize_whitespace(self, text: str, language: SupportedLanguage) -> str:
        """Normalize whitespace characters."""
        patterns = self.text_patterns.get(language, {})
        
        # Replace various space characters with regular space
        for space_char in patterns.get('spaces', []):
            text = text.replace(space_char, ' ')
        
        # Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove trailing/leading whitespace
        text = text.strip()
        
        return text
    
    def _standardize_quotes(self, text: str, language: SupportedLanguage) -> str:
        """Standardize quote characters."""
        patterns = self.text_patterns.get(language, {})
        
        # Replace fancy quotes with standard ones
        for old_quote, new_quote in patterns.get('quotes', []):
            text = text.replace(old_quote, new_quote)
        
        return text
    
    def _apply_language_specific_rules(
        self, 
        text: str, 
        language: SupportedLanguage,
        text_type: str
    ) -> str:
        """Apply language-specific normalization rules."""
        
        if language == SupportedLanguage.LATVIAN:
            text = self._normalize_latvian_text(text, text_type)
        elif language == SupportedLanguage.RUSSIAN:
            text = self._normalize_russian_text(text, text_type)
        elif language == SupportedLanguage.ENGLISH:
            text = self._normalize_english_text(text, text_type)
        
        return text
    
    def _normalize_latvian_text(self, text: str, text_type: str) -> str:
        """Apply Latvian-specific normalization."""
        
        # Fix common Latvian character issues
        latvian_fixes = {
            'sh': 'š',
            'ch': 'č', 
            'zh': 'ž',
            'gh': 'ģ',
            'kh': 'ķ',
            'lh': 'ļ',
            'nh': 'ņ'
        }
        
        # Apply fixes only to words that look Latvian
        words = text.split()
        for i, word in enumerate(words):
            if self._looks_latvian(word):
                for wrong, correct in latvian_fixes.items():
                    word = word.replace(wrong, correct)
                words[i] = word
        
        text = ' '.join(words)
        
        # Latvian-specific capitalization rules
        if text_type == "title":
            text = self._capitalize_latvian_title(text)
        
        return text
    
    def _normalize_russian_text(self, text: str, text_type: str) -> str:
        """Apply Russian-specific normalization."""
        
        # Fix common transliteration issues
        cyrillic_fixes = {
            'jo': 'ё',
            'yo': 'ё',
            'zh': 'ж',
            'ch': 'ч',
            'sh': 'ш',
            'shh': 'щ',
            'jh': 'ъ',
            'yy': 'ы',
            'jj': 'ь',
            'eh': 'э',
            'yu': 'ю',
            'ya': 'я'
        }
        
        # Apply carefully to avoid false positives
        if self._has_cyrillic(text):
            for wrong, correct in cyrillic_fixes.items():
                # Only replace if surrounded by Cyrillic or at word boundaries
                pattern = rf'\b{re.escape(wrong)}\b'
                text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_english_text(self, text: str, text_type: str) -> str:
        """Apply English-specific normalization."""
        
        # Fix common spelling variations in real estate context
        spelling_fixes = {
            'appartment': 'apartment',
            'appartments': 'apartments',
            'seperate': 'separate',
            'occassion': 'occasion',
            'accomodation': 'accommodation',
            'realestate': 'real estate',
            'realtor': 'real estate agent'
        }
        
        for wrong, correct in spelling_fixes.items():
            text = re.sub(rf'\b{re.escape(wrong)}\b', correct, text, flags=re.IGNORECASE)
        
        # English title capitalization
        if text_type == "title":
            text = self._capitalize_english_title(text)
        
        return text
    
    def _looks_latvian(self, word: str) -> bool:
        """Check if a word looks like it could be Latvian."""
        latvian_chars = set('āčēģīķļņšūž')
        return any(char in latvian_chars for char in word.lower())
    
    def _has_cyrillic(self, text: str) -> bool:
        """Check if text contains Cyrillic characters."""
        cyrillic_pattern = re.compile(r'[а-яё]', re.IGNORECASE)
        return bool(cyrillic_pattern.search(text))
    
    def _capitalize_latvian_title(self, text: str) -> str:
        """Apply Latvian title capitalization rules."""
        # Latvian doesn't capitalize articles and prepositions in titles
        lowercase_words = {'un', 'ar', 'no', 'uz', 'par', 'pie', 'pa', 'bez', 'līdz'}
        
        words = text.split()
        capitalized = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                capitalized.append(word.capitalize())
            else:
                capitalized.append(word.lower())
        
        return ' '.join(capitalized)
    
    def _capitalize_english_title(self, text: str) -> str:
        """Apply English title capitalization rules."""
        # Don't capitalize articles, prepositions, conjunctions (unless first/last word)
        lowercase_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'under', 'over'
        }
        
        words = text.split()
        capitalized = []
        
        for i, word in enumerate(words):
            if i == 0 or i == len(words) - 1 or word.lower() not in lowercase_words:
                capitalized.append(word.capitalize())
            else:
                capitalized.append(word.lower())
        
        return ' '.join(capitalized)
    
    def _final_cleanup(self, text: str) -> str:
        """Final text cleanup."""
        # Remove multiple punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        text = re.sub(r'([.!?])\s*([A-ZĀČĒĢĪĶĻŅŠŪŽA-Я])', r'\1 \2', text)
        
        return text.strip()


class MultilingualAddressNormalizer:
    """Normalizer for multilingual address data."""
    
    def __init__(self, config: NormalizationConfig):
        self.config = config
        
        # Address component patterns by language
        self.address_patterns = {
            SupportedLanguage.LATVIAN: {
                'street_types': ['iela', 'bulvāris', 'prospekts', 'aleja', 'laukums', 'gatve'],
                'city_names': ['Rīga', 'Jūrmala', 'Liepāja', 'Daugavpils', 'Jelgava', 'Ventspils'],
                'district_markers': ['rajons', 'apkaime', 'mikrorajons', 'ciems'],
                'building_markers': ['māja', 'nams', 'ēka', 'korpuss']
            },
            SupportedLanguage.RUSSIAN: {
                'street_types': ['улица', 'бульвар', 'проспект', 'аллея', 'площадь', 'шоссе'],
                'city_names': ['Рига', 'Юрмала', 'Лиепая', 'Даугавпилс', 'Елгава', 'Вентспилс'],
                'district_markers': ['район', 'микрорайон', 'округ'],
                'building_markers': ['дом', 'здание', 'корпус', 'строение']
            },
            SupportedLanguage.ENGLISH: {
                'street_types': ['street', 'boulevard', 'avenue', 'road', 'square', 'drive'],
                'city_names': ['Riga', 'Jurmala', 'Liepaja', 'Daugavpils', 'Jelgava', 'Ventspils'],
                'district_markers': ['district', 'neighborhood', 'area', 'quarter'],
                'building_markers': ['building', 'house', 'block', 'tower']
            }
        }
    
    def normalize_address(self, address_text: str, language: SupportedLanguage) -> AddressComponents:
        """
        Normalize and parse address text into structured components.
        
        Args:
            address_text: Raw address text
            language: Language of the address
            
        Returns:
            AddressComponents object with parsed address data
        """
        if not address_text or not address_text.strip():
            return AddressComponents()
        
        # Clean the address text
        text_normalizer = MultilingualTextNormalizer(self.config)
        cleaned_address = text_normalizer.normalize_text(address_text, language, "address")
        
        # Parse address components
        components = self._parse_address_components(cleaned_address, language)
        
        # Create multilingual text objects for each component
        address_components = AddressComponents()
        
        if components.get('street'):
            address_components.street = MultilingualText()
            address_components.street.set_content(
                language,
                components['street'],
                ContentMetadata(
                    detected_language=language,
                    confidence=0.9,
                    translation_status=TranslationStatus.ORIGINAL
                )
            )
        
        if components.get('city'):
            address_components.city = MultilingualText()
            address_components.city.set_content(
                language,
                components['city'],
                ContentMetadata(
                    detected_language=language,
                    confidence=0.95,
                    translation_status=TranslationStatus.ORIGINAL
                )
            )
        
        if components.get('district'):
            address_components.district = MultilingualText()
            address_components.district.set_content(
                language,
                components['district'],
                ContentMetadata(
                    detected_language=language,
                    confidence=0.8,
                    translation_status=TranslationStatus.ORIGINAL
                )
            )
        
        # Set other components
        address_components.postal_code = components.get('postal_code')
        address_components.latitude = components.get('latitude')
        address_components.longitude = components.get('longitude')
        
        # Create formatted address
        formatted_address = self._format_address(components, language)
        if formatted_address:
            address_components.formatted_address = MultilingualText()
            address_components.formatted_address.set_content(
                language,
                formatted_address,
                ContentMetadata(
                    detected_language=language,
                    confidence=0.9,
                    translation_status=TranslationStatus.ORIGINAL
                )
            )
        
        return address_components
    
    def _parse_address_components(self, address_text: str, language: SupportedLanguage) -> Dict[str, Any]:
        """Parse address text into components."""
        components = {}
        patterns = self.address_patterns.get(language, {})
        
        # Extract postal code (Latvian format: LV-####)
        postal_match = re.search(r'LV-?(\d{4})', address_text, re.IGNORECASE)
        if postal_match:
            components['postal_code'] = f"LV-{postal_match.group(1)}"
            address_text = address_text.replace(postal_match.group(0), '').strip()
        
        # Extract city
        for city in patterns.get('city_names', []):
            if city.lower() in address_text.lower():
                components['city'] = city
                # Remove city from text for further parsing
                address_text = re.sub(rf'\b{re.escape(city)}\b', '', address_text, flags=re.IGNORECASE)
                break
        
        # Extract district
        for marker in patterns.get('district_markers', []):
            district_pattern = rf'([A-ZĀČĒĢĪĶĻŅŠŪŽА-Я][a-zāčēģīķļņšūžа-я]+)\s+{re.escape(marker)}'
            match = re.search(district_pattern, address_text, re.IGNORECASE)
            if match:
                components['district'] = match.group(1)
                address_text = address_text.replace(match.group(0), '').strip()
                break
        
        # Extract street (remaining text is likely street)
        if address_text.strip():
            # Clean up remaining text
            street = re.sub(r'\s+', ' ', address_text.strip())
            street = re.sub(r'^[,\-\s]+|[,\-\s]+$', '', street)
            
            if street:
                components['street'] = street
        
        return components
    
    def _format_address(self, components: Dict[str, Any], language: SupportedLanguage) -> str:
        """Format address components into a standardized string."""
        parts = []
        
        if components.get('street'):
            parts.append(components['street'])
        
        if components.get('district'):
            if language == SupportedLanguage.LATVIAN:
                parts.append(f"{components['district']} rajons")
            elif language == SupportedLanguage.RUSSIAN:
                parts.append(f"{components['district']} район")
            else:
                parts.append(f"{components['district']} district")
        
        if components.get('city'):
            parts.append(components['city'])
        
        if components.get('postal_code'):
            parts.append(components['postal_code'])
        
        return ', '.join(parts) if parts else None


class MultilingualFeatureNormalizer:
    """Normalizer for property features across languages."""
    
    def __init__(self, config: NormalizationConfig):
        self.config = config
        
        # Feature mappings from various languages to standardized English terms
        self.feature_mappings = {
            # Amenities
            'parking': {
                'en': ['parking', 'garage', 'car park', 'parking space', 'parking lot'],
                'lv': ['parkošana', 'stāvvieta', 'garāža', 'auto stāvvieta'],
                'ru': ['парковка', 'гараж', 'стоянка', 'автостоянка']
            },
            'balcony': {
                'en': ['balcony', 'terrace', 'patio', 'deck'],
                'lv': ['balkons', 'terase', 'veranda'],
                'ru': ['балкон', 'терраса', 'лоджия', 'веранда']
            },
            'elevator': {
                'en': ['elevator', 'lift', 'escalator'],
                'lv': ['lifts', 'elevators'],
                'ru': ['лифт', 'подъемник']
            },
            'furnished': {
                'en': ['furnished', 'fully furnished', 'semi furnished', 'equipped'],
                'lv': ['mēbelēts', 'ar mēbelēm', 'aprīkots'],
                'ru': ['мебелированный', 'с мебелью', 'обставленный']
            },
            'renovated': {
                'en': ['renovated', 'refurbished', 'updated', 'modernized', 'restored'],
                'lv': ['renovēts', 'atjaunots', 'pārbūvēts', 'modernizēts'],
                'ru': ['отремонтированный', 'обновленный', 'модернизированный']
            },
            'air_conditioning': {
                'en': ['air conditioning', 'ac', 'climate control', 'cooling'],
                'lv': ['gaisa kondicionēšana', 'kondicionieris', 'klimata kontrole'],
                'ru': ['кондиционер', 'климат-контроль', 'охлаждение']
            },
            'heating': {
                'en': ['heating', 'central heating', 'radiators', 'heat pump'],
                'lv': ['apkure', 'centrālā apkure', 'radiatori', 'siltuma sūknis'],
                'ru': ['отопление', 'центральное отопление', 'радиаторы']
            },
            'internet': {
                'en': ['internet', 'wifi', 'wi-fi', 'broadband', 'cable internet'],
                'lv': ['internets', 'wifi', 'bezvadu internets'],
                'ru': ['интернет', 'вайфай', 'широкополосный']
            },
            'security': {
                'en': ['security', 'alarm', 'security system', 'cctv', 'concierge'],
                'lv': ['apsardze', 'drošība', 'signalizācija', 'konsjeržs'],
                'ru': ['охрана', 'сигнализация', 'консьерж', 'видеонаблюдение']
            },
            'garden': {
                'en': ['garden', 'yard', 'backyard', 'landscaping', 'green space'],
                'lv': ['dārzs', 'pagalms', 'zaļā zona', 'ainava'],
                'ru': ['сад', 'двор', 'зеленая зона', 'ландшафт']
            },
            'pool': {
                'en': ['pool', 'swimming pool', 'spa', 'jacuzzi'],
                'lv': ['baseins', 'peldbaseins', 'spa', 'džakuzi'],
                'ru': ['бассейн', 'плавательный бассейн', 'джакузи']
            },
            'fireplace': {
                'en': ['fireplace', 'chimney', 'wood burning stove'],
                'lv': ['kamīns', 'dūmvads', 'malkas krāsns'],
                'ru': ['камин', 'дымоход', 'печь']
            },
            'storage': {
                'en': ['storage', 'basement', 'attic', 'closet', 'pantry'],
                'lv': ['noliktava', 'pagrabs', 'bēniņi', 'skapis'],
                'ru': ['кладовая', 'подвал', 'чердак', 'шкаф']
            }
        }
        
        # Categories for feature organization
        self.feature_categories = {
            'amenities': ['parking', 'balcony', 'elevator', 'pool', 'garden'],
            'utilities': ['heating', 'air_conditioning', 'internet'],
            'building_features': ['renovated', 'furnished', 'fireplace', 'storage'],
            'location_features': ['security']
        }
    
    def normalize_features(self, features_list: List[str], language: SupportedLanguage) -> PropertyFeatures:
        """
        Normalize and categorize property features.
        
        Args:
            features_list: List of raw feature strings
            language: Language of the features
            
        Returns:
            PropertyFeatures object with categorized and normalized features
        """
        if not features_list:
            return PropertyFeatures()
        
        # Normalize each feature text
        text_normalizer = MultilingualTextNormalizer(self.config)
        normalized_features = []
        
        for feature in features_list:
            if feature and isinstance(feature, str):
                normalized = text_normalizer.normalize_text(feature, language, "feature")
                if normalized:
                    normalized_features.append(normalized)
        
        # Map features to standardized terms
        standardized_features = self._map_features_to_standard(normalized_features, language)
        
        # Categorize features
        categorized_features = self._categorize_features(standardized_features, language)
        
        return categorized_features
    
    def _map_features_to_standard(self, features: List[str], language: SupportedLanguage) -> Dict[str, MultilingualText]:
        """Map features to standardized terms."""
        mapped_features = {}
        lang_key = language.value
        
        for feature_text in features:
            feature_lower = feature_text.lower()
            
            # Find matching standard feature
            for standard_feature, translations in self.feature_mappings.items():
                language_variants = translations.get(lang_key, [])
                
                if any(variant.lower() in feature_lower for variant in language_variants):
                    if standard_feature not in mapped_features:
                        mapped_features[standard_feature] = MultilingualText()
                    
                    # Set content for detected language
                    mapped_features[standard_feature].set_content(
                        language,
                        feature_text,
                        ContentMetadata(
                            detected_language=language,
                            confidence=0.8,
                            translation_status=TranslationStatus.ORIGINAL
                        )
                    )
                    break
            else:
                # If no mapping found, create custom feature
                custom_key = f"custom_{len(mapped_features)}"
                mapped_features[custom_key] = MultilingualText()
                mapped_features[custom_key].set_content(
                    language,
                    feature_text,
                    ContentMetadata(
                        detected_language=language,
                        confidence=0.6,
                        translation_status=TranslationStatus.ORIGINAL
                    )
                )
        
        return mapped_features
    
    def _categorize_features(self, features: Dict[str, MultilingualText], language: SupportedLanguage) -> PropertyFeatures:
        """Categorize features into structured groups."""
        property_features = PropertyFeatures()
        
        # Categorize known features
        for feature_key, feature_text in features.items():
            categorized = False
            
            for category, feature_list in self.feature_categories.items():
                if feature_key in feature_list:
                    category_list = getattr(property_features, category)
                    category_list.append(feature_text)
                    categorized = True
                    break
            
            # Add to raw features if not categorized
            if not categorized:
                primary_lang = feature_text.primary_language
                content = feature_text.get_content(primary_lang)
                if content:
                    property_features.raw_features.append(content)
        
        return property_features


class MultilingualPriceNormalizer:
    """Normalizer for price information across currencies and languages."""
    
    def __init__(self, config: NormalizationConfig):
        self.config = config
        self.base_normalizer = DataNormalizer()
        
        # Currency patterns by language
        self.currency_patterns = {
            SupportedLanguage.LATVIAN: {
                'symbols': ['€', 'EUR', 'Ls', 'LVL'],
                'terms': ['euro', 'eiro', 'lats', 'santīms'],
                'period_markers': ['mēnesī', 'nedēļā', 'dienā', 'gadā']
            },
            SupportedLanguage.RUSSIAN: {
                'symbols': ['€', 'EUR', '₽', 'руб'],
                'terms': ['евро', 'рубль', 'рублей'],
                'period_markers': ['в месяц', 'в неделю', 'в день', 'в год']
            },
            SupportedLanguage.ENGLISH: {
                'symbols': ['€', 'EUR', '$', 'USD'],
                'terms': ['euro', 'euros', 'dollar', 'dollars'],
                'period_markers': ['per month', 'monthly', 'per week', 'per day', 'annually']
            }
        }
    
    def normalize_price(self, price_text: str, language: SupportedLanguage) -> PriceInformation:
        """
        Normalize price information from text.
        
        Args:
            price_text: Raw price text
            language: Language of the price text
            
        Returns:
            PriceInformation object with normalized price data
        """
        if not price_text or not price_text.strip():
            return PriceInformation()
        
        # Use base normalizer for basic price parsing
        price_info = self.base_normalizer.normalize_price(price_text, self.config.default_currency)
        
        if not price_info:
            return PriceInformation()
        
        # Create price information object
        price_obj = PriceInformation(
            amount=Decimal(str(price_info['price'])),
            currency=price_info['currency'],
            original_amount=price_info.get('original_price'),
            original_currency=price_info.get('original_currency')
        )
        
        # Create multilingual display text
        display_text = MultilingualText()
        formatted_price = self._format_price_for_language(price_obj.amount, price_obj.currency, language)
        
        display_text.set_content(
            language,
            formatted_price,
            ContentMetadata(
                detected_language=language,
                confidence=0.9,
                translation_status=TranslationStatus.ORIGINAL
            )
        )
        
        price_obj.display_text = display_text
        
        return price_obj
    
    def _format_price_for_language(self, amount: Decimal, currency: str, language: SupportedLanguage) -> str:
        """Format price according to language conventions."""
        
        if language == SupportedLanguage.LATVIAN:
            if currency == "EUR":
                return f"{amount:,.0f} €"
            else:
                return f"{amount:,.0f} {currency}"
        
        elif language == SupportedLanguage.RUSSIAN:
            if currency == "EUR":
                return f"{amount:,.0f} евро"
            else:
                return f"{amount:,.0f} {currency}"
        
        else:  # English
            if currency == "EUR":
                return f"€{amount:,.0f}"
            elif currency == "USD":
                return f"${amount:,.0f}"
            else:
                return f"{amount:,.0f} {currency}"


class I18nNormalizationPipeline:
    """Main pipeline for multilingual content normalization."""
    
    def __init__(self, config: Optional[NormalizationConfig] = None):
        self.config = config or NormalizationConfig()
        
        # Initialize normalizers
        self.text_normalizer = MultilingualTextNormalizer(self.config)
        self.address_normalizer = MultilingualAddressNormalizer(self.config)
        self.feature_normalizer = MultilingualFeatureNormalizer(self.config)
        self.price_normalizer = MultilingualPriceNormalizer(self.config)
    
    def normalize_listing_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all multilingual content in a listing.
        
        Args:
            raw_data: Raw listing data dictionary
            
        Returns:
            Dictionary with normalized multilingual content
        """
        # Analyze languages in the raw data
        language_analysis = analyze_listing_languages(raw_data)
        primary_language = SupportedLanguage(language_analysis['primary_language'])
        
        normalized_data = raw_data.copy()
        normalized_data['language_analysis'] = language_analysis
        
        # Normalize title
        if raw_data.get('title'):
            title_ml = MultilingualText()
            normalized_title = self.text_normalizer.normalize_text(
                raw_data['title'], primary_language, "title"
            )
            
            if normalized_title:
                title_ml.set_content(
                    primary_language,
                    normalized_title,
                    ContentMetadata(
                        detected_language=primary_language,
                        confidence=language_analysis.get('overall_confidence', 0.0),
                        translation_status=TranslationStatus.ORIGINAL
                    )
                )
                normalized_data['title'] = title_ml.model_dump()
        
        # Normalize description
        if raw_data.get('description'):
            description_ml = MultilingualText()
            normalized_description = self.text_normalizer.normalize_text(
                raw_data['description'], primary_language, "description"
            )
            
            if normalized_description:
                description_ml.set_content(
                    primary_language,
                    normalized_description,
                    ContentMetadata(
                        detected_language=primary_language,
                        confidence=language_analysis.get('overall_confidence', 0.0),
                        translation_status=TranslationStatus.ORIGINAL
                    )
                )
                normalized_data['description'] = description_ml.model_dump()
        
        # Normalize address
        if raw_data.get('address'):
            address_components = self.address_normalizer.normalize_address(
                raw_data['address'], primary_language
            )
            normalized_data['address'] = address_components.model_dump()
        
        # Normalize features
        if raw_data.get('features'):
            property_features = self.feature_normalizer.normalize_features(
                raw_data['features'], primary_language
            )
            normalized_data['features'] = property_features.model_dump()
        
        # Normalize price
        if raw_data.get('price'):
            price_info = self.price_normalizer.normalize_price(
                str(raw_data['price']), primary_language
            )
            normalized_data['price'] = price_info.model_dump()
        
        # Set translation flags
        normalized_data['needs_translation'] = True
        normalized_data['needs_verification'] = False
        normalized_data['quality_score'] = language_analysis.get('overall_confidence', 0.0)
        
        return normalized_data


# Convenience functions
def normalize_multilingual_listing(raw_data: Dict[str, Any], config: Optional[NormalizationConfig] = None) -> Dict[str, Any]:
    """Convenience function for normalizing a single listing."""
    pipeline = I18nNormalizationPipeline(config)
    return pipeline.normalize_listing_data(raw_data)


def create_normalization_config(**kwargs) -> NormalizationConfig:
    """Create normalization configuration with custom settings."""
    return NormalizationConfig(**kwargs)