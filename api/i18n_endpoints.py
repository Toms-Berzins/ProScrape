"""
Internationalized API endpoints for ProScrape.

These endpoints demonstrate how to integrate i18n functionality with FastAPI,
providing localized responses and error handling.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from models.i18n_listing import I18nListingResponse, I18nPaginatedListingResponse
from models.listing import ListingResponse
from utils.database import async_db
from utils.i18n import i18n_manager, DEFAULT_LANGUAGE
from api.middleware.i18n import (
    get_current_language, 
    get_current_request,
    t, 
    translate_error,
    localize_listing_data
)

logger = logging.getLogger(__name__)

# Create router for i18n endpoints
router = APIRouter(prefix="/i18n", tags=["Internationalization"])


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    try:
        languages = i18n_manager.get_supported_languages()
        current_lang = get_current_language()
        
        return {
            "supported_languages": languages,
            "current_language": current_lang,
            "default_language": DEFAULT_LANGUAGE,
            "message": t("messages.success")
        }
    except Exception as e:
        logger.error(f"Error getting languages: {e}")
        raise HTTPException(
            status_code=500, 
            detail=translate_error("internal_server_error")
        )


@router.get("/listings", response_model=I18nPaginatedListingResponse)
async def get_localized_listings(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=1000, description="Items per page"),
    city: Optional[str] = Query(None, description="Filter by city"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    listing_type: Optional[str] = Query(None, description="Filter by listing type"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum area"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum area"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    # Map bounds parameters
    north: Optional[float] = Query(None, description="Northern boundary"),
    south: Optional[float] = Query(None, description="Southern boundary"),
    east: Optional[float] = Query(None, description="Eastern boundary"),
    west: Optional[float] = Query(None, description="Western boundary"),
    sort_by: str = Query("scraped_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """
    Get listings with full localization support.
    
    Returns listings with:
    - Translated property types, listing types, features
    - Localized city names and districts  
    - Formatted prices and dates according to locale
    - Localized error messages
    """
    try:
        current_lang = get_current_language()
        collection = async_db.get_collection("listings")
        
        # Build filter query (same logic as original endpoint)
        filter_query = {}
        
        if city:
            filter_query["city"] = {"$regex": city, "$options": "i"}
        if property_type:
            filter_query["property_type"] = {"$regex": property_type, "$options": "i"}
        if listing_type:
            filter_query["listing_type"] = listing_type.lower()
        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
            filter_query["price"] = price_filter
        if min_area is not None or max_area is not None:
            area_filter = {}
            if min_area is not None:
                area_filter["$gte"] = min_area
            if max_area is not None:
                area_filter["$lte"] = max_area
            filter_query["area_sqm"] = area_filter
        if source_site:
            filter_query["source_site"] = source_site
        if date_from is not None or date_to is not None:
            scraped_filter = {}
            if date_from is not None:
                scraped_filter["$gte"] = date_from
            if date_to is not None:
                scraped_filter["$lte"] = date_to
            filter_query["scraped_at"] = scraped_filter
        
        # Map bounds filtering
        if north is not None and south is not None and east is not None and west is not None:
            filter_query["latitude"] = {"$gte": south, "$lte": north}
            filter_query["longitude"] = {"$gte": west, "$lte": east}
        
        # Build sort order
        sort_direction = 1 if sort_order == "asc" else -1
        offset = (page - 1) * limit
        
        # Get total count
        total_count = await collection.count_documents(filter_query)
        
        # Execute query
        cursor = collection.find(filter_query)
        cursor = cursor.sort(sort_by, sort_direction)
        cursor = cursor.skip(offset).limit(limit)
        
        listings = await cursor.to_list(length=limit)
        
        # Localize listings
        localized_listings = []
        for listing_data in listings:
            listing_data["id"] = str(listing_data["_id"])
            
            # Apply localization
            localized_data = localize_listing_data(listing_data)
            
            # Create localized response model
            localized_listing = I18nListingResponse(
                id=localized_data["id"],
                listing_id=localized_data["listing_id"],
                source_site=localized_data["source_site"],
                title=localized_data["title"],
                description=localized_data.get("description"),
                price=localized_data.get("price"),
                price_formatted=localized_data.get("price_formatted"),
                price_currency=localized_data.get("price_currency", "EUR"),
                property_type=localized_data.get("property_type"),
                property_type_localized=localized_data.get("property_type_localized"),
                listing_type=localized_data.get("listing_type"),
                listing_type_localized=localized_data.get("listing_type_localized"),
                area_sqm=localized_data.get("area_sqm"),
                area_formatted=localized_data.get("area_formatted"),
                rooms=localized_data.get("rooms"),
                floor=localized_data.get("floor"),
                total_floors=localized_data.get("total_floors"),
                address=localized_data.get("address"),
                city=localized_data.get("city"),
                city_localized=localized_data.get("city_localized"),
                district=localized_data.get("district"),
                district_localized=localized_data.get("district_localized"),
                postal_code=localized_data.get("postal_code"),
                latitude=localized_data.get("latitude"),
                longitude=localized_data.get("longitude"),
                features=localized_data.get("features", []),
                features_localized=localized_data.get("features_localized", []),
                amenities=localized_data.get("amenities", []),
                amenities_localized=localized_data.get("amenities_localized", []),
                image_urls=localized_data.get("image_urls", []),
                video_urls=localized_data.get("video_urls", []),
                posted_date=localized_data.get("posted_date"),
                posted_date_formatted=localized_data.get("posted_date_formatted"),
                updated_date=localized_data.get("updated_date"),
                updated_date_formatted=localized_data.get("updated_date_formatted"),
                scraped_at=localized_data["scraped_at"],
                scraped_at_formatted=localized_data.get("scraped_at_formatted"),
                source_url=localized_data["source_url"],
                language=current_lang,
                available_languages=localized_data.get("available_languages", [current_lang])
            )
            
            localized_listings.append(localized_listing)
        
        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return I18nPaginatedListingResponse(
            items=localized_listings,
            total=total_count,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            language=current_lang
        )
        
    except Exception as e:
        logger.error(f"Error fetching localized listings: {e}")
        raise HTTPException(
            status_code=500, 
            detail=translate_error("internal_server_error")
        )


@router.get("/listings/{listing_id}", response_model=I18nListingResponse)
async def get_localized_listing(listing_id: str):
    """Get a specific listing with full localization."""
    try:
        current_lang = get_current_language()
        collection = async_db.get_collection("listings")
        
        from bson import ObjectId
        if ObjectId.is_valid(listing_id):
            listing_data = await collection.find_one({"_id": ObjectId(listing_id)})
        else:
            listing_data = await collection.find_one({"listing_id": listing_id})
        
        if not listing_data:
            raise HTTPException(
                status_code=404, 
                detail=translate_error("not_found")
            )
        
        listing_data["id"] = str(listing_data["_id"])
        localized_data = localize_listing_data(listing_data)
        
        return I18nListingResponse(
            id=localized_data["id"],
            listing_id=localized_data["listing_id"],
            source_site=localized_data["source_site"],
            title=localized_data["title"],
            description=localized_data.get("description"),
            price=localized_data.get("price"),
            price_formatted=localized_data.get("price_formatted"),
            price_currency=localized_data.get("price_currency", "EUR"),
            property_type=localized_data.get("property_type"),
            property_type_localized=localized_data.get("property_type_localized"),
            listing_type=localized_data.get("listing_type"),
            listing_type_localized=localized_data.get("listing_type_localized"),
            area_sqm=localized_data.get("area_sqm"),
            area_formatted=localized_data.get("area_formatted"),
            rooms=localized_data.get("rooms"),
            floor=localized_data.get("floor"),
            total_floors=localized_data.get("total_floors"),
            address=localized_data.get("address"),
            city=localized_data.get("city"),
            city_localized=localized_data.get("city_localized"),
            district=localized_data.get("district"),
            district_localized=localized_data.get("district_localized"),
            postal_code=localized_data.get("postal_code"),
            latitude=localized_data.get("latitude"),
            longitude=localized_data.get("longitude"),
            features=localized_data.get("features", []),
            features_localized=localized_data.get("features_localized", []),
            amenities=localized_data.get("amenities", []),
            amenities_localized=localized_data.get("amenities_localized", []),
            image_urls=localized_data.get("image_urls", []),
            video_urls=localized_data.get("video_urls", []),
            posted_date=localized_data.get("posted_date"),
            posted_date_formatted=localized_data.get("posted_date_formatted"),
            updated_date=localized_data.get("updated_date"),
            updated_date_formatted=localized_data.get("updated_date_formatted"),
            scraped_at=localized_data["scraped_at"],
            scraped_at_formatted=localized_data.get("scraped_at_formatted"),
            source_url=localized_data["source_url"],
            language=current_lang,
            available_languages=localized_data.get("available_languages", [current_lang])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching localized listing {listing_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=translate_error("internal_server_error")
        )


@router.get("/search")
async def search_localized_listings(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Search listings with localized results and messages."""
    try:
        current_lang = get_current_language()
        collection = async_db.get_collection("listings")
        
        # Build search query
        filter_query = {
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"address": {"$regex": q, "$options": "i"}},
                {"city": {"$regex": q, "$options": "i"}},
                {"district": {"$regex": q, "$options": "i"}}
            ]
        }
        
        cursor = collection.find(filter_query)
        cursor = cursor.sort("scraped_at", -1)
        cursor = cursor.skip(offset).limit(limit)
        
        listings = await cursor.to_list(length=limit)
        
        if not listings:
            return {
                "results": [],
                "total": 0,
                "query": q,
                "language": current_lang,
                "message": t("messages.no_results")
            }
        
        # Localize results
        localized_results = []
        for listing_data in listings:
            listing_data["id"] = str(listing_data["_id"])
            localized_data = localize_listing_data(listing_data)
            localized_results.append(localized_data)
        
        return {
            "results": localized_results,
            "total": len(localized_results),
            "query": q,
            "language": current_lang,
            "message": t("messages.success")
        }
        
    except Exception as e:
        logger.error(f"Error searching localized listings: {e}")
        raise HTTPException(
            status_code=500, 
            detail=translate_error("internal_server_error")
        )


@router.get("/stats")
async def get_localized_statistics():
    """Get database statistics with localized labels."""
    try:
        current_lang = get_current_language()
        collection = async_db.get_collection("listings")
        
        # Get basic stats (same as original endpoint)
        total_count = await collection.count_documents({})
        
        # Source site stats
        source_stats = await collection.aggregate([
            {"$group": {"_id": "$source_site", "count": {"$sum": 1}}}
        ]).to_list(length=None)
        
        # Property type stats with localization
        property_type_stats = await collection.aggregate([
            {"$group": {"_id": "$property_type", "count": {"$sum": 1}}}
        ]).to_list(length=None)
        
        # Localize property types
        localized_property_stats = {}
        for stat in property_type_stats:
            original_type = stat["_id"]
            localized_type = i18n_manager.translate_property_type(original_type, current_lang)
            localized_property_stats[localized_type] = stat["count"]
        
        # Listing type stats with localization
        listing_type_stats = await collection.aggregate([
            {"$group": {"_id": "$listing_type", "count": {"$sum": 1}}}
        ]).to_list(length=None)
        
        localized_listing_stats = {}
        for stat in listing_type_stats:
            original_type = stat["_id"]
            localized_type = i18n_manager.translate_listing_type(original_type, current_lang)
            localized_listing_stats[localized_type] = stat["count"]
        
        # City stats with localization
        city_stats = await collection.aggregate([
            {"$group": {"_id": "$city", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]).to_list(length=None)
        
        localized_city_stats = {}
        for stat in city_stats:
            original_city = stat["_id"]
            localized_city = i18n_manager.translate_city_name(original_city, current_lang)
            localized_city_stats[localized_city] = stat["count"]
        
        # Price statistics
        price_stats = await collection.aggregate([
            {"$match": {"price": {"$ne": None}}},
            {"$group": {
                "_id": None,
                "avg_price": {"$avg": "$price"},
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"}
            }}
        ]).to_list(length=None)
        
        # Format prices according to locale
        formatted_price_stats = None
        if price_stats:
            stats = price_stats[0]
            formatted_price_stats = {
                "average_price": i18n_manager.format_price(stats["avg_price"], current_lang),
                "minimum_price": i18n_manager.format_price(stats["min_price"], current_lang),
                "maximum_price": i18n_manager.format_price(stats["max_price"], current_lang),
                "raw_values": stats  # Keep raw values for API consumers
            }
        
        return {
            "total_listings": total_count,
            "by_source": {item["_id"]: item["count"] for item in source_stats},
            "by_property_type": localized_property_stats,
            "by_listing_type": localized_listing_stats,
            "top_cities": localized_city_stats,
            "price_statistics": formatted_price_stats,
            "language": current_lang,
            "labels": {
                "total_listings": t("stats.total_listings"),
                "by_source": t("stats.by_source"),
                "by_property_type": t("stats.by_property_type"),
                "by_listing_type": t("stats.by_listing_type"),
                "top_cities": t("stats.top_cities"),
                "price_statistics": t("stats.price_statistics")
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching localized statistics: {e}")
        raise HTTPException(
            status_code=500, 
            detail=translate_error("internal_server_error")
        )


@router.post("/reload-translations")
async def reload_translations():
    """Reload translation files (admin endpoint)."""
    try:
        current_lang = get_current_language()
        
        # Reload translations
        i18n_manager.reload_translations()
        
        return {
            "message": t("messages.success"),
            "detail": "Translation files reloaded successfully",
            "language": current_lang,
            "supported_languages": i18n_manager.get_supported_languages()
        }
        
    except Exception as e:
        logger.error(f"Error reloading translations: {e}")
        raise HTTPException(
            status_code=500, 
            detail=translate_error("internal_server_error")
        )


@router.get("/demo")
async def i18n_demo():
    """
    Demonstration endpoint showing various i18n features.
    
    This endpoint showcases:
    - Language detection
    - Message translation
    - Number formatting
    - Date formatting
    - Error handling
    """
    try:
        current_lang = get_current_language()
        current_request = get_current_request()
        
        # Sample data for demonstration
        sample_price = 125000.50
        sample_area = 75.5
        sample_date = datetime.now()
        
        demo_data = {
            "language_info": {
                "detected_language": current_lang,
                "supported_languages": i18n_manager.get_supported_languages(),
                "request_headers": {
                    "accept_language": current_request.headers.get("Accept-Language") if current_request else None,
                    "user_agent": current_request.headers.get("User-Agent") if current_request else None
                }
            },
            "translations": {
                "welcome_message": t("messages.welcome"),
                "success_message": t("messages.success"),
                "loading_message": t("messages.loading"),
                "search_placeholder": t("messages.search_placeholder")
            },
            "formatting_examples": {
                "price_formatted": i18n_manager.format_price(sample_price, current_lang),
                "area_formatted": i18n_manager.format_area(sample_area, current_lang),
                "date_formatted": i18n_manager.format_datetime(sample_date, current_lang),
                "raw_values": {
                    "price": sample_price,
                    "area": sample_area,
                    "date": sample_date.isoformat()
                }
            },
            "property_translations": {
                "apartment": i18n_manager.translate_property_type("apartment", current_lang),
                "house": i18n_manager.translate_property_type("house", current_lang),
                "sell": i18n_manager.translate_listing_type("sell", current_lang),
                "rent": i18n_manager.translate_listing_type("rent", current_lang)
            },
            "city_translations": {
                "riga": i18n_manager.translate_city_name("Riga", current_lang),
                "jurmala": i18n_manager.translate_city_name("Jurmala", current_lang),
                "liepaja": i18n_manager.translate_city_name("Liepaja", current_lang)
            },
            "feature_translations": i18n_manager.translate_features([
                "balcony", "parking", "elevator", "garden"
            ], current_lang)
        }
        
        return demo_data
        
    except Exception as e:
        logger.error(f"Error in i18n demo: {e}")
        raise HTTPException(
            status_code=500, 
            detail=translate_error("internal_server_error")
        )