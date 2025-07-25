import re
import locale
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Union, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Utility class for normalizing scraped real estate data."""
    
    # Currency conversion rates to EUR (example rates - should be updated from API)
    CURRENCY_RATES = {
        'EUR': 1.0,
        'USD': 0.85,
        'GBP': 1.15,
        'LVL': 1.42,  # Historical Latvian Lats
    }
    
    # Area unit conversions to square meters
    AREA_CONVERSIONS = {
        'm²': 1.0,
        'm2': 1.0,
        'sqm': 1.0,
        'ha': 10000.0,  # hectares
        'acres': 4046.86,
    }
    
    @staticmethod
    def normalize_price(price_text: str, currency: str = 'EUR') -> Optional[Dict[str, Union[float, str]]]:
        """
        Normalize price from various text formats to a standard format.
        
        Args:
            price_text: Raw price text from webpage
            currency: Currency code
            
        Returns:
            Dict with normalized price and currency, or None if parsing fails
        """
        if not price_text:
            return None
        
        try:
            # Remove common currency symbols and text
            cleaned = re.sub(r'[€$£¥]|EUR|USD|GBP|JPY|LVL', '', price_text)
            
            # Remove spaces, commas, and other non-numeric characters except decimal points
            cleaned = re.sub(r'[,\s]+', '', cleaned)
            
            # Handle different decimal separators
            cleaned = cleaned.replace(',', '.')
            
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                price = float(match.group(1))
                
                # Convert to EUR if needed
                if currency in DataNormalizer.CURRENCY_RATES:
                    price_eur = price * DataNormalizer.CURRENCY_RATES[currency]
                else:
                    price_eur = price
                    currency = 'EUR'  # Assume EUR if unknown currency
                
                return {
                    'price': round(price_eur, 2),
                    'currency': 'EUR',
                    'original_price': price,
                    'original_currency': currency
                }
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Error normalizing price '{price_text}': {e}")
        
        return None
    
    @staticmethod
    def normalize_area(area_text: str) -> Optional[Dict[str, Union[float, str]]]:
        """
        Normalize area from various text formats to square meters.
        
        Args:
            area_text: Raw area text from webpage
            
        Returns:
            Dict with normalized area in m², or None if parsing fails
        """
        if not area_text:
            return None
        
        try:
            # Extract numeric value and unit
            pattern = r'(\d+\.?\d*)\s*(m²|m2|sqm|ha|acres?)?'
            match = re.search(pattern, area_text.lower())
            
            if match:
                area_value = float(match.group(1))
                unit = match.group(2) or 'm²'
                
                # Convert to square meters
                if unit in DataNormalizer.AREA_CONVERSIONS:
                    area_sqm = area_value * DataNormalizer.AREA_CONVERSIONS[unit]
                else:
                    area_sqm = area_value  # Assume m² if unknown unit
                
                return {
                    'area_sqm': round(area_sqm, 2),
                    'original_area': area_value,
                    'original_unit': unit
                }
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Error normalizing area '{area_text}': {e}")
        
        return None
    
    @staticmethod
    def normalize_address(address_text: str) -> Optional[Dict[str, str]]:
        """
        Normalize address and extract components.
        
        Args:
            address_text: Raw address text
            
        Returns:
            Dict with normalized address components
        """
        if not address_text:
            return None
        
        try:
            # Clean the address
            cleaned_address = re.sub(r'\s+', ' ', address_text.strip())
            
            # Extract city (Latvian cities)
            city_patterns = {
                'Riga': r'R[īi]g[aā]|Riga',
                'Jurmala': r'J[ūu]rmal[aā]|Jurmala',
                'Liepaja': r'Liep[āa]j[aā]|Liepaja',
                'Daugavpils': r'Daugavpils',
                'Jelgava': r'Jelgava',
                'Ventspils': r'Ventspils'
            }
            
            city = None
            for city_name, pattern in city_patterns.items():
                if re.search(pattern, cleaned_address, re.IGNORECASE):
                    city = city_name
                    break
            
            # Extract postal code (Latvian format: LV-####)
            postal_match = re.search(r'LV-?(\d{4})', cleaned_address, re.IGNORECASE)
            postal_code = postal_match.group(0) if postal_match else None
            
            # Extract district/neighborhood (common patterns)
            district_patterns = [
                r'([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\s+(?:rajons?|district)',
                r'([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\s+(?:apkaime|mikrorajons)',
            ]
            
            district = None
            for pattern in district_patterns:
                match = re.search(pattern, cleaned_address)
                if match:
                    district = match.group(1)
                    break
            
            return {
                'full_address': cleaned_address,
                'city': city,
                'district': district,
                'postal_code': postal_code
            }
            
        except Exception as e:
            logger.warning(f"Error normalizing address '{address_text}': {e}")
        
        return {'full_address': address_text.strip()}
    
    @staticmethod
    def normalize_property_type(property_type_text: str) -> Optional[str]:
        """
        Normalize property type to standard categories.
        
        Args:
            property_type_text: Raw property type text
            
        Returns:
            Normalized property type string
        """
        if not property_type_text:
            return None
        
        type_text = property_type_text.lower().strip()
        
        # Mapping of various terms to standard types
        type_mappings = {
            'apartment': ['apartment', 'flat', 'dzīvoklis', 'dzivoklis'],
            'house': ['house', 'māja', 'maja', 'villa', 'townhouse'],
            'land': ['land', 'zeme', 'plot', 'lot', 'gabals'],
            'commercial': ['commercial', 'office', 'biroja', 'veikals', 'shop'],
            'garage': ['garage', 'garāža', 'garaza', 'parking']
        }
        
        for standard_type, variants in type_mappings.items():
            if any(variant in type_text for variant in variants):
                return standard_type
        
        return 'other'
    
    @staticmethod
    def normalize_features(features_list: list) -> list:
        """
        Normalize and standardize feature names.
        
        Args:
            features_list: List of raw feature strings
            
        Returns:
            List of normalized feature strings
        """
        if not features_list:
            return []
        
        # Feature mappings from various languages to English
        feature_mappings = {
            'balcony': ['balcony', 'balkons', 'balkon', 'terrace', 'terase'],
            'parking': ['parking', 'parkošana', 'stāvvieta', 'garage', 'garāža'],
            'elevator': ['elevator', 'lift', 'lifts', 'elevators'],
            'furnished': ['furnished', 'mēbelēts', 'mebelēts', 'furnished'],
            'renovated': ['renovated', 'renovēts', 'atjaunots', 'restored'],
            'new_building': ['new building', 'jauns nams', 'new', 'jauns'],
            'central_heating': ['central heating', 'centrālā apkure', 'centrala apkure'],
            'internet': ['internet', 'wifi', 'wi-fi', 'internets'],
            'security': ['security', 'apsardze', 'drošība', 'alarm'],
            'garden': ['garden', 'dārzs', 'darzs', 'yard', 'pagalms']
        }
        
        normalized_features = set()
        
        for feature in features_list:
            if not feature or not isinstance(feature, str):
                continue
                
            feature_lower = feature.lower().strip()
            
            # Find matching normalized feature
            matched = False
            for standard_feature, variants in feature_mappings.items():
                if any(variant in feature_lower for variant in variants):
                    normalized_features.add(standard_feature)
                    matched = True
                    break
            
            # If no mapping found, keep original (cleaned)
            if not matched and len(feature_lower) > 2:
                normalized_features.add(feature_lower)
        
        return sorted(list(normalized_features))
    
    @staticmethod
    def normalize_date(date_text: str) -> Optional[datetime]:
        """
        Normalize date from various formats.
        
        Args:
            date_text: Raw date text
            
        Returns:
            Normalized datetime object or None
        """
        if not date_text:
            return None
        
        # Common date formats used in Latvia
        date_formats = [
            '%d.%m.%Y',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d.%m.%Y %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%d %B %Y',
            '%B %d, %Y',
        ]
        
        # Month name mappings (Latvian to English)
        month_mappings = {
            'janvāris': 'January', 'janvaris': 'January',
            'februāris': 'February', 'februaris': 'February',
            'marts': 'March',
            'aprīlis': 'April', 'aprilis': 'April',
            'maijs': 'May',
            'jūnijs': 'June', 'junijs': 'June',
            'jūlijs': 'July', 'julijs': 'July',
            'augusts': 'August',
            'septembris': 'September',
            'oktobris': 'October',
            'novembris': 'November',
            'decembris': 'December'
        }
        
        try:
            # Replace Latvian month names with English
            normalized_text = date_text.strip()
            for latvian, english in month_mappings.items():
                normalized_text = re.sub(latvian, english, normalized_text, flags=re.IGNORECASE)
            
            # Try different date formats
            for fmt in date_formats:
                try:
                    return datetime.strptime(normalized_text, fmt)
                except ValueError:
                    continue
            
            # Handle relative dates like "šodien" (today), "vakar" (yesterday)
            relative_dates = {
                'šodien': 0, 'today': 0,
                'vakar': -1, 'yesterday': -1,
                'aizvakar': -2, 'day before yesterday': -2
            }
            
            for relative_text, days_offset in relative_dates.items():
                if relative_text in normalized_text.lower():
                    from datetime import timedelta
                    return datetime.now() + timedelta(days=days_offset)
                    
        except Exception as e:
            logger.warning(f"Error normalizing date '{date_text}': {e}")
        
        return None
    
    @staticmethod
    def calculate_price_per_sqm(price: float, area_sqm: float) -> Optional[float]:
        """
        Calculate price per square meter.
        
        Args:
            price: Property price
            area_sqm: Area in square meters
            
        Returns:
            Price per square meter or None
        """
        try:
            if price and area_sqm and area_sqm > 0:
                return round(price / area_sqm, 2)
        except (TypeError, ZeroDivisionError):
            pass
        
        return None
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """
        Validate if coordinates are within Latvia's bounds.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            True if coordinates are valid for Latvia
        """
        try:
            # Latvia's approximate coordinate bounds
            LAT_MIN, LAT_MAX = 55.0, 58.5
            LNG_MIN, LNG_MAX = 20.0, 28.5
            
            return (LAT_MIN <= latitude <= LAT_MAX and 
                    LNG_MIN <= longitude <= LNG_MAX)
                    
        except (TypeError, ValueError):
            return False


# Convenience functions for easy access
def normalize_listing_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all fields in a listing data dictionary.
    
    Args:
        raw_data: Dictionary with raw listing data
        
    Returns:
        Dictionary with normalized data
    """
    normalized = raw_data.copy()
    normalizer = DataNormalizer()
    
    # Normalize price
    if raw_data.get('price'):
        price_info = normalizer.normalize_price(
            str(raw_data['price']), 
            raw_data.get('price_currency', 'EUR')
        )
        if price_info:
            normalized.update(price_info)
    
    # Normalize area
    if raw_data.get('area_sqm'):
        area_info = normalizer.normalize_area(str(raw_data['area_sqm']))
        if area_info:
            normalized['area_sqm'] = area_info['area_sqm']
    
    # Normalize address
    if raw_data.get('address'):
        address_info = normalizer.normalize_address(raw_data['address'])
        if address_info:
            normalized.update(address_info)
    
    # Normalize property type
    if raw_data.get('property_type'):
        normalized['property_type'] = normalizer.normalize_property_type(raw_data['property_type'])
    
    # Normalize features
    if raw_data.get('features'):
        normalized['features'] = normalizer.normalize_features(raw_data['features'])
    
    # Normalize posted date
    if raw_data.get('posted_date'):
        normalized_date = normalizer.normalize_date(str(raw_data['posted_date']))
        if normalized_date:
            normalized['posted_date'] = normalized_date
    
    # Calculate price per sqm
    if normalized.get('price') and normalized.get('area_sqm'):
        price_per_sqm = normalizer.calculate_price_per_sqm(
            normalized['price'], 
            normalized['area_sqm']
        )
        if price_per_sqm:
            normalized['price_per_sqm'] = price_per_sqm
    
    # Validate coordinates
    if raw_data.get('latitude') and raw_data.get('longitude'):
        if normalizer.validate_coordinates(raw_data['latitude'], raw_data['longitude']):
            normalized['latitude'] = raw_data['latitude']
            normalized['longitude'] = raw_data['longitude']
        else:
            logger.warning(f"Invalid coordinates: {raw_data['latitude']}, {raw_data['longitude']}")
            normalized.pop('latitude', None)
            normalized.pop('longitude', None)
    
    return normalized