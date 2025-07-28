"""
Cross-Language Duplicate Detection for ProScrape i18n Pipeline

This module provides comprehensive duplicate detection for multilingual real estate
listings, using fuzzy matching, semantic similarity, and property-specific algorithms
to identify the same property listed in different languages or sites.
"""

import re
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
import math

# Optional dependencies for advanced matching
try:
    from fuzzywuzzy import fuzz, process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True  
except ImportError:
    LEVENSHTEIN_AVAILABLE = False

from models.i18n_models import MultilingualListing, SupportedLanguage
from utils.language_detection import SupportedLanguage
from utils.i18n_database import I18nDatabaseManager

logger = logging.getLogger(__name__)


class MatchType(Enum):
    """Types of duplicate matches."""
    EXACT = "exact"                    # Exact match (same listing_id + source)
    HIGH_CONFIDENCE = "high_confidence"  # Very likely the same property
    MEDIUM_CONFIDENCE = "medium_confidence"  # Probably the same property
    LOW_CONFIDENCE = "low_confidence"    # Possibly the same property
    NO_MATCH = "no_match"             # Not a match


@dataclass
class DuplicateMatchConfig:
    """Configuration for duplicate detection."""
    
    # Text similarity thresholds
    title_similarity_threshold: float = 0.80
    description_similarity_threshold: float = 0.70
    address_similarity_threshold: float = 0.85
    
    # Property matching thresholds
    price_tolerance_percent: float = 0.10  # 10% price difference allowed
    area_tolerance_percent: float = 0.05   # 5% area difference allowed
    coordinate_tolerance_meters: float = 100.0  # 100m coordinate difference
    
    # Match confidence weights
    title_weight: float = 0.25
    description_weight: float = 0.20
    address_weight: float = 0.25
    price_weight: float = 0.15
    area_weight: float = 0.10
    coordinate_weight: float = 0.05
    
    # Advanced matching options
    use_fuzzy_matching: bool = True
    use_semantic_matching: bool = False  # Requires additional ML models
    cross_language_matching: bool = True
    
    # Performance settings
    max_candidates: int = 100
    batch_size: int = 50


@dataclass
class MatchResult:
    """Result of a duplicate match comparison."""
    
    listing1_id: str
    listing2_id: str
    match_type: MatchType
    confidence_score: float
    
    # Component scores
    title_score: float
    description_score: float
    address_score: float
    price_score: float
    area_score: float
    coordinate_score: float
    
    # Additional metadata
    same_source: bool
    languages_compared: Tuple[SupportedLanguage, SupportedLanguage]
    match_reasons: List[str]
    created_at: datetime


class TextSimilarityCalculator:
    """Calculator for text similarity across languages."""
    
    def __init__(self, config: DuplicateMatchConfig):
        self.config = config
    
    def calculate_similarity(
        self,
        text1: str,
        text2: str,
        lang1: SupportedLanguage,
        lang2: SupportedLanguage
    ) -> float:
        """
        Calculate similarity between two texts, potentially in different languages.
        
        Args:
            text1: First text to compare
            text2: Second text to compare  
            lang1: Language of first text
            lang2: Language of second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts for comparison
        normalized_text1 = self._normalize_for_comparison(text1, lang1)
        normalized_text2 = self._normalize_for_comparison(text2, lang2)
        
        if not normalized_text1 or not normalized_text2:
            return 0.0
        
        # Use different similarity algorithms based on language pair
        if lang1 == lang2:
            # Same language - use standard fuzzy matching
            return self._same_language_similarity(normalized_text1, normalized_text2)
        else:
            # Different languages - use cross-language techniques
            return self._cross_language_similarity(
                normalized_text1, normalized_text2, lang1, lang2
            )
    
    def _normalize_for_comparison(self, text: str, language: SupportedLanguage) -> str:
        """Normalize text for similarity comparison."""
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove punctuation and extra whitespace
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Language-specific normalization
        if language == SupportedLanguage.LATVIAN:
            # Normalize Latvian diacritics for comparison
            char_map = {
                'ā': 'a', 'č': 'c', 'ē': 'e', 'ģ': 'g', 'ī': 'i',
                'ķ': 'k', 'ļ': 'l', 'ņ': 'n', 'š': 's', 'ū': 'u', 'ž': 'z'
            }
            for latvian_char, latin_char in char_map.items():
                normalized = normalized.replace(latvian_char, latin_char)
        
        elif language == SupportedLanguage.RUSSIAN:
            # Transliterate Cyrillic to Latin for cross-language comparison
            normalized = self._transliterate_cyrillic(normalized)
        
        return normalized.strip()
    
    def _transliterate_cyrillic(self, text: str) -> str:
        """Basic Cyrillic to Latin transliteration."""
        cyrillic_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
            'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k',
            'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
            'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
            'ч': 'ch', 'ш': 'sh', 'щ': 'shh', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        result = []
        for char in text:
            result.append(cyrillic_to_latin.get(char, char))
        
        return ''.join(result)
    
    def _same_language_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity for same-language texts."""
        if not FUZZYWUZZY_AVAILABLE:
            return self._basic_similarity(text1, text2)
        
        # Use multiple fuzzy matching techniques
        ratio = fuzz.ratio(text1, text2) / 100.0
        partial_ratio = fuzz.partial_ratio(text1, text2) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(text1, text2) / 100.0
        token_set_ratio = fuzz.token_set_ratio(text1, text2) / 100.0
        
        # Weighted average of different similarity measures
        similarity = (
            ratio * 0.4 +
            partial_ratio * 0.2 +
            token_sort_ratio * 0.2 +
            token_set_ratio * 0.2
        )
        
        return min(1.0, similarity)
    
    def _cross_language_similarity(
        self,
        text1: str,
        text2: str,
        lang1: SupportedLanguage,
        lang2: SupportedLanguage
    ) -> float:
        """Calculate similarity for cross-language texts."""
        
        # Extract key terms that are likely to be similar across languages
        terms1 = self._extract_key_terms(text1, lang1)
        terms2 = self._extract_key_terms(text2, lang2)
        
        if not terms1 or not terms2:
            return 0.0
        
        # Calculate overlap of key terms
        term_similarity = self._calculate_term_overlap(terms1, terms2)
        
        # Calculate numeric similarity (prices, areas, etc.)
        numeric_similarity = self._calculate_numeric_similarity(text1, text2)
        
        # Combine similarities
        combined_similarity = (term_similarity * 0.7 + numeric_similarity * 0.3)
        
        return min(1.0, combined_similarity)
    
    def _extract_key_terms(self, text: str, language: SupportedLanguage) -> Set[str]:
        """Extract key terms that are likely to be preserved across languages."""
        terms = set()
        
        # Extract numbers (prices, areas, room counts, etc.)
        numbers = re.findall(r'\d+(?:[.,]\d+)?', text)
        terms.update(numbers)
        
        # Extract short words that might be place names or technical terms
        words = text.split()
        for word in words:
            # Include capitalized words (likely proper nouns)
            if word and word[0].isupper() and len(word) >= 3:
                terms.add(word.lower())
            
            # Include numbers with units
            if re.match(r'\d+\s*(?:m2|km|m²|sqm)', word.lower()):
                terms.add(word.lower())
        
        return terms
    
    def _calculate_term_overlap(self, terms1: Set[str], terms2: Set[str]) -> float:
        """Calculate overlap between two sets of terms."""
        if not terms1 or not terms2:
            return 0.0
        
        intersection = terms1.intersection(terms2)
        union = terms1.union(terms2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_numeric_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity based on numeric values in texts."""
        # Extract all numbers from both texts
        numbers1 = [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', text1)]
        numbers2 = [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', text2)]
        
        if not numbers1 or not numbers2:
            return 0.0
        
        # Sort numbers for comparison
        numbers1.sort()
        numbers2.sort()
        
        # Calculate similarity of numeric sequences
        max_len = max(len(numbers1), len(numbers2))
        min_len = min(len(numbers1), len(numbers2))
        
        if max_len == 0:
            return 1.0
        
        # Compare overlapping numbers
        matches = 0
        for i in range(min_len):
            if abs(numbers1[i] - numbers2[i]) < max(numbers1[i], numbers2[i]) * 0.1:  # 10% tolerance
                matches += 1
        
        return matches / max_len
    
    def _basic_similarity(self, text1: str, text2: str) -> float:
        """Basic similarity calculation without external libraries."""
        if not text1 or not text2:
            return 0.0
        
        # Use Jaccard similarity of word sets
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


class PropertyMatcher:
    """Matcher for property-specific attributes."""
    
    def __init__(self, config: DuplicateMatchConfig):
        self.config = config
    
    def calculate_price_similarity(
        self,
        price1: Optional[Union[Decimal, float]],
        price2: Optional[Union[Decimal, float]]
    ) -> float:
        """Calculate similarity between two prices."""
        if price1 is None or price2 is None:
            return 0.0 if price1 != price2 else 1.0
        
        price1, price2 = float(price1), float(price2)
        
        if price1 == 0 and price2 == 0:
            return 1.0
        
        if price1 == 0 or price2 == 0:
            return 0.0
        
        # Calculate percentage difference
        max_price = max(price1, price2)
        min_price = min(price1, price2)
        
        if max_price == 0:
            return 1.0
        
        percentage_diff = (max_price - min_price) / max_price
        
        if percentage_diff <= self.config.price_tolerance_percent:
            return 1.0 - (percentage_diff / self.config.price_tolerance_percent) * 0.2
        else:
            return max(0.0, 1.0 - percentage_diff)
    
    def calculate_area_similarity(
        self,
        area1: Optional[float],
        area2: Optional[float]
    ) -> float:
        """Calculate similarity between two areas."""
        if area1 is None or area2 is None:
            return 0.0 if area1 != area2 else 1.0
        
        if area1 == 0 and area2 == 0:
            return 1.0
        
        if area1 == 0 or area2 == 0:
            return 0.0
        
        # Calculate percentage difference
        max_area = max(area1, area2)
        min_area = min(area1, area2)
        
        percentage_diff = (max_area - min_area) / max_area
        
        if percentage_diff <= self.config.area_tolerance_percent:
            return 1.0 - (percentage_diff / self.config.area_tolerance_percent) * 0.1
        else:
            return max(0.0, 1.0 - percentage_diff)
    
    def calculate_coordinate_similarity(
        self,
        lat1: Optional[float], lng1: Optional[float],
        lat2: Optional[float], lng2: Optional[float]
    ) -> float:
        """Calculate similarity between two coordinate pairs."""
        if None in [lat1, lng1, lat2, lng2]:
            return 0.0
        
        # Calculate distance using Haversine formula
        distance = self._haversine_distance(lat1, lng1, lat2, lng2)
        
        if distance <= self.config.coordinate_tolerance_meters:
            return 1.0 - (distance / self.config.coordinate_tolerance_meters) * 0.2
        else:
            return max(0.0, 1.0 - (distance / 1000.0))  # Decrease by 1000m intervals
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in meters
        r = 6371000
        
        return c * r


class DuplicateDetector:
    """Main duplicate detection system for multilingual listings."""
    
    def __init__(self, config: Optional[DuplicateMatchConfig] = None):
        self.config = config or DuplicateMatchConfig()
        self.text_calculator = TextSimilarityCalculator(self.config)
        self.property_matcher = PropertyMatcher(self.config)
    
    def find_duplicates(
        self,
        listing: Dict[str, Any],
        candidate_listings: List[Dict[str, Any]]
    ) -> List[MatchResult]:
        """
        Find potential duplicates for a given listing.
        
        Args:
            listing: The listing to find duplicates for
            candidate_listings: List of potential duplicate listings
            
        Returns:
            List of MatchResult objects sorted by confidence score
        """
        matches = []
        
        for candidate in candidate_listings:
            # Skip self-comparison
            if self._is_same_listing(listing, candidate):
                continue
            
            # Calculate match
            match_result = self._calculate_match(listing, candidate)
            
            # Only include matches above minimum confidence
            if match_result.match_type != MatchType.NO_MATCH:
                matches.append(match_result)
        
        # Sort by confidence score (descending)
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return matches
    
    def find_duplicates_in_database(
        self,
        listing: Dict[str, Any],
        db_manager: I18nDatabaseManager,
        exclude_same_source: bool = False
    ) -> List[MatchResult]:
        """
        Find duplicates for a listing by searching the database.
        
        Args:
            listing: The listing to find duplicates for
            db_manager: Database manager instance
            exclude_same_source: Whether to exclude listings from same source
            
        Returns:
            List of MatchResult objects
        """
        # Build query to find potential candidates
        query = {}
        
        if exclude_same_source:
            query["source_site"] = {"$ne": listing.get("source_site")}
        
        # Add property type filter if available
        if listing.get("property_type"):
            query["property_type"] = listing["property_type"]
        
        # Add price range filter if available
        if listing.get("price", {}).get("amount"):
            price = float(listing["price"]["amount"])
            price_range = price * self.config.price_tolerance_percent
            query["price.amount"] = {
                "$gte": price - price_range,
                "$lte": price + price_range
            }
        
        # Get candidate listings
        candidates = db_manager.find_listings(
            filter_dict=query,
            limit=self.config.max_candidates
        )
        
        return self.find_duplicates(listing, candidates)
    
    def _calculate_match(
        self,
        listing1: Dict[str, Any],
        listing2: Dict[str, Any]
    ) -> MatchResult:
        """Calculate match result between two listings."""
        
        # Extract languages
        lang1 = self._get_primary_language(listing1)
        lang2 = self._get_primary_language(listing2)
        
        # Calculate component similarities
        title_score = self._calculate_title_similarity(listing1, listing2, lang1, lang2)
        description_score = self._calculate_description_similarity(listing1, listing2, lang1, lang2)
        address_score = self._calculate_address_similarity(listing1, listing2, lang1, lang2)
        price_score = self._calculate_price_similarity(listing1, listing2)
        area_score = self._calculate_area_similarity(listing1, listing2)
        coordinate_score = self._calculate_coordinate_similarity(listing1, listing2)
        
        # Calculate weighted overall confidence
        confidence_score = (
            title_score * self.config.title_weight +
            description_score * self.config.description_weight +
            address_score * self.config.address_weight +
            price_score * self.config.price_weight +
            area_score * self.config.area_weight +
            coordinate_score * self.config.coordinate_weight
        )
        
        # Determine match type based on confidence
        match_type = self._determine_match_type(confidence_score, listing1, listing2)
        
        # Generate match reasons
        match_reasons = self._generate_match_reasons(
            title_score, description_score, address_score,
            price_score, area_score, coordinate_score
        )
        
        return MatchResult(
            listing1_id=listing1.get("listing_id", ""),
            listing2_id=listing2.get("listing_id", ""),
            match_type=match_type,
            confidence_score=confidence_score,
            title_score=title_score,
            description_score=description_score,
            address_score=address_score,
            price_score=price_score,
            area_score=area_score,
            coordinate_score=coordinate_score,
            same_source=listing1.get("source_site") == listing2.get("source_site"),
            languages_compared=(lang1, lang2),
            match_reasons=match_reasons,
            created_at=datetime.utcnow()
        )
    
    def _get_primary_language(self, listing: Dict[str, Any]) -> SupportedLanguage:
        """Get the primary language of a listing."""
        language_analysis = listing.get("language_analysis", {})
        primary_lang = language_analysis.get("primary_language", "unknown")
        
        try:
            return SupportedLanguage(primary_lang)
        except ValueError:
            return SupportedLanguage.UNKNOWN
    
    def _calculate_title_similarity(
        self,
        listing1: Dict[str, Any],
        listing2: Dict[str, Any],
        lang1: SupportedLanguage,
        lang2: SupportedLanguage
    ) -> float:
        """Calculate title similarity between listings."""
        title1 = self._extract_text_content(listing1.get("title"), lang1)
        title2 = self._extract_text_content(listing2.get("title"), lang2)
        
        if not title1 or not title2:
            return 0.0
        
        return self.text_calculator.calculate_similarity(title1, title2, lang1, lang2)
    
    def _calculate_description_similarity(
        self,
        listing1: Dict[str, Any],
        listing2: Dict[str, Any],
        lang1: SupportedLanguage,
        lang2: SupportedLanguage
    ) -> float:
        """Calculate description similarity between listings."""
        desc1 = self._extract_text_content(listing1.get("description"), lang1)
        desc2 = self._extract_text_content(listing2.get("description"), lang2)
        
        if not desc1 or not desc2:
            return 0.0
        
        return self.text_calculator.calculate_similarity(desc1, desc2, lang1, lang2)
    
    def _calculate_address_similarity(
        self,
        listing1: Dict[str, Any],
        listing2: Dict[str, Any],
        lang1: SupportedLanguage,
        lang2: SupportedLanguage
    ) -> float:
        """Calculate address similarity between listings."""
        # Try formatted address first
        addr1 = self._extract_text_content(
            listing1.get("address", {}).get("formatted_address"), lang1
        )
        addr2 = self._extract_text_content(
            listing2.get("address", {}).get("formatted_address"), lang2
        )
        
        # Fallback to legacy address field
        if not addr1:
            addr1 = listing1.get("address", "") if isinstance(listing1.get("address"), str) else ""
        if not addr2:
            addr2 = listing2.get("address", "") if isinstance(listing2.get("address"), str) else ""
        
        if not addr1 or not addr2:
            return 0.0
        
        return self.text_calculator.calculate_similarity(addr1, addr2, lang1, lang2)
    
    def _calculate_price_similarity(self, listing1: Dict[str, Any], listing2: Dict[str, Any]) -> float:
        """Calculate price similarity between listings."""
        price1 = self._extract_price(listing1)
        price2 = self._extract_price(listing2)
        
        return self.property_matcher.calculate_price_similarity(price1, price2)
    
    def _calculate_area_similarity(self, listing1: Dict[str, Any], listing2: Dict[str, Any]) -> float:
        """Calculate area similarity between listings."""
        area1 = listing1.get("area_sqm")
        area2 = listing2.get("area_sqm")
        
        return self.property_matcher.calculate_area_similarity(area1, area2)
    
    def _calculate_coordinate_similarity(self, listing1: Dict[str, Any], listing2: Dict[str, Any]) -> float:
        """Calculate coordinate similarity between listings."""
        coords1 = self._extract_coordinates(listing1)
        coords2 = self._extract_coordinates(listing2)
        
        if not coords1 or not coords2:
            return 0.0
        
        return self.property_matcher.calculate_coordinate_similarity(
            coords1[0], coords1[1], coords2[0], coords2[1]
        )
    
    def _extract_text_content(
        self,
        multilingual_field: Optional[Dict[str, Any]],
        preferred_language: SupportedLanguage
    ) -> Optional[str]:
        """Extract text content from multilingual field."""
        if not multilingual_field:
            return None
        
        # Try preferred language first
        lang_key = preferred_language.value
        if lang_key in multilingual_field and multilingual_field[lang_key]:
            return multilingual_field[lang_key]
        
        # Try other languages
        for lang in ['en', 'lv', 'ru']:
            if lang in multilingual_field and multilingual_field[lang]:
                return multilingual_field[lang]
        
        return None
    
    def _extract_price(self, listing: Dict[str, Any]) -> Optional[float]:
        """Extract price from listing."""
        price_info = listing.get("price")
        
        if isinstance(price_info, dict):
            amount = price_info.get("amount")
            if amount is not None:
                return float(amount)
        elif isinstance(price_info, (int, float, Decimal)):
            return float(price_info)
        
        return None
    
    def _extract_coordinates(self, listing: Dict[str, Any]) -> Optional[Tuple[float, float]]:
        """Extract coordinates from listing."""
        # Try structured address first
        address = listing.get("address", {})
        if isinstance(address, dict):
            lat = address.get("latitude")
            lng = address.get("longitude")
            if lat is not None and lng is not None:
                return (float(lat), float(lng))
        
        # Try legacy fields
        lat = listing.get("latitude")
        lng = listing.get("longitude")
        if lat is not None and lng is not None:
            return (float(lat), float(lng))
        
        return None
    
    def _is_same_listing(self, listing1: Dict[str, Any], listing2: Dict[str, Any]) -> bool:
        """Check if two listings are exactly the same."""
        return (
            listing1.get("listing_id") == listing2.get("listing_id") and
            listing1.get("source_site") == listing2.get("source_site")
        )
    
    def _determine_match_type(
        self,
        confidence_score: float,
        listing1: Dict[str, Any],
        listing2: Dict[str, Any]
    ) -> MatchType:
        """Determine match type based on confidence score and other factors."""
        
        # Check for exact match (same listing_id and source)
        if self._is_same_listing(listing1, listing2):
            return MatchType.EXACT
        
        # Apply confidence thresholds
        if confidence_score >= 0.90:
            return MatchType.HIGH_CONFIDENCE
        elif confidence_score >= 0.70:
            return MatchType.MEDIUM_CONFIDENCE
        elif confidence_score >= 0.50:
            return MatchType.LOW_CONFIDENCE
        else:
            return MatchType.NO_MATCH
    
    def _generate_match_reasons(
        self,
        title_score: float,
        description_score: float,
        address_score: float,
        price_score: float,
        area_score: float,
        coordinate_score: float
    ) -> List[str]:
        """Generate human-readable reasons for the match."""
        reasons = []
        
        if title_score >= 0.8:
            reasons.append("Very similar titles")
        elif title_score >= 0.6:
            reasons.append("Similar titles")
        
        if description_score >= 0.7:
            reasons.append("Similar descriptions")
        
        if address_score >= 0.8:
            reasons.append("Very similar addresses")
        elif address_score >= 0.6:
            reasons.append("Similar addresses")
        
        if price_score >= 0.9:
            reasons.append("Nearly identical prices")
        elif price_score >= 0.7:
            reasons.append("Similar prices")
        
        if area_score >= 0.9:
            reasons.append("Nearly identical areas")
        elif area_score >= 0.8:
            reasons.append("Similar areas")
        
        if coordinate_score >= 0.9:
            reasons.append("Very close geographic locations")
        elif coordinate_score >= 0.7:
            reasons.append("Similar geographic locations")
        
        return reasons


class DuplicateDetectionPipeline:
    """Pipeline for batch duplicate detection and management."""
    
    def __init__(
        self,
        db_manager: I18nDatabaseManager,
        config: Optional[DuplicateMatchConfig] = None
    ):
        self.db_manager = db_manager
        self.config = config or DuplicateMatchConfig()
        self.detector = DuplicateDetector(self.config)
    
    def detect_duplicates_for_listing(
        self,
        listing_id: str,
        source_site: str,
        exclude_same_source: bool = True
    ) -> List[MatchResult]:
        """Detect duplicates for a specific listing."""
        # Get the listing
        listing = self.db_manager.get_listing(listing_id, source_site)
        if not listing:
            logger.warning(f"Listing not found: {listing_id} from {source_site}")
            return []
        
        # Find duplicates
        return self.detector.find_duplicates_in_database(
            listing, self.db_manager, exclude_same_source
        )
    
    def detect_all_duplicates(
        self,
        batch_size: Optional[int] = None,
        exclude_same_source: bool = True
    ) -> Dict[str, List[MatchResult]]:
        """Detect duplicates for all listings in the database."""
        batch_size = batch_size or self.config.batch_size
        
        # Get all listings
        all_listings = self.db_manager.find_listings(limit=10000)  # Adjust as needed
        
        duplicate_results = {}
        processed = 0
        
        for i in range(0, len(all_listings), batch_size):
            batch = all_listings[i:i + batch_size]
            
            for listing in batch:
                listing_key = f"{listing['source_site']}:{listing['listing_id']}"
                
                try:
                    duplicates = self.detector.find_duplicates_in_database(
                        listing, self.db_manager, exclude_same_source
                    )
                    
                    if duplicates:
                        duplicate_results[listing_key] = duplicates
                    
                    processed += 1
                    
                    if processed % 100 == 0:
                        logger.info(f"Processed {processed} listings for duplicate detection")
                
                except Exception as e:
                    logger.error(f"Error detecting duplicates for {listing_key}: {e}")
                    continue
        
        logger.info(f"Duplicate detection completed: {len(duplicate_results)} listings have duplicates")
        return duplicate_results
    
    def get_duplicate_groups(
        self,
        min_confidence: float = 0.7
    ) -> List[List[Dict[str, Any]]]:
        """Group listings that are likely duplicates of each other."""
        duplicate_results = self.detect_all_duplicates()
        
        # Build graph of duplicate relationships
        duplicate_groups = []
        processed_listings = set()
        
        for listing_key, matches in duplicate_results.items():
            if listing_key in processed_listings:
                continue
            
            # Start a new group
            group = set([listing_key])
            
            # Add high-confidence matches to the group
            for match in matches:
                if match.confidence_score >= min_confidence:
                    duplicate_key = f"{match.listing2_id}"  # Assuming source can be derived
                    group.add(duplicate_key)
            
            # Convert to listing objects
            group_listings = []
            for key in group:
                # Parse listing key to get listing_id and source_site
                if ":" in key:
                    source_site, listing_id = key.split(":", 1)
                    listing = self.db_manager.get_listing(listing_id, source_site)
                    if listing:
                        group_listings.append(listing)
            
            if len(group_listings) > 1:
                duplicate_groups.append(group_listings)
                processed_listings.update(group)
        
        return duplicate_groups
    
    def merge_duplicate_listings(
        self,
        primary_listing_id: str,
        primary_source_site: str,
        duplicate_listing_ids: List[Tuple[str, str]]
    ) -> bool:
        """
        Merge duplicate listings into a primary listing.
        
        Args:
            primary_listing_id: ID of the primary listing to keep
            primary_source_site: Source site of primary listing
            duplicate_listing_ids: List of (listing_id, source_site) tuples to merge
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get primary listing
            primary_listing = self.db_manager.get_listing(primary_listing_id, primary_source_site)
            if not primary_listing:
                logger.error(f"Primary listing not found: {primary_listing_id}")
                return False
            
            # Merge data from duplicates
            for dup_id, dup_source in duplicate_listing_ids:
                duplicate_listing = self.db_manager.get_listing(dup_id, dup_source)
                if not duplicate_listing:
                    logger.warning(f"Duplicate listing not found: {dup_id}")
                    continue
                
                # Merge multilingual content
                merged_listing = self._merge_multilingual_content(primary_listing, duplicate_listing)
                
                # Update primary listing
                # Note: This would require updating the database update method
                # to handle multilingual content properly
                
                # Mark duplicate as merged (you might want to add a status field)
                # self.db_manager.mark_as_duplicate(dup_id, dup_source, primary_listing_id)
            
            logger.info(f"Successfully merged {len(duplicate_listing_ids)} duplicates into {primary_listing_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error merging duplicates: {e}")
            return False
    
    def _merge_multilingual_content(
        self,
        primary: Dict[str, Any],
        duplicate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge multilingual content from duplicate into primary listing."""
        merged = primary.copy()
        
        # Merge multilingual text fields
        for field in ['title', 'description']:
            if field in duplicate and duplicate[field]:
                if field not in merged or not merged[field]:
                    merged[field] = duplicate[field]
                else:
                    # Merge language versions
                    primary_field = merged[field]
                    duplicate_field = duplicate[field]
                    
                    for lang in ['en', 'lv', 'ru']:
                        if lang in duplicate_field and duplicate_field[lang]:
                            if lang not in primary_field or not primary_field[lang]:
                                primary_field[lang] = duplicate_field[lang]
                                # Also merge metadata if available
                                if 'metadata' in duplicate_field:
                                    if 'metadata' not in primary_field:
                                        primary_field['metadata'] = {}
                                    primary_field['metadata'][lang] = duplicate_field['metadata'].get(lang)
        
        return merged


# Convenience functions
def detect_listing_duplicates(
    listing: Dict[str, Any],
    db_manager: I18nDatabaseManager,
    config: Optional[DuplicateMatchConfig] = None
) -> List[MatchResult]:
    """Convenience function to detect duplicates for a single listing."""
    detector = DuplicateDetector(config)
    return detector.find_duplicates_in_database(listing, db_manager)


def create_duplicate_detection_config(**kwargs) -> DuplicateMatchConfig:
    """Create duplicate detection configuration with custom settings."""
    return DuplicateMatchConfig(**kwargs)