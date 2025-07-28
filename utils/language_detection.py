"""
Language Detection and Classification System for ProScrape i18n Pipeline

This module provides comprehensive language detection capabilities for real estate
content scraped from Latvian websites. It supports automatic detection of English,
Latvian, and Russian content with high accuracy and confidence scoring.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import Counter, defaultdict

# Optional: Use langdetect for enhanced detection if available
try:
    from langdetect import detect, detect_langs, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    LANGDETECT_AVAILABLE = True
    # Set seed for consistent results
    DetectorFactory.seed = 0
except ImportError:
    LANGDETECT_AVAILABLE = False

logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    """Supported languages for the i18n pipeline."""
    ENGLISH = "en"
    LATVIAN = "lv"  
    RUSSIAN = "ru"
    UNKNOWN = "unknown"


@dataclass
class LanguageDetectionResult:
    """Result of language detection with confidence scores."""
    primary_language: SupportedLanguage
    confidence: float
    all_probabilities: Dict[SupportedLanguage, float]
    detected_method: str
    text_length: int
    metadata: Dict[str, Any]


class LanguagePatterns:
    """Language-specific patterns and dictionaries for rule-based detection."""
    
    # Latvian-specific character patterns
    LATVIAN_CHARS = set('āčēģīķļņšūž')
    LATVIAN_WORDS = {
        'dzīvoklis', 'māja', 'istaba', 'virtuves', 'vannas', 'pagalms', 'dārzs',
        'centrs', 'rajons', 'iela', 'bulvāris', 'prospekts', 'pilsēta',
        'kvadrātmetrs', 'stāvs', 'lifts', 'balkons', 'pārdod', 'īrē',
        'euro', 'mēnesī', 'nedēļā', 'dienā', 'remonts', 'jauns', 'vecs',
        'plašs', 'mazs', 'liels', 'skaists', 'ērts', 'mājīgs'
    }
    
    # Russian-specific character patterns  
    RUSSIAN_CHARS = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')
    RUSSIAN_WORDS = {
        'квартира', 'дом', 'комната', 'кухня', 'ванная', 'двор', 'сад',
        'центр', 'район', 'улица', 'бульвар', 'проспект', 'город',
        'квадратный', 'этаж', 'лифт', 'балкон', 'продаю', 'сдаю',
        'евро', 'месяц', 'неделя', 'день', 'ремонт', 'новый', 'старый',
        'просторный', 'маленький', 'большой', 'красивый', 'удобный'
    }
    
    # English real estate vocabulary
    ENGLISH_WORDS = {
        'apartment', 'house', 'room', 'kitchen', 'bathroom', 'yard', 'garden',
        'center', 'district', 'street', 'boulevard', 'avenue', 'city',
        'square', 'floor', 'elevator', 'balcony', 'selling', 'renting',
        'euro', 'month', 'week', 'day', 'renovation', 'new', 'old',
        'spacious', 'small', 'large', 'beautiful', 'comfortable'
    }
    
    # Common function words by language
    LATVIAN_FUNCTION_WORDS = {
        'un', 'ar', 'no', 'uz', 'par', 'pēc', 'pie', 'pa', 'caur', 'bez',
        'līdz', 'kopš', 'dēļ', 'virs', 'zem', 'starp', 'aiz', 'pie',
        'kas', 'kurš', 'kā', 'kad', 'kur', 'kāpēc', 'cik', 'vai'
    }
    
    RUSSIAN_FUNCTION_WORDS = {
        'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'при', 'над',
        'под', 'за', 'перед', 'между', 'через', 'без', 'кроме',
        'что', 'который', 'как', 'когда', 'где', 'почему', 'сколько', 'или'
    }
    
    ENGLISH_FUNCTION_WORDS = {
        'and', 'in', 'on', 'with', 'by', 'for', 'from', 'to', 'at', 'over',
        'under', 'behind', 'before', 'between', 'through', 'without', 'except',
        'what', 'which', 'how', 'when', 'where', 'why', 'how much', 'or'
    }


class RuleBasedDetector:
    """Rule-based language detection using character patterns and vocabulary."""
    
    def __init__(self):
        self.patterns = LanguagePatterns()
    
    def detect_by_characters(self, text: str) -> Dict[SupportedLanguage, float]:
        """Detect language based on character frequency analysis."""
        if not text:
            return {}
        
        text_lower = text.lower()
        total_chars = len(text_lower)
        
        # Count language-specific characters
        latvian_count = sum(1 for char in text_lower if char in self.patterns.LATVIAN_CHARS)
        russian_count = sum(1 for char in text_lower if char in self.patterns.RUSSIAN_CHARS)
        
        # Calculate character-based probabilities
        scores = {}
        
        # Latvian score based on special characters
        if latvian_count > 0:
            scores[SupportedLanguage.LATVIAN] = min(latvian_count / total_chars * 10, 0.9)
        
        # Russian score based on Cyrillic characters
        if russian_count > 0:
            scores[SupportedLanguage.RUSSIAN] = min(russian_count / total_chars * 5, 0.9)
        
        # English score (default if no special characters)
        latin_count = sum(1 for char in text_lower if char.isalpha() and ord(char) < 256)
        if latin_count > total_chars * 0.8:  # Mostly Latin characters
            scores[SupportedLanguage.ENGLISH] = min(latin_count / total_chars, 0.8)
        
        return scores
    
    def detect_by_vocabulary(self, text: str) -> Dict[SupportedLanguage, float]:
        """Detect language based on vocabulary matching."""
        if not text:
            return {}
        
        # Tokenize and clean text
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return {}
        
        # Count vocabulary matches
        latvian_matches = sum(1 for word in words if word in self.patterns.LATVIAN_WORDS)
        russian_matches = sum(1 for word in words if word in self.patterns.RUSSIAN_WORDS)
        english_matches = sum(1 for word in words if word in self.patterns.ENGLISH_WORDS)
        
        # Count function word matches
        latvian_func_matches = sum(1 for word in words if word in self.patterns.LATVIAN_FUNCTION_WORDS)
        russian_func_matches = sum(1 for word in words if word in self.patterns.RUSSIAN_FUNCTION_WORDS)
        english_func_matches = sum(1 for word in words if word in self.patterns.ENGLISH_FUNCTION_WORDS)
        
        total_words = len(words)
        scores = {}
        
        # Calculate vocabulary-based scores
        if latvian_matches + latvian_func_matches > 0:
            score = (latvian_matches * 2 + latvian_func_matches) / total_words
            scores[SupportedLanguage.LATVIAN] = min(score, 0.95)
        
        if russian_matches + russian_func_matches > 0:
            score = (russian_matches * 2 + russian_func_matches) / total_words
            scores[SupportedLanguage.RUSSIAN] = min(score, 0.95)
        
        if english_matches + english_func_matches > 0:
            score = (english_matches * 2 + english_func_matches) / total_words
            scores[SupportedLanguage.ENGLISH] = min(score, 0.95)
        
        return scores
    
    def detect(self, text: str) -> Dict[SupportedLanguage, float]:
        """Combined rule-based detection using both character and vocabulary analysis."""
        char_scores = self.detect_by_characters(text)
        vocab_scores = self.detect_by_vocabulary(text)
        
        # Combine scores with weighted average
        combined_scores = defaultdict(float)
        
        for lang in SupportedLanguage:
            if lang == SupportedLanguage.UNKNOWN:
                continue
                
            char_score = char_scores.get(lang, 0.0)
            vocab_score = vocab_scores.get(lang, 0.0)
            
            # Weight vocabulary more heavily for longer texts
            text_length = len(text.split())
            vocab_weight = min(0.8, text_length / 50)  # Max weight 0.8 for 50+ words
            char_weight = 1.0 - vocab_weight
            
            combined_scores[lang] = char_score * char_weight + vocab_score * vocab_weight
        
        return dict(combined_scores)


class StatisticalDetector:
    """Statistical language detection using n-gram analysis."""
    
    # Character n-gram frequencies for each language (simplified)
    TRIGRAM_PROFILES = {
        SupportedLanguage.LATVIAN: {
            'ija', 'iet', 'tās', 'ība', 'ājs', 'šan', 'ums', 'ējs', 'īgs', 'ām',
            'par', 'nav', 'var', 'kur', 'kas', 'pie', 'tik', 'kā ', 'ar ', 'uz '
        },
        SupportedLanguage.RUSSIAN: {
            'ова', 'ени', 'ост', 'тел', 'ени', 'ств', 'тся', 'ать', 'его', 'или',
            'что', 'для', 'был', 'еще', 'как', 'все', 'при', 'так', 'уже', 'его'
        },
        SupportedLanguage.ENGLISH: {
            'the', 'and', 'ing', 'ion', 'tio', 'ent', 'ive', 'for', 'are', 'but',
            'not', 'you', 'all', 'can', 'had', 'was', 'one', 'our', 'out', 'day'
        }
    }
    
    def extract_trigrams(self, text: str) -> Counter:
        """Extract character trigrams from text."""
        text = text.lower().replace(' ', '')
        trigrams = []
        
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            if trigram.isalpha():
                trigrams.append(trigram)
        
        return Counter(trigrams)
    
    def detect(self, text: str) -> Dict[SupportedLanguage, float]:
        """Detect language using trigram analysis."""
        if len(text) < 10:  # Too short for reliable trigram analysis
            return {}
        
        trigrams = self.extract_trigrams(text)
        if not trigrams:
            return {}
        
        scores = {}
        
        for lang, profile in self.TRIGRAM_PROFILES.items():
            # Calculate overlap with language profile
            matches = sum(trigrams[trigram] for trigram in profile if trigram in trigrams)
            total_trigrams = sum(trigrams.values())
            
            if total_trigrams > 0:
                scores[lang] = min(matches / total_trigrams * 3, 0.9)  # Scale and cap
        
        return scores


class LanguageDetector:
    """Main language detection system combining multiple detection methods."""
    
    def __init__(self):
        self.rule_detector = RuleBasedDetector()
        self.statistical_detector = StatisticalDetector()
        
    def detect_language(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> LanguageDetectionResult:
        """
        Detect the primary language of the given text.
        
        Args:
            text: Text to analyze
            context: Additional context (source site, field type, etc.)
            
        Returns:
            LanguageDetectionResult with detection results
        """
        if not text or not text.strip():
            return LanguageDetectionResult(
                primary_language=SupportedLanguage.UNKNOWN,
                confidence=0.0,
                all_probabilities={},
                detected_method="empty_text",
                text_length=0,
                metadata={"error": "Empty or null text"}
            )
        
        text = text.strip()
        text_length = len(text)
        
        # Collect scores from different detection methods
        all_scores = defaultdict(list)
        detection_methods = []
        
        # Rule-based detection
        try:
            rule_scores = self.rule_detector.detect(text)
            for lang, score in rule_scores.items():
                all_scores[lang].append(score)
            detection_methods.append("rule_based")
        except Exception as e:
            logger.warning(f"Rule-based detection failed: {e}")
        
        # Statistical detection
        try:
            stat_scores = self.statistical_detector.detect(text)
            for lang, score in stat_scores.items():
                all_scores[lang].append(score)
            detection_methods.append("statistical")
        except Exception as e:
            logger.warning(f"Statistical detection failed: {e}")
        
        # External library detection (if available)
        if LANGDETECT_AVAILABLE and text_length > 20:
            try:
                detected_langs = detect_langs(text)
                for lang_prob in detected_langs:
                    lang_code = lang_prob.lang
                    prob = lang_prob.prob
                    
                    # Map to supported languages
                    if lang_code == 'en':
                        all_scores[SupportedLanguage.ENGLISH].append(prob)
                    elif lang_code == 'lv':
                        all_scores[SupportedLanguage.LATVIAN].append(prob)
                    elif lang_code == 'ru':
                        all_scores[SupportedLanguage.RUSSIAN].append(prob)
                
                detection_methods.append("langdetect")
                
            except (LangDetectException, Exception) as e:
                logger.debug(f"Langdetect failed: {e}")
        
        # Calculate combined probabilities
        final_probabilities = {}
        
        for lang, scores in all_scores.items():
            if scores:
                # Use weighted average with higher weight for consistent results
                if len(scores) > 1:
                    # Remove outliers if we have multiple scores
                    if len(scores) >= 3:
                        scores = sorted(scores)[1:-1]  # Remove min and max
                    final_probabilities[lang] = statistics.mean(scores)
                else:
                    final_probabilities[lang] = scores[0]
        
        # Apply context-based adjustments
        if context:
            final_probabilities = self._apply_contextual_adjustments(
                final_probabilities, context, text
            )
        
        # Determine primary language and confidence
        if not final_probabilities:
            primary_language = SupportedLanguage.UNKNOWN
            confidence = 0.0
        else:
            # Normalize probabilities
            total_prob = sum(final_probabilities.values())
            if total_prob > 0:
                final_probabilities = {
                    lang: prob / total_prob 
                    for lang, prob in final_probabilities.items()
                }
            
            # Get primary language
            primary_language = max(final_probabilities, key=final_probabilities.get)
            confidence = final_probabilities[primary_language]
            
            # Adjust confidence based on score distribution
            if len(final_probabilities) > 1:
                scores_list = sorted(final_probabilities.values(), reverse=True)
                if len(scores_list) >= 2:
                    # Reduce confidence if second-best score is close
                    score_gap = scores_list[0] - scores_list[1]
                    confidence = confidence * (0.5 + score_gap * 0.5)
        
        return LanguageDetectionResult(
            primary_language=primary_language,
            confidence=confidence,
            all_probabilities=final_probabilities,
            detected_method="+".join(detection_methods),
            text_length=text_length,
            metadata={
                "detection_methods": detection_methods,
                "context": context or {}
            }
        )
    
    def _apply_contextual_adjustments(
        self, 
        probabilities: Dict[SupportedLanguage, float],
        context: Dict[str, Any],
        text: str
    ) -> Dict[SupportedLanguage, float]:
        """Apply contextual adjustments to language probabilities."""
        adjusted = probabilities.copy()
        
        # Source site context
        source_site = context.get('source_site', '')
        if source_site:
            if 'ss.com' in source_site:
                # SS.com tends to have more English/Latvian mix
                if SupportedLanguage.ENGLISH in adjusted:
                    adjusted[SupportedLanguage.ENGLISH] *= 1.1
                if SupportedLanguage.LATVIAN in adjusted:
                    adjusted[SupportedLanguage.LATVIAN] *= 1.1
            
            elif any(site in source_site for site in ['city24.lv', 'pp.lv']):
                # City24 and PP.lv tend to be more Latvian/Russian
                if SupportedLanguage.LATVIAN in adjusted:
                    adjusted[SupportedLanguage.LATVIAN] *= 1.2
                if SupportedLanguage.RUSSIAN in adjusted:
                    adjusted[SupportedLanguage.RUSSIAN] *= 1.1
        
        # Field type context
        field_type = context.get('field_type', '')
        if field_type == 'address':
            # Addresses are often mixed or abbreviated
            for lang in adjusted:
                adjusted[lang] *= 0.9  # Reduce confidence for addresses
        
        elif field_type == 'features':
            # Features often contain standard terminology
            if SupportedLanguage.ENGLISH in adjusted:
                adjusted[SupportedLanguage.ENGLISH] *= 1.1
        
        # Text characteristics
        has_urls = bool(re.search(r'http[s]?://|www\.', text))
        has_numbers = bool(re.search(r'\d', text))
        
        if has_urls or (has_numbers and len(text.split()) < 5):
            # URLs and number-heavy short texts are less reliable
            for lang in adjusted:
                adjusted[lang] *= 0.8
        
        return adjusted
    
    def detect_batch(
        self, 
        texts: List[str], 
        contexts: Optional[List[Dict[str, Any]]] = None
    ) -> List[LanguageDetectionResult]:
        """
        Detect languages for a batch of texts efficiently.
        
        Args:
            texts: List of texts to analyze
            contexts: Optional list of contexts for each text
            
        Returns:
            List of LanguageDetectionResult objects
        """
        if contexts is None:
            contexts = [None] * len(texts)
        
        results = []
        for text, context in zip(texts, contexts):
            result = self.detect_language(text, context)
            results.append(result)
        
        return results


class ContentLanguageAnalyzer:
    """High-level analyzer for real estate listing content."""
    
    def __init__(self):
        self.detector = LanguageDetector()
    
    def analyze_listing_languages(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze languages in all text fields of a real estate listing.
        
        Args:
            listing_data: Dictionary containing listing information
            
        Returns:
            Dictionary with language analysis results
        """
        # Define text fields to analyze
        text_fields = {
            'title': listing_data.get('title', ''),
            'description': listing_data.get('description', ''),
            'address': listing_data.get('address', ''),
            'features': ' '.join(listing_data.get('features', [])),
            'amenities': ' '.join(listing_data.get('amenities', []))
        }
        
        # Context for each field
        source_site = listing_data.get('source_site', '')
        
        field_results = {}
        language_votes = defaultdict(float)
        total_confidence = 0.0
        
        for field_name, text in text_fields.items():
            if not text or not text.strip():
                continue
                
            context = {
                'source_site': source_site,
                'field_type': field_name
            }
            
            result = self.detector.detect_language(text, context)
            field_results[field_name] = result
            
            # Accumulate votes for overall language determination
            if result.primary_language != SupportedLanguage.UNKNOWN:
                weight = self._get_field_weight(field_name) * result.confidence
                language_votes[result.primary_language] += weight
                total_confidence += weight
        
        # Determine overall primary language
        if language_votes:
            primary_language = max(language_votes, key=language_votes.get)
            overall_confidence = language_votes[primary_language] / total_confidence
        else:
            primary_language = SupportedLanguage.UNKNOWN
            overall_confidence = 0.0
        
        return {
            'primary_language': primary_language,
            'overall_confidence': overall_confidence,
            'field_results': field_results,
            'language_distribution': dict(language_votes),
            'source_site': source_site,
            'analysis_timestamp': logger.name  # Using logger name as timestamp placeholder
        }
    
    def _get_field_weight(self, field_name: str) -> float:
        """Get relative importance weight for different fields."""
        weights = {
            'title': 0.3,
            'description': 0.4,
            'address': 0.1,
            'features': 0.1,
            'amenities': 0.1
        }
        return weights.get(field_name, 0.1)


# Convenience functions for easy integration
def detect_text_language(text: str, context: Optional[Dict[str, Any]] = None) -> LanguageDetectionResult:
    """Convenience function for detecting single text language."""
    detector = LanguageDetector()
    return detector.detect_language(text, context)


def analyze_listing_languages(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for analyzing all languages in a listing."""
    analyzer = ContentLanguageAnalyzer()
    return analyzer.analyze_listing_languages(listing_data)


def get_supported_languages() -> List[str]:
    """Get list of supported language codes."""
    return [lang.value for lang in SupportedLanguage if lang != SupportedLanguage.UNKNOWN]