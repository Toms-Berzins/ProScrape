"""
Enhanced listing models with internationalization support.

Extends the base listing model to support multilingual content storage
and retrieval with fallback mechanisms.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

from models.listing import ListingBase, ListingResponse, PyObjectId


class MultilingualText(BaseModel):
    """Model for storing text in multiple languages."""
    
    en: Optional[str] = Field(None, description="English text")
    lv: Optional[str] = Field(None, description="Latvian text")
    ru: Optional[str] = Field(None, description="Russian text")
    
    def get_text(self, language: str = 'en') -> Optional[str]:
        """Get text in specified language with fallback."""
        # Try requested language
        if hasattr(self, language) and getattr(self, language):
            return getattr(self, language)
        
        # Fallback order: en -> lv -> ru -> any available
        fallback_order = ['en', 'lv', 'ru']
        for lang in fallback_order:
            if hasattr(self, lang) and getattr(self, lang):
                return getattr(self, lang)
        
        return None
    
    def set_text(self, language: str, text: str):
        """Set text for specific language."""
        if language in ['en', 'lv', 'ru']:
            setattr(self, language, text)
    
    def get_available_languages(self) -> List[str]:
        """Get list of languages with available text."""
        languages = []
        for lang in ['en', 'lv', 'ru']:
            if hasattr(self, lang) and getattr(self, lang):
                languages.append(lang)
        return languages
    
    class Config:
        populate_by_name = True


class MultilingualFeatures(BaseModel):
    """Model for storing feature lists in multiple languages."""
    
    en: List[str] = Field(default_factory=list, description="English features")
    lv: List[str] = Field(default_factory=list, description="Latvian features")
    ru: List[str] = Field(default_factory=list, description="Russian features")
    
    def get_features(self, language: str = 'en') -> List[str]:
        """Get features in specified language with fallback."""
        # Try requested language
        if hasattr(self, language):
            features = getattr(self, language, [])
            if features:
                return features
        
        # Fallback order: en -> lv -> ru -> any available
        fallback_order = ['en', 'lv', 'ru']
        for lang in fallback_order:
            if hasattr(self, lang):
                features = getattr(self, lang, [])
                if features:
                    return features
        
        return []
    
    def add_feature(self, language: str, feature: str):
        """Add feature for specific language."""
        if language in ['en', 'lv', 'ru']:
            features = getattr(self, language, [])
            if feature not in features:
                features.append(feature)
                setattr(self, language, features)
    
    class Config:
        populate_by_name = True


class GeoLocation(BaseModel):
    """Enhanced location model with multilingual support."""
    
    # Original fields (for backward compatibility)
    address: Optional[str] = Field(None, description="Original address")
    city: Optional[str] = Field(None, description="Original city name")
    district: Optional[str] = Field(None, description="Original district name")
    
    # Multilingual fields
    address_i18n: Optional[MultilingualText] = Field(None, description="Multilingual address")
    city_i18n: Optional[MultilingualText] = Field(None, description="Multilingual city name")
    district_i18n: Optional[MultilingualText] = Field(None, description="Multilingual district name")
    
    # Geographic data
    postal_code: Optional[str] = Field(None, description="Postal code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    
    # Administrative divisions
    municipality: Optional[str] = Field(None, description="Municipality")
    region: Optional[str] = Field(None, description="Region/State")
    country: str = Field("LV", description="Country code")
    
    def get_address(self, language: str = 'en') -> Optional[str]:
        """Get address in specified language."""
        if self.address_i18n:
            return self.address_i18n.get_text(language)
        return self.address
    
    def get_city(self, language: str = 'en') -> Optional[str]:
        """Get city name in specified language."""
        if self.city_i18n:
            return self.city_i18n.get_text(language)
        return self.city
    
    def get_district(self, language: str = 'en') -> Optional[str]:
        """Get district name in specified language."""
        if self.district_i18n:
            return self.district_i18n.get_text(language)
        return self.district
    
    class Config:
        populate_by_name = True


class I18nListingBase(BaseModel):
    """Enhanced listing model with full internationalization support."""
    
    # Identifiers
    listing_id: str = Field(..., description="Unique identifier from source site")
    source_site: str = Field(..., description="Source website")
    
    # Multilingual content
    title_i18n: Optional[MultilingualText] = Field(None, description="Multilingual title")
    description_i18n: Optional[MultilingualText] = Field(None, description="Multilingual description")
    
    # Original fields (for backward compatibility)
    title: str = Field(..., description="Original title")
    description: Optional[str] = Field(None, description="Original description")
    
    # Price information (language-neutral)
    price: Optional[Decimal] = Field(None, description="Price in EUR")
    price_currency: str = Field("EUR", description="Price currency")
    price_per_sqm: Optional[Decimal] = Field(None, description="Price per square meter")
    
    # Property details (mostly language-neutral)
    property_type: Optional[str] = Field(None, description="Type of property")
    listing_type: Optional[str] = Field(None, description="Listing type (sell, rent)")
    area_sqm: Optional[float] = Field(None, description="Area in square meters")
    rooms: Optional[int] = Field(None, description="Number of rooms")
    floor: Optional[int] = Field(None, description="Floor number")
    total_floors: Optional[int] = Field(None, description="Total floors in building")
    
    # Enhanced location with i18n
    location: Optional[GeoLocation] = Field(None, description="Enhanced location data")
    
    # Legacy location fields (for compatibility)
    address: Optional[str] = Field(None, description="Legacy address field")
    city: Optional[str] = Field(None, description="Legacy city field")
    district: Optional[str] = Field(None, description="Legacy district field")
    postal_code: Optional[str] = Field(None, description="Legacy postal code field")
    latitude: Optional[float] = Field(None, description="Legacy latitude field")
    longitude: Optional[float] = Field(None, description="Legacy longitude field")
    
    # Multilingual features and amenities
    features_i18n: Optional[MultilingualFeatures] = Field(None, description="Multilingual features")
    amenities_i18n: Optional[MultilingualFeatures] = Field(None, description="Multilingual amenities")
    
    # Legacy feature fields (for compatibility)
    features: List[str] = Field(default_factory=list, description="Legacy features")
    amenities: List[str] = Field(default_factory=list, description="Legacy amenities")
    
    # Media (language-neutral)
    image_urls: List[str] = Field(default_factory=list, description="Property image URLs")
    video_urls: List[str] = Field(default_factory=list, description="Property video URLs")
    
    # Metadata
    posted_date: Optional[datetime] = Field(None, description="Date when listing was posted")
    updated_date: Optional[datetime] = Field(None, description="Last update date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")
    source_url: str = Field(..., description="Original listing URL")
    
    # Language detection metadata
    detected_language: Optional[str] = Field(None, description="Auto-detected content language")
    available_languages: List[str] = Field(default_factory=list, description="Available content languages")
    
    # Additional data
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw data from source")
    
    def get_title(self, language: str = 'en') -> str:
        """Get title in specified language with fallback."""
        if self.title_i18n:
            localized = self.title_i18n.get_text(language)
            if localized:
                return localized
        return self.title
    
    def get_description(self, language: str = 'en') -> Optional[str]:
        """Get description in specified language with fallback."""
        if self.description_i18n:
            localized = self.description_i18n.get_text(language)
            if localized:
                return localized
        return self.description
    
    def get_features(self, language: str = 'en') -> List[str]:
        """Get features in specified language with fallback."""
        if self.features_i18n:
            localized = self.features_i18n.get_features(language)
            if localized:
                return localized
        return self.features
    
    def get_amenities(self, language: str = 'en') -> List[str]:
        """Get amenities in specified language with fallback."""
        if self.amenities_i18n:
            localized = self.amenities_i18n.get_features(language)
            if localized:
                return localized
        return self.amenities
    
    def get_location_data(self, language: str = 'en') -> Dict[str, Optional[str]]:
        """Get location data in specified language."""
        if self.location:
            return {
                'address': self.location.get_address(language),
                'city': self.location.get_city(language),
                'district': self.location.get_district(language),
                'postal_code': self.location.postal_code,
                'municipality': self.location.municipality,
                'region': self.location.region,
                'country': self.location.country
            }
        else:
            # Fallback to legacy fields
            return {
                'address': self.address,
                'city': self.city,
                'district': self.district,
                'postal_code': self.postal_code,
                'municipality': None,
                'region': None,
                'country': 'LV'
            }
    
    @field_validator('price', 'price_per_sqm', mode='before')
    @classmethod
    def parse_price(cls, v):
        """Parse price values to Decimal for precision."""
        if v is None:
            return v
        if isinstance(v, str):
            v = v.replace('€', '').replace('EUR', '').replace(',', '').replace(' ', '')
            try:
                return Decimal(v)
            except:
                return None
        return Decimal(str(v))
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class I18nListing(I18nListingBase):
    """Full i18n listing model with MongoDB ObjectId."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class I18nListingResponse(BaseModel):
    """Localized API response model for listings."""
    
    # Basic fields
    id: str
    listing_id: str
    source_site: str
    
    # Localized content (already in requested language)
    title: str
    description: Optional[str] = None
    
    # Price information with formatting
    price: Optional[Decimal] = None
    price_formatted: Optional[str] = None
    price_currency: str = "EUR"
    price_per_sqm: Optional[Decimal] = None
    
    # Property details with localization
    property_type: Optional[str] = None
    property_type_localized: Optional[str] = None
    listing_type: Optional[str] = None
    listing_type_localized: Optional[str] = None
    
    # Measurements with formatting
    area_sqm: Optional[float] = None
    area_formatted: Optional[str] = None
    rooms: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    
    # Localized location
    address: Optional[str] = None
    city: Optional[str] = None
    city_localized: Optional[str] = None
    district: Optional[str] = None
    district_localized: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Localized features
    features: List[str] = Field(default_factory=list)
    features_localized: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    amenities_localized: List[str] = Field(default_factory=list)
    
    # Media
    image_urls: List[str] = Field(default_factory=list)
    video_urls: List[str] = Field(default_factory=list)
    
    # Formatted dates
    posted_date: Optional[datetime] = None
    posted_date_formatted: Optional[str] = None
    updated_date: Optional[datetime] = None
    updated_date_formatted: Optional[str] = None
    scraped_at: datetime
    scraped_at_formatted: Optional[str] = None
    
    # Source information
    source_url: str
    
    # Language metadata
    language: str = Field(..., description="Language of localized content")
    available_languages: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class I18nPaginatedListingResponse(BaseModel):
    """Paginated response for i18n listings API."""
    
    items: List[I18nListingResponse]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_prev: bool = Field(..., description="Has previous page")
    language: str = Field(..., description="Response language")
    
    class Config:
        populate_by_name = True


# Migration helpers for existing data
class ListingMigration:
    """Helper class for migrating existing listings to i18n format."""
    
    @staticmethod
    def migrate_listing_to_i18n(listing: dict, detected_language: str = 'en') -> dict:
        """
        Migrate existing listing data to i18n format.
        
        Args:
            listing: Existing listing data
            detected_language: Language of the existing content
            
        Returns:
            Migrated listing data with i18n structure
        """
        migrated = listing.copy()
        
        # Migrate title
        if 'title' in listing and listing['title']:
            migrated['title_i18n'] = MultilingualText()
            migrated['title_i18n'].set_text(detected_language, listing['title'])
        
        # Migrate description
        if 'description' in listing and listing['description']:
            migrated['description_i18n'] = MultilingualText()
            migrated['description_i18n'].set_text(detected_language, listing['description'])
        
        # Migrate location
        if any(field in listing for field in ['address', 'city', 'district']):
            location = GeoLocation()
            
            # Copy geographic coordinates
            if 'latitude' in listing:
                location.latitude = listing['latitude']
            if 'longitude' in listing:
                location.longitude = listing['longitude']
            if 'postal_code' in listing:
                location.postal_code = listing['postal_code']
            
            # Migrate multilingual location fields
            if 'address' in listing and listing['address']:
                location.address = listing['address']
                location.address_i18n = MultilingualText()
                location.address_i18n.set_text(detected_language, listing['address'])
            
            if 'city' in listing and listing['city']:
                location.city = listing['city']
                location.city_i18n = MultilingualText()
                location.city_i18n.set_text(detected_language, listing['city'])
            
            if 'district' in listing and listing['district']:
                location.district = listing['district']
                location.district_i18n = MultilingualText()
                location.district_i18n.set_text(detected_language, listing['district'])
            
            migrated['location'] = location.dict()
        
        # Migrate features
        if 'features' in listing and listing['features']:
            migrated['features_i18n'] = MultilingualFeatures()
            setattr(migrated['features_i18n'], detected_language, listing['features'])
        
        # Migrate amenities
        if 'amenities' in listing and listing['amenities']:
            migrated['amenities_i18n'] = MultilingualFeatures()
            setattr(migrated['amenities_i18n'], detected_language, listing['amenities'])
        
        # Set language metadata
        migrated['detected_language'] = detected_language
        migrated['available_languages'] = [detected_language]
        
        return migrated