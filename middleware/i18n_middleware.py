"""
FastAPI i18n middleware for automatic language detection and request context management.
"""

import uuid
import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from utils.i18n import (
    LanguageDetector,
    set_current_language,
    set_current_request_id,
    get_current_language,
    SupportedLanguage
)
from config.settings import settings

logger = logging.getLogger(__name__)


class I18nMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for internationalization support.
    
    Features:
    - Automatic language detection from multiple sources
    - Request-scoped language context
    - Language preference persistence via cookies
    - Request ID tracking for logging
    - Performance monitoring
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_language: str = "lv",
        cookie_name: str = "proscrape_lang",
        cookie_max_age: int = 30 * 24 * 3600,  # 30 days
        query_param: str = "lang",
        header_name: str = "X-Language"
    ):
        super().__init__(app)
        self.default_language = default_language
        self.cookie_name = cookie_name
        self.cookie_max_age = cookie_max_age
        self.query_param = query_param
        self.header_name = header_name
        
        # Validate default language
        if default_language not in [lang.value for lang in SupportedLanguage]:
            logger.warning(f"Invalid default language '{default_language}', using 'lv'")
            self.default_language = SupportedLanguage.LATVIAN
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and detect language."""
        start_time = time.time()
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        set_current_request_id(request_id)
        
        # Detect language from multiple sources
        detected_language = self._detect_language(request)
        set_current_language(detected_language)
        
        # Add language info to request state
        request.state.language = detected_language
        request.state.request_id = request_id
        request.state.i18n_start_time = start_time
        
        # Add request ID to headers for debugging
        if settings.api_debug:
            logger.debug(f"Request {request_id}: {request.method} {request.url} - Language: {detected_language}")
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add language info to response headers
            response.headers["X-Language"] = detected_language
            response.headers["X-Request-ID"] = request_id
            
            # Set language cookie if it changed or doesn't exist
            current_cookie_lang = request.cookies.get(self.cookie_name)
            if current_cookie_lang != detected_language:
                response.set_cookie(
                    key=self.cookie_name,
                    value=detected_language,
                    max_age=self.cookie_max_age,
                    httponly=True,
                    samesite="lax",
                    secure=request.url.scheme == "https"
                )
            
            # Add performance metrics
            processing_time = time.time() - start_time
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
            
            if settings.api_debug:
                logger.debug(f"Request {request_id} completed in {processing_time:.3f}s")
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Request {request_id} failed after {processing_time:.3f}s: {e}")
            raise
    
    def _detect_language(self, request: Request) -> str:
        """
        Detect language from multiple sources in order of priority:
        1. Query parameter (?lang=en)
        2. Custom header (X-Language: en)
        3. Cookie (proscrape_lang=en)
        4. Accept-Language header
        5. Path prefix (/en/api/...)
        6. Default language
        """
        
        # 1. Query parameter (highest priority)
        query_lang = request.query_params.get(self.query_param)
        if query_lang and self._is_supported_language(query_lang):
            logger.debug(f"Language detected from query parameter: {query_lang}")
            return query_lang
        
        # 2. Custom header
        header_lang = request.headers.get(self.header_name)
        if header_lang and self._is_supported_language(header_lang):
            logger.debug(f"Language detected from header: {header_lang}")
            return header_lang
        
        # 3. Cookie
        cookie_lang = request.cookies.get(self.cookie_name)
        if cookie_lang and self._is_supported_language(cookie_lang):
            logger.debug(f"Language detected from cookie: {cookie_lang}")
            return cookie_lang
        
        # 4. Accept-Language header
        accept_language = request.headers.get("Accept-Language")
        if accept_language:
            detected_lang = LanguageDetector.detect_from_accept_language(accept_language)
            if self._is_supported_language(detected_lang):
                logger.debug(f"Language detected from Accept-Language: {detected_lang}")
                return detected_lang
        
        # 5. Path prefix detection (e.g., /en/api/listings)
        path = str(request.url.path)
        path_parts = path.strip('/').split('/')
        if path_parts and len(path_parts[0]) == 2:
            potential_lang = path_parts[0].lower()
            if self._is_supported_language(potential_lang):
                logger.debug(f"Language detected from path: {potential_lang}")
                return potential_lang
        
        # 6. Default language
        logger.debug(f"Using default language: {self.default_language}")
        return self.default_language
    
    def _is_supported_language(self, language: str) -> bool:
        """Check if a language code is supported."""
        if not language:
            return False
        
        language = language.lower().strip()
        supported_codes = [lang.value for lang in SupportedLanguage]
        return language in supported_codes


class LanguageSwitchMiddleware(BaseHTTPMiddleware):
    """
    Additional middleware for handling language switching via special endpoints.
    Handles URLs like /switch-language/en that redirect back to referrer.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        switch_path_prefix: str = "/switch-language",
        cookie_name: str = "proscrape_lang",
        cookie_max_age: int = 30 * 24 * 3600
    ):
        super().__init__(app)
        self.switch_path_prefix = switch_path_prefix
        self.cookie_name = cookie_name
        self.cookie_max_age = cookie_max_age
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle language switching requests."""
        path = str(request.url.path)
        
        # Check if this is a language switch request
        if path.startswith(self.switch_path_prefix):
            return await self._handle_language_switch(request)
        
        # Otherwise, continue with normal processing
        return await call_next(request)
    
    async def _handle_language_switch(self, request: Request) -> Response:
        """Handle language switching and redirect."""
        from fastapi.responses import RedirectResponse
        
        path = str(request.url.path)
        
        # Extract language from path (e.g., /switch-language/en -> en)
        parts = path.strip('/').split('/')
        if len(parts) >= 2:
            new_language = parts[1].lower()
            
            # Validate language
            if new_language in [lang.value for lang in SupportedLanguage]:
                # Get referrer URL for redirect
                referrer = request.headers.get("Referer")
                redirect_url = referrer or "/"
                
                # Create redirect response
                response = RedirectResponse(url=redirect_url, status_code=302)
                
                # Set language cookie
                response.set_cookie(
                    key=self.cookie_name,
                    value=new_language,
                    max_age=self.cookie_max_age,
                    httponly=True,
                    samesite="lax",
                    secure=request.url.scheme == "https"
                )
                
                logger.info(f"Language switched to {new_language}, redirecting to {redirect_url}")
                return response
        
        # Invalid language switch request
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid language switch request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enriching request context with i18n information.
    Adds helpful context variables that can be used in templates or API responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enrich request context."""
        
        # Add i18n context to request
        if not hasattr(request.state, 'language'):
            request.state.language = get_current_language()
        
        # Add helper functions to request state
        request.state.get_language_name = self._get_language_name
        request.state.is_rtl = self._is_rtl_language
        request.state.get_language_direction = self._get_language_direction
        
        return await call_next(request)
    
    def _get_language_name(self, language_code: str = None, in_language: str = None) -> str:
        """Get language display name."""
        from utils.i18n import get_language_name
        if language_code is None:
            language_code = get_current_language()
        if in_language is None:
            in_language = get_current_language()
        return get_language_name(language_code, in_language)
    
    def _is_rtl_language(self, language_code: str = None) -> bool:
        """Check if language is right-to-left."""
        if language_code is None:
            language_code = get_current_language()
        
        # None of our supported languages are RTL, but this could be extended
        rtl_languages = {'ar', 'he', 'fa', 'ur'}
        return language_code in rtl_languages
    
    def _get_language_direction(self, language_code: str = None) -> str:
        """Get text direction for language."""
        return 'rtl' if self._is_rtl_language(language_code) else 'ltr'


def create_i18n_middleware_stack(
    app: ASGIApp,
    enable_language_switching: bool = True,
    enable_request_context: bool = True,
    **kwargs
) -> ASGIApp:
    """
    Create a complete i18n middleware stack.
    
    Args:
        app: FastAPI application
        enable_language_switching: Enable language switching endpoints
        enable_request_context: Enable request context enrichment
        **kwargs: Additional arguments for I18nMiddleware
        
    Returns:
        App with i18n middleware stack applied
    """
    
    # Apply middlewares in reverse order (last applied = first executed)
    
    # 1. Request context middleware (innermost - closest to app)
    if enable_request_context:
        app = RequestContextMiddleware(app)
    
    # 2. Language switching middleware
    if enable_language_switching:
        app = LanguageSwitchMiddleware(app)
    
    # 3. Main i18n middleware (outermost - first to process requests)
    app = I18nMiddleware(app, **kwargs)
    
    return app