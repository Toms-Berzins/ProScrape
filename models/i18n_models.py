"""
Internationalized Pydantic models for API responses.
Extends base models with localized formatting and translation support.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, computed_field
from bson import ObjectId

from models.listing import ListingBase, ListingResponse, PaginatedListingResponse
from utils.i18n import (
    get_current_language,
    LocalizedFormatter,
    CurrencyFormatter,
    DateTimeFormatter,
    NumberFormatter,
    get_language_name
)
from utils.translation_manager import t


class LocalizedListingResponse(ListingResponse):
    """Localized version of ListingResponse with formatted fields."""
    
    @computed_field
    @property
    def localized_data(self) -> Dict[str, Any]:
        """Computed field with all localized formatting."""
        language = get_current_language()
        formatter = LocalizedFormatter(language)
        
        # Get base listing data
        base_data = self.model_dump()
        
        # Apply localized formatting
        localized = formatter.format_listing_data(base_data)
        
        # Add additional locale-specific metadata
        localized.update({
            "language": language,
            "language_name": get_language_name(language, language),
            "currency_symbol": "€",
            "locale_info": {
                "date_format": DateTimeFormatter.format_date(self.posted_date, language) if self.posted_date else None,
                "relative_date": DateTimeFormatter.format_relative_date(self.posted_date, language) if self.posted_date else None,
                "formatted_price": CurrencyFormatter.format_price(self.price, language) if self.price else None,
                "formatted_area": NumberFormatter.format_area(self.area_sqm, language) if self.area_sqm else None,
                "formatted_rooms": NumberFormatter.format_rooms(self.rooms, language) if self.rooms else None,
                "formatted_floor": NumberFormatter.format_floor(self.floor, language) if self.floor else None,
            }
        })
        
        return localized
    
    @computed_field
    @property
    def display_title(self) -> str:
        """Localized display title."""
        return self.title or t("api.messages.no_title", fallback="No title")
    
    @computed_field
    @property
    def display_description(self) -> str:
        """Localized display description."""
        return self.description or t("api.messages.no_description", fallback="No description available")
    
    @computed_field
    @property
    def display_price(self) -> str:
        """Formatted price for display."""
        if self.price:
            return CurrencyFormatter.format_price(self.price, get_current_language())
        return t("api.messages.price_on_request", fallback="Price on request")
    
    @computed_field
    @property
    def display_area(self) -> str:
        """Formatted area for display."""
        if self.area_sqm:
            return NumberFormatter.format_area(self.area_sqm, get_current_language())
        return t("api.messages.area_not_specified", fallback="Area not specified")
    
    @computed_field
    @property
    def display_location(self) -> str:
        """Formatted location for display."""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.district:
            parts.append(self.district)
        
        if parts:
            return ", ".join(parts)
        return t("api.messages.location_not_specified", fallback="Location not specified")
    
    @computed_field
    @property
    def display_property_type(self) -> str:
        """Localized property type."""
        if not self.property_type:
            return t("api.messages.property_type_not_specified", fallback="Property type not specified")
        
        # Try to get localized property type
        type_key = f"properties.types.{self.property_type.lower()}"
        return t(type_key, fallback=self.property_type.title())
    
    @computed_field
    @property
    def display_listing_type(self) -> str:
        """Localized listing type."""
        if not self.listing_type:
            return t("api.messages.listing_type_not_specified", fallback="Listing type not specified")
        
        # Try to get localized listing type
        type_key = f"properties.listing_types.{self.listing_type.lower()}"
        return t(type_key, fallback=self.listing_type.title())
    
    @computed_field
    @property
    def display_posted_date(self) -> str:
        """Formatted posted date."""
        if self.posted_date:
            return DateTimeFormatter.format_date(self.posted_date, get_current_language())
        return t("api.messages.date_not_available", fallback="Date not available")
    
    @computed_field
    @property
    def display_posted_date_relative(self) -> str:
        """Relative posted date (e.g., "2 days ago")."""
        if self.posted_date:
            return DateTimeFormatter.format_relative_date(self.posted_date, get_current_language())
        return t("api.messages.date_not_available", fallback="Date not available")


class LocalizedPaginatedListingResponse(BaseModel):
    """Localized paginated response for listings."""
    
    items: List[LocalizedListingResponse]
    total: int = Field(..., description="Total number of items matching the query")
    page: int = Field(..., description="Current page number (1-based)")
    limit: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
    
    @computed_field
    @property
    def pagination_info(self) -> Dict[str, Any]:
        """Localized pagination information."""
        language = get_current_language()
        
        start_item = (self.page - 1) * self.limit + 1
        end_item = min(self.page * self.limit, self.total)
        
        return {
            "language": language,
            "current_page_text": t("api.pagination.page", fallback="Page"),
            "of_text": t("api.pagination.of", fallback="of"),
            "items_text": t("api.pagination.items", fallback="items"),
            "showing_text": t("api.pagination.showing", fallback="Showing"),
            "to_text": t("api.pagination.to", fallback="to"),
            "display_text": t(
                "api.pagination.display",
                fallback="Showing {start} to {end} of {total} items",
                start=start_item,
                end=end_item,
                total=self.total
            ),
            "page_display": f"{self.page} {t('api.pagination.of', fallback='of')} {self.total_pages}",
            "navigation": {
                "previous_text": t("api.pagination.previous", fallback="Previous"),
                "next_text": t("api.pagination.next", fallback="Next"),
                "first_text": t("api.pagination.first", fallback="First"),
                "last_text": t("api.pagination.last", fallback="Last")
            }
        }


class LocalizedStatisticsResponse(BaseModel):
    """Localized statistics response."""
    
    total_listings: int
    by_source: Dict[str, int]
    by_property_type: Dict[str, int]
    by_listing_type: Dict[str, int]
    top_cities: Dict[str, int]
    price_stats: Optional[Dict[str, float]]
    
    @computed_field
    @property
    def localized_stats(self) -> Dict[str, Any]:
        """Localized statistics with translated labels."""
        language = get_current_language()
        
        return {
            "language": language,
            "total_listings": {
                "value": self.total_listings,
                "label": t("api.stats.total_listings", fallback="Total Listings")
            },
            "by_source": {
                "label": t("api.stats.by_source", fallback="By Source"),
                "data": {
                    source: {
                        "value": count,
                        "label": t(f"sources.{source}", fallback=source.title())
                    }
                    for source, count in self.by_source.items()
                }
            },
            "by_property_type": {
                "label": t("api.stats.by_property_type", fallback="By Property Type"),
                "data": {
                    prop_type: {
                        "value": count,
                        "label": t(f"properties.types.{prop_type.lower()}", fallback=prop_type.title())
                    }
                    for prop_type, count in self.by_property_type.items()
                }
            },
            "by_listing_type": {
                "label": t("api.stats.by_listing_type", fallback="By Listing Type"),
                "data": {
                    listing_type: {
                        "value": count,
                        "label": t(f"properties.listing_types.{listing_type.lower()}", fallback=listing_type.title())
                    }
                    for listing_type, count in self.by_listing_type.items()
                }
            },
            "top_cities": {
                "label": t("api.stats.top_cities", fallback="Top Cities"),
                "data": self.top_cities
            },
            "price_stats": self._format_price_stats() if self.price_stats else None
        }
    
    def _format_price_stats(self) -> Optional[Dict[str, Any]]:
        """Format price statistics with localized currency."""
        if not self.price_stats:
            return None
        
        language = get_current_language()
        
        return {
            "label": t("api.stats.price_statistics", fallback="Price Statistics"),
            "average_price": {
                "value": self.price_stats.get("avg_price"),
                "formatted": CurrencyFormatter.format_price(self.price_stats.get("avg_price"), language),
                "label": t("api.stats.average_price", fallback="Average Price")
            },
            "min_price": {
                "value": self.price_stats.get("min_price"),
                "formatted": CurrencyFormatter.format_price(self.price_stats.get("min_price"), language),
                "label": t("api.stats.minimum_price", fallback="Minimum Price")
            },
            "max_price": {
                "value": self.price_stats.get("max_price"),
                "formatted": CurrencyFormatter.format_price(self.price_stats.get("max_price"), language),
                "label": t("api.stats.maximum_price", fallback="Maximum Price")
            }
        }


class LocalizedErrorResponse(BaseModel):
    """Localized error response."""
    
    error: str
    message: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    @computed_field
    @property
    def localized_error(self) -> Dict[str, Any]:
        """Localized error information."""
        language = get_current_language()
        
        # Try to get localized error message
        error_key = f"api.errors.{self.error.lower().replace(' ', '_')}"
        localized_message = t(error_key, fallback=self.message)
        
        return {
            "language": language,
            "error_code": self.error,
            "message": localized_message,
            "original_message": self.message,
            "status_code": self.status_code,
            "timestamp": DateTimeFormatter.format_datetime(self.timestamp, language),
            "request_id": self.request_id,
            "user_friendly_message": self._get_user_friendly_message()
        }
    
    def _get_user_friendly_message(self) -> str:
        """Get user-friendly error message."""
        error_mappings = {
            "internal_server_error": "api.errors.user_friendly.server_error",
            "not_found": "api.errors.user_friendly.not_found",
            "validation_error": "api.errors.user_friendly.validation_error",
            "unauthorized": "api.errors.user_friendly.unauthorized",
            "forbidden": "api.errors.user_friendly.forbidden",
            "bad_request": "api.errors.user_friendly.bad_request"
        }
        
        error_key = error_mappings.get(
            self.error.lower().replace(' ', '_'),
            "api.errors.user_friendly.generic"
        )
        
        return t(error_key, fallback="An error occurred. Please try again later.")


class LanguageInfo(BaseModel):
    """Information about a supported language."""
    
    code: str = Field(..., description="Language code (en, lv, ru)")
    name: str = Field(..., description="Language name in its own language")
    name_en: str = Field(..., description="Language name in English")
    name_local: str = Field(..., description="Language name in current locale")
    is_default: bool = Field(False, description="Whether this is the default language")
    is_current: bool = Field(False, description="Whether this is the current language")
    switch_url: Optional[str] = Field(None, description="URL to switch to this language")
    
    @computed_field
    @property
    def display_info(self) -> Dict[str, Any]:
        """Display information for the language."""
        current_lang = get_current_language()
        
        return {
            "code": self.code,
            "name": get_language_name(self.code, self.code),
            "name_in_current_locale": get_language_name(self.code, current_lang),
            "is_current": self.code == current_lang,
            "is_default": self.is_default,
            "direction": "ltr",  # All supported languages are LTR
            "flag_emoji": self._get_flag_emoji(),
            "switch_text": t(
                f"languages.switch_to_{self.code}",
                fallback=f"Switch to {get_language_name(self.code, current_lang)}"
            )
        }
    
    def _get_flag_emoji(self) -> str:
        """Get flag emoji for the language."""
        flag_map = {
            "en": "🇬🇧",
            "lv": "🇱🇻", 
            "ru": "🇷🇺"
        }
        return flag_map.get(self.code, "🏳️")


class LocalizedValidationError(BaseModel):
    """Localized validation error details."""
    
    field: str
    message: str
    error_type: str
    input_value: Any = None
    
    @computed_field
    @property
    def localized_error(self) -> Dict[str, Any]:
        """Localized validation error."""
        language = get_current_language()
        
        # Map error types to translation keys
        error_key_map = {
            "missing": "api.validation.required",
            "type_error": "api.validation.invalid",
            "value_error": "api.validation.invalid",
            "assertion_error": "api.validation.invalid",
            "string_too_short": "api.validation.min_length",
            "string_too_long": "api.validation.max_length",
            "greater_than_equal": "api.validation.minimum_value",
            "less_than_equal": "api.validation.maximum_value"
        }
        
        error_key = error_key_map.get(self.error_type, "api.validation.invalid")
        
        # Get localized field name
        field_key = f"api.fields.{self.field}"
        localized_field = t(field_key, fallback=self.field.replace('_', ' ').title())
        
        # Get localized error message
        localized_message = t(error_key, fallback=self.message, field=localized_field)
        
        return {
            "field": self.field,
            "localized_field": localized_field,
            "message": localized_message,
            "original_message": self.message,
            "error_type": self.error_type,
            "input_value": self.input_value,
            "language": language
        }


class ApiMetadataResponse(BaseModel):
    """API metadata with localization information."""
    
    version: str = "1.0.0"
    title: str = "ProScrape API"
    description: str = "API for accessing scraped real estate data from Latvian websites"
    
    @computed_field
    @property
    def localized_metadata(self) -> Dict[str, Any]:
        """Localized API metadata."""
        language = get_current_language()
        
        return {
            "version": self.version,
            "title": t("api.title", fallback=self.title),
            "description": t("api.description", fallback=self.description),
            "language": language,
            "language_name": get_language_name(language, language),
            "supported_languages": [
                {
                    "code": lang_code,
                    "name": get_language_name(lang_code, language),
                    "native_name": get_language_name(lang_code, lang_code)
                }
                for lang_code in ["en", "lv", "ru"]
            ],
            "timezone": "Europe/Riga",
            "currency": "EUR",
            "date_format": "d.m.Y" if language in ["lv", "ru"] else "m/d/Y",
            "decimal_separator": "," if language in ["lv", "ru"] else ".",
            "thousands_separator": " " if language in ["lv", "ru"] else ","
        }