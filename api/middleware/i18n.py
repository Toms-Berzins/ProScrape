"""
Internationalization middleware for FastAPI.

Handles language detection, request context, and response localization.
"""

import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import contextvars
import json

from utils.i18n import detect_language_from_request, i18n_manager, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

# Context variable to store current language for the request
current_language: contextvars.ContextVar[str] = contextvars.ContextVar(
    'current_language', default=DEFAULT_LANGUAGE
)

# Context variable to store current request for access in dependencies
current_request: contextvars.ContextVar[Optional[Request]] = contextvars.ContextVar(
    'current_request', default=None
)


class I18nMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle internationalization for API requests.
    
    Features:
    - Automatic language detection from headers, parameters, or user preferences
    - Sets language context for the entire request lifecycle
    - Optionally localizes error responses
    - Adds language information to response headers
    """
    
    def __init__(
        self,
        app,
        default_language: str = DEFAULT_LANGUAGE,
        localize_errors: bool = True,
        add_language_header: bool = True
    ):
        super().__init__(app)
        self.default_language = default_language
        self.localize_errors = localize_errors
        self.add_language_header = add_language_header
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and detect language."""
        
        # Detect language from various sources
        lang = self._detect_request_language(request)
        
        # Set language in context for the entire request
        current_language_token = current_language.set(lang)
        current_request_token = current_request.set(request)
        
        # Log language detection for debugging
        logger.debug(f"Detected language: {lang} for {request.url.path}")
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add language information to response headers
            if self.add_language_header:
                response.headers["Content-Language"] = lang
                response.headers["X-Detected-Language"] = lang
            
            # If it's a JSON response and we want to localize errors
            if (self.localize_errors and 
                hasattr(response, 'status_code') and 
                response.status_code >= 400 and
                response.headers.get("content-type", "").startswith("application/json")):
                
                response = await self._localize_error_response(response, lang)
            
            return response
            
        except Exception as e:
            # Handle errors during request processing
            logger.error(f"Error in i18n middleware: {e}")
            
            # Create localized error response
            if self.localize_errors:
                error_message = i18n_manager.translate_api_message(
                    "errors.internal_server_error", lang
                )
                return JSONResponse(
                    status_code=500,
                    content={"detail": error_message, "error_code": "internal_server_error"},
                    headers={"Content-Language": lang}
                )
            raise
            
        finally:
            # Reset context variables
            current_language.reset(current_language_token)
            current_request.reset(current_request_token)
    
    def _detect_request_language(self, request: Request) -> str:
        """Detect language for the current request."""
        
        # Get language from query parameter
        lang_param = request.query_params.get('lang') or request.query_params.get('language')
        
        # Get Accept-Language header
        accept_language = request.headers.get('Accept-Language')
        
        # TODO: Get user preference from database/session
        # This could be implemented by checking user profile or session data
        user_preference = None
        
        # Detect language using utility function
        return detect_language_from_request(
            accept_language=accept_language,
            lang_param=lang_param,
            user_preference=user_preference
        )
    
    async def _localize_error_response(self, response: Response, lang: str) -> Response:
        """Localize error response content."""
        try:
            # Get response body
            body = response.body
            
            # Parse JSON content
            if body:
                content = json.loads(bytes(body).decode())
                
                # Localize common error fields
                if isinstance(content, dict):
                    # Localize 'detail' field (FastAPI default error field)
                    if 'detail' in content:
                        if isinstance(content['detail'], str):
                            # Try to localize common error messages
                            localized_detail = self._localize_error_detail(content['detail'], lang)
                            content['detail'] = localized_detail
                        elif isinstance(content['detail'], list):
                            # Handle validation errors
                            content['detail'] = self._localize_validation_errors(content['detail'], lang)
                    
                    # Add language info to error response
                    content['language'] = lang
                
                # Create new response with localized content
                return JSONResponse(
                    content=content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            return response
            
        except Exception as e:
            logger.warning(f"Failed to localize error response: {e}")
            return response
    
    def _localize_error_detail(self, detail: str, lang: str) -> str:
        """Localize error detail message."""
        # Map common FastAPI error messages to translation keys
        error_mappings = {
            "Not found": "errors.not_found",
            "Internal server error": "errors.internal_server_error",
            "Validation error": "errors.validation_error",
            "Unauthorized": "errors.unauthorized",
            "Forbidden": "errors.forbidden",
            "Bad request": "errors.bad_request",
            "Method not allowed": "errors.method_not_allowed",
            "Unprocessable Entity": "errors.unprocessable_entity"
        }
        
        # Check for direct mappings
        for english_text, translation_key in error_mappings.items():
            if english_text.lower() in detail.lower():
                return i18n_manager.translate_api_message(translation_key, lang)
        
        # Return original if no mapping found
        return detail
    
    def _localize_validation_errors(self, validation_errors: list, lang: str) -> list:
        """Localize FastAPI validation errors."""
        localized_errors = []
        
        for error in validation_errors:
            if isinstance(error, dict):
                localized_error = error.copy()
                
                # Localize error message
                if 'msg' in error:
                    localized_error['msg'] = self._localize_validation_message(
                        error.get('msg', ''), 
                        error.get('type', ''),
                        error.get('loc', []),
                        lang
                    )
                
                localized_errors.append(localized_error)
            else:
                localized_errors.append(error)
        
        return localized_errors
    
    def _localize_validation_message(self, msg: str, error_type: str, 
                                   location: list, lang: str) -> str:
        """Localize individual validation error message."""
        
        # Extract field name from location
        field_name = location[-1] if location else "field"
        
        # Map validation error types to translation keys
        validation_mappings = {
            "value_error.missing": "validation.required",
            "type_error.integer": "validation.must_be_integer",
            "type_error.float": "validation.must_be_number",
            "type_error.bool": "validation.must_be_boolean",
            "value_error.email": "validation.invalid_email",
            "value_error.url": "validation.invalid_url",
            "value_error.any_str.min_length": "validation.min_length",
            "value_error.any_str.max_length": "validation.max_length",
            "value_error.number.not_ge": "validation.minimum_value",
            "value_error.number.not_le": "validation.maximum_value"
        }
        
        # Try to find translation for error type
        translation_key = validation_mappings.get(error_type)
        if translation_key:
            return i18n_manager.translate_api_message(
                translation_key, lang, field=field_name
            )
        
        # Fallback: try to localize common validation messages
        if "required" in msg.lower():
            return i18n_manager.translate_api_message(
                "validation.required", lang, field=field_name
            )
        elif "invalid" in msg.lower():
            return i18n_manager.translate_api_message(
                "validation.invalid", lang, field=field_name
            )
        
        # Return original message if no translation found
        return msg


# Dependency function to get current language in route handlers
def get_current_language() -> str:
    """Get the current request language from context."""
    return current_language.get(DEFAULT_LANGUAGE)


# Dependency function to get current request in route handlers
def get_current_request() -> Optional[Request]:
    """Get the current request from context."""
    return current_request.get(None)


# Helper functions for use in route handlers
def t(key: str, **kwargs) -> str:
    """Shortcut for translations using current request language."""
    lang = get_current_language()
    return i18n_manager.get_translation(key, lang, 'api', **kwargs)


def translate_error(error_code: str, **kwargs) -> str:
    """Translate error message using current request language."""
    lang = get_current_language()
    return i18n_manager.translate_api_message(f"errors.{error_code}", lang, **kwargs)


def localize_listing_data(listing_data: dict) -> dict:
    """Localize listing data fields for current request language."""
    lang = get_current_language()
    localized = listing_data.copy()
    
    # Translate city name
    if 'city' in localized and localized['city']:
        localized['city_localized'] = i18n_manager.translate_city_name(
            localized['city'], lang
        )
    
    # Translate property type
    if 'property_type' in localized and localized['property_type']:
        localized['property_type_localized'] = i18n_manager.translate_property_type(
            localized['property_type'], lang
        )
    
    # Translate listing type
    if 'listing_type' in localized and localized['listing_type']:
        localized['listing_type_localized'] = i18n_manager.translate_listing_type(
            localized['listing_type'], lang
        )
    
    # Translate features
    if 'features' in localized and localized['features']:
        localized['features_localized'] = i18n_manager.translate_features(
            localized['features'], lang
        )
    
    # Format price
    if 'price' in localized and localized['price'] is not None:
        localized['price_formatted'] = i18n_manager.format_price(
            localized['price'], lang, 
            localized.get('price_currency', 'EUR')
        )
    
    # Format area
    if 'area_sqm' in localized and localized['area_sqm'] is not None:
        localized['area_formatted'] = i18n_manager.format_area(
            localized['area_sqm'], lang
        )
    
    # Format dates
    for date_field in ['posted_date', 'updated_date', 'scraped_at']:
        if date_field in localized and localized[date_field]:
            localized[f"{date_field}_formatted"] = i18n_manager.format_datetime(
                localized[date_field], lang
            )
    
    return localized