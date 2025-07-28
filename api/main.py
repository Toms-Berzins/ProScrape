from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import json
import csv
import io

# Import enhanced WebSocket manager
from websocket.enhanced_manager import enhanced_manager

from models.listing import ListingResponse, Listing, PaginatedListingResponse
from models.i18n_models import (
    LocalizedListingResponse,
    LocalizedPaginatedListingResponse,
    LocalizedStatisticsResponse,
    LocalizedErrorResponse,
    LanguageInfo
)
from utils.database import async_db
from utils.proxies import proxy_rotator
from utils.alerting import alert_manager
from utils.translation_manager import translation_manager, t
from utils.i18n import get_current_language, SupportedLanguage
from middleware.i18n_middleware import I18nMiddleware
from config.settings import settings
try:
    from config.docker_settings import docker_settings
except (ImportError, Exception):
    docker_settings = settings


# Health check functions for Docker services
def check_mongodb():
    """Check MongoDB connection health."""
    try:
        # This will be async in the actual health check endpoint
        return {"status": "healthy", "message": "MongoDB connection active"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"MongoDB error: {str(e)}"}


def check_redis():
    """Check Redis connection health."""
    try:
        import redis
        redis_url = getattr(docker_settings, 'redis_url', settings.redis_url)
        r = redis.from_url(redis_url)
        r.ping()
        return {"status": "healthy", "message": "Redis connection active"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Redis error: {str(e)}"}


def check_celery_workers():
    """Check Celery workers health."""
    try:
        from tasks.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            return {"status": "healthy", "message": f"Celery workers active: {len(stats)}"}
        else:
            return {"status": "unhealthy", "message": "No Celery workers found"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Celery error: {str(e)}"}

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


# Old ConnectionManager removed - now using enhanced_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ProScrape API...")
    await async_db.connect()
    
    # Initialize translation manager
    try:
        await translation_manager.initialize()
        logger.info("Translation manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize translation manager: {e}")
    
    # Start enhanced WebSocket manager
    try:
        await enhanced_manager.start()
        logger.info("Enhanced WebSocket manager started")
    except Exception as e:
        logger.error(f"Failed to start WebSocket manager: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ProScrape API...")
    
    # Stop WebSocket manager
    try:
        await enhanced_manager.stop()
        logger.info("Enhanced WebSocket manager stopped")
    except Exception as e:
        logger.error(f"Error stopping WebSocket manager: {e}")
    
    await async_db.disconnect()


app = FastAPI(
    title="ProScrape API",
    description="API for accessing scraped real estate data from Latvian websites",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Docker and frontend integration
cors_origins = ["*"]  # Allow all origins for development
cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
cors_headers = ["*"]

# Use docker settings if available, otherwise use defaults
if hasattr(docker_settings, 'cors_origins'):
    cors_origins = docker_settings.cors_origins.split(',') if isinstance(docker_settings.cors_origins, str) else docker_settings.cors_origins
if hasattr(docker_settings, 'cors_allow_methods'):
    cors_methods = docker_settings.cors_allow_methods.split(',') if isinstance(docker_settings.cors_allow_methods, str) else docker_settings.cors_allow_methods
if hasattr(docker_settings, 'cors_allow_headers'):
    cors_headers = docker_settings.cors_allow_headers.split(',') if isinstance(docker_settings.cors_allow_headers, str) else docker_settings.cors_allow_headers

# Add i18n middleware first (will be processed first)
app.add_middleware(
    I18nMiddleware,
    default_language=getattr(settings, 'default_language', 'lv')
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=getattr(docker_settings, 'cors_allow_credentials', True),
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)


@app.get("/")
async def root():
    """Root endpoint with i18n support."""
    language = get_current_language()
    
    return {
        "message": t("api.messages.welcome", fallback="Welcome to ProScrape API"),
        "version": "1.0.0",
        "docs": "/docs",
        "language": language,
        "supported_languages": [lang.value for lang in SupportedLanguage],
        "i18n": {
            "current_language": language,
            "language_name": t(f"languages.{language}", fallback=language.upper()),
            "switch_language_info": {
                "query_param": "lang",
                "header": "X-Language",
                "cookie": "proscrape_lang"
            }
        }
    }


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint for Docker services with i18n support."""
    try:
        current_lang = get_current_language()
        
        # Test database connection
        await async_db.client.admin.command('ping')
        
        # Check all services
        services = {
            "mongodb": check_mongodb(),
            "redis": check_redis(),
            "celery": check_celery_workers()
        }
        
        # Determine overall health
        unhealthy_services = [name for name, status in services.items() if status["status"] != "healthy"]
        overall_status = "healthy" if not unhealthy_services else "degraded"
        
        # Get i18n health
        i18n_health = translation_manager.health_check()
        
        return {
            "status": overall_status,
            "message": t("api.health.status_message", fallback="System health check completed"),
            "timestamp": datetime.utcnow(),
            "language": current_lang,
            "services": services,
            "i18n": {
                "status": i18n_health.get("status", "unknown"),
                "supported_languages": [lang.value for lang in SupportedLanguage],
                "current_language": current_lang,
                "translation_stats": translation_manager.get_statistics(),
                "middleware_active": True
            },
            "docker_enabled": True,
            "cors_origins": cors_origins[:3]  # Show first 3 for security
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_message = t("api.errors.service_unavailable", fallback="Service unavailable")
        raise HTTPException(status_code=503, detail=error_message)


@app.get("/listings", response_model=PaginatedListingResponse)
async def get_listings(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(20, ge=1, le=1000, description="Number of listings per page"),
    city: Optional[str] = Query(None, description="Filter by city"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    listing_type: Optional[str] = Query(None, description="Filter by listing type (sell, rent)"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum area in sqm"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum area in sqm"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    date_from: Optional[datetime] = Query(None, description="Filter listings scraped after this date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter listings scraped before this date (ISO format)"),
    posted_from: Optional[datetime] = Query(None, description="Filter listings posted after this date (ISO format)"),
    posted_to: Optional[datetime] = Query(None, description="Filter listings posted before this date (ISO format)"),
    # Map bounds parameters
    north: Optional[float] = Query(None, description="Northern boundary latitude"),
    south: Optional[float] = Query(None, description="Southern boundary latitude"),
    east: Optional[float] = Query(None, description="Eastern boundary longitude"),
    west: Optional[float] = Query(None, description="Western boundary longitude"),
    has_coordinates: Optional[bool] = Query(None, description="Filter listings with valid coordinates"),
    sort_by: str = Query("scraped_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """Get listings with filtering and pagination."""
    try:
        collection = async_db.get_collection("listings")
        
        # Build filter query
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
        
        # Date filtering for scraped_at
        if date_from is not None or date_to is not None:
            scraped_filter = {}
            if date_from is not None:
                scraped_filter["$gte"] = date_from
            if date_to is not None:
                scraped_filter["$lte"] = date_to
            filter_query["scraped_at"] = scraped_filter
        
        # Date filtering for posted_date
        if posted_from is not None or posted_to is not None:
            posted_filter = {}
            if posted_from is not None:
                posted_filter["$gte"] = posted_from
            if posted_to is not None:
                posted_filter["$lte"] = posted_to
            filter_query["posted_date"] = posted_filter
        
        # Map bounds filtering - coordinates are stored as separate latitude/longitude fields
        if north is not None and south is not None and east is not None and west is not None:
            filter_query["latitude"] = {"$gte": south, "$lte": north}
            filter_query["longitude"] = {"$gte": west, "$lte": east}
        
        # Filter listings with coordinates if requested
        if has_coordinates is not None:
            if has_coordinates:
                filter_query["latitude"] = {"$exists": True, "$ne": None}
                filter_query["longitude"] = {"$exists": True, "$ne": None}
            else:
                filter_query["$or"] = [
                    {"latitude": {"$exists": False}},
                    {"latitude": None},
                    {"longitude": {"$exists": False}},
                    {"longitude": None}
                ]
        
        # Build sort order
        sort_direction = 1 if sort_order == "asc" else -1
        
        # Calculate offset from page
        offset = (page - 1) * limit
        
        # Get total count for pagination
        total_count = await collection.count_documents(filter_query)
        
        # Execute query
        cursor = collection.find(filter_query)
        cursor = cursor.sort(sort_by, sort_direction)
        cursor = cursor.skip(offset).limit(limit)
        
        listings = await cursor.to_list(length=limit)
        
        # Convert to response models
        response_listings = []
        for listing_data in listings:
            listing_data["id"] = str(listing_data["_id"])
            response_listings.append(ListingResponse(**listing_data))
        
        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        return PaginatedListingResponse(
            items=response_listings,
            total=total_count,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        logger.error(f"Error fetching listings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: str):
    """Get a specific listing by ID."""
    try:
        collection = async_db.get_collection("listings")
        
        from bson import ObjectId
        if ObjectId.is_valid(listing_id):
            # Search by MongoDB ObjectId
            listing_data = await collection.find_one({"_id": ObjectId(listing_id)})
        else:
            # Search by listing_id field
            listing_data = await collection.find_one({"listing_id": listing_id})
        
        if not listing_data:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        listing_data["id"] = str(listing_data["_id"])
        return ListingResponse(**listing_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listing {listing_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/listings/search", response_model=List[ListingResponse])
async def search_listings(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Search listings by text."""
    try:
        collection = async_db.get_collection("listings")
        
        # Text search query
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
        
        response_listings = []
        for listing_data in listings:
            listing_data["id"] = str(listing_data["_id"])
            response_listings.append(ListingResponse(**listing_data))
        
        return response_listings
        
    except Exception as e:
        logger.error(f"Error searching listings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/stats")
async def get_statistics():
    """Get database statistics."""
    try:
        collection = async_db.get_collection("listings")
        
        # Total count
        total_count = await collection.count_documents({})
        
        # Count by source site
        source_stats = await collection.aggregate([
            {"$group": {"_id": "$source_site", "count": {"$sum": 1}}}
        ]).to_list(length=None)
        
        # Count by property type
        property_type_stats = await collection.aggregate([
            {"$group": {"_id": "$property_type", "count": {"$sum": 1}}}
        ]).to_list(length=None)
        
        # Count by listing type
        listing_type_stats = await collection.aggregate([
            {"$group": {"_id": "$listing_type", "count": {"$sum": 1}}}
        ]).to_list(length=None)
        
        # Count by city (top 10)
        city_stats = await collection.aggregate([
            {"$group": {"_id": "$city", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]).to_list(length=None)
        
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
        
        return {
            "total_listings": total_count,
            "by_source": {item["_id"]: item["count"] for item in source_stats},
            "by_property_type": {item["_id"]: item["count"] for item in property_type_stats},
            "by_listing_type": {item["_id"]: item["count"] for item in listing_type_stats},
            "top_cities": {item["_id"]: item["count"] for item in city_stats},
            "price_stats": price_stats[0] if price_stats else None
        }
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/export/csv")
async def export_listings_csv(
    city: Optional[str] = Query(None, description="Filter by city"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    listing_type: Optional[str] = Query(None, description="Filter by listing type (sell, rent)"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum area in sqm"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum area in sqm"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    date_from: Optional[datetime] = Query(None, description="Filter listings scraped after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter listings scraped before this date"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of listings to export")
):
    """Export listings to CSV format."""
    try:
        collection = async_db.get_collection("listings")
        
        # Build filter query (reuse logic from get_listings)
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
        
        # Get listings
        cursor = collection.find(filter_query).sort("scraped_at", -1).limit(limit)
        listings = await cursor.to_list(length=limit)
        
        # Create CSV content
        output = io.StringIO()
        if listings:
            fieldnames = ['listing_id', 'title', 'price', 'area_sqm', 'property_type', 'listing_type',
                         'city', 'district', 'address', 'source_site', 'url', 'scraped_at', 'posted_date']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for listing in listings:
                row = {field: listing.get(field, '') for field in fieldnames}
                # Convert datetime objects to strings
                if row['scraped_at']:
                    row['scraped_at'] = row['scraped_at'].isoformat() if isinstance(row['scraped_at'], datetime) else str(row['scraped_at'])
                if row['posted_date']:
                    row['posted_date'] = row['posted_date'].isoformat() if isinstance(row['posted_date'], datetime) else str(row['posted_date'])
                writer.writerow(row)
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=listings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting listings to CSV: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/export/json")
async def export_listings_json(
    city: Optional[str] = Query(None, description="Filter by city"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    listing_type: Optional[str] = Query(None, description="Filter by listing type (sell, rent)"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum area in sqm"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum area in sqm"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    date_from: Optional[datetime] = Query(None, description="Filter listings scraped after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter listings scraped before this date"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of listings to export")
):
    """Export listings to JSON format."""
    try:
        collection = async_db.get_collection("listings")
        
        # Build filter query (same as CSV export)
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
        
        # Get listings
        cursor = collection.find(filter_query).sort("scraped_at", -1).limit(limit)
        listings = await cursor.to_list(length=limit)
        
        # Convert to JSON-serializable format
        json_listings = []
        for listing in listings:
            listing["id"] = str(listing["_id"])
            del listing["_id"]
            # Convert datetime objects to ISO strings
            for field in ['scraped_at', 'posted_date']:
                if field in listing and listing[field]:
                    if isinstance(listing[field], datetime):
                        listing[field] = listing[field].isoformat()
            json_listings.append(listing)
        
        json_content = json.dumps({
            "export_date": datetime.now().isoformat(),
            "total_listings": len(json_listings),
            "filters_applied": {
                "city": city,
                "property_type": property_type,
                "listing_type": listing_type,
                "min_price": min_price,
                "max_price": max_price,
                "min_area": min_area,
                "max_area": max_area,
                "source_site": source_site,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None
            },
            "listings": json_listings
        }, indent=2)
        
        return StreamingResponse(
            io.BytesIO(json_content.encode('utf-8')),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=listings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting listings to JSON: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint for real-time updates with improved stability."""
    connection_id = None
    
    try:
        # Connect using enhanced manager
        connection_id = await enhanced_manager.connect(websocket)
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                
                # Handle the message using enhanced manager
                await enhanced_manager.handle_client_message(connection_id, data)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket message loop for {connection_id}: {e}")
                # Send error message to client if connection is still active
                try:
                    await enhanced_manager.send_personal_message(connection_id, {
                        "type": "error",
                        "message": "Internal server error",
                        "error_details": str(e) if logger.level <= logging.DEBUG else None
                    })
                except:
                    break  # Connection is broken, exit loop
                
    except Exception as e:
        logger.error(f"Error in WebSocket endpoint: {e}")
    finally:
        # Clean up connection
        if connection_id:
            await enhanced_manager.disconnect(connection_id, "client_disconnect")


async def broadcast_new_listing(listing_data: dict):
    """Function to broadcast new listings to all connected WebSocket clients."""
    message = {
        "type": "new_listing",
        "data": listing_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # Use enhanced manager for broadcasting
    sent_count = await enhanced_manager.broadcast_message(message)
    logger.info(f"Broadcast new listing to {sent_count} connections")


@app.get("/proxy/stats")
async def get_proxy_statistics():
    """Get proxy rotation statistics and health information."""
    try:
        if not proxy_rotator.proxy_list:
            return {
                "message": "No proxies configured",
                "proxy_rotation_enabled": settings.rotate_proxies,
                "proxy_count": 0
            }
        
        stats = proxy_rotator.get_proxy_statistics()
        stats["proxy_rotation_enabled"] = settings.rotate_proxies
        stats["health_check_interval"] = settings.proxy_health_check_interval
        stats["max_retries"] = settings.max_proxy_retries
        
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching proxy statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/monitoring/dead-letter-queue")
async def get_dead_letter_queue_stats():
    """Get dead letter queue statistics and failed requests."""
    try:
        from spiders.middlewares import retry_middleware_instance
        
        if not retry_middleware_instance:
            return {
                "message": "Retry middleware not initialized",
                "stats": {"total": 0, "by_reason": {}, "by_spider": {}, "items": []}
            }
        
        stats = retry_middleware_instance.get_dead_letter_stats()
        return {
            "message": "Dead letter queue statistics",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error fetching dead letter queue stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/monitoring/alerts")
async def get_recent_alerts(limit: int = Query(50, ge=1, le=200)):
    """Get recent alerts and alert summary."""
    try:
        alerts = alert_manager.get_recent_alerts(limit)
        summary = alert_manager.get_alert_summary()
        
        return {
            "alerts": alerts,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/monitoring/check-alerts")
async def trigger_alert_check():
    """Manually trigger alert checking."""
    try:
        alert_manager.check_and_send_alerts()
        return {"message": "Alert check completed"}
        
    except Exception as e:
        logger.error(f"Error running alert check: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/monitoring/health")
async def get_system_health():
    """Get comprehensive system health information."""
    try:
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "database": "unknown",
            "proxy_health": {},
            "dead_letter_queue": {},
            "alerts": {},
            "websocket": {}
        }
        
        # Database health
        try:
            await async_db.client.admin.command('ping')
            health_data["database"] = "healthy"
        except Exception as e:
            health_data["database"] = f"unhealthy: {str(e)}"
        
        # Proxy health (if configured)
        if proxy_rotator.proxy_list:
            health_data["proxy_health"] = proxy_rotator.get_proxy_statistics()
        else:
            health_data["proxy_health"] = {"message": "No proxies configured"}
        
        # Dead letter queue health
        try:
            from spiders.middlewares import retry_middleware_instance
            if retry_middleware_instance:
                health_data["dead_letter_queue"] = retry_middleware_instance.get_dead_letter_stats()
            else:
                health_data["dead_letter_queue"] = {"message": "Retry middleware not initialized"}
        except Exception as e:
            health_data["dead_letter_queue"] = {"error": str(e)}
        
        # Alert summary
        health_data["alerts"] = alert_manager.get_alert_summary()
        
        # WebSocket health
        health_data["websocket"] = enhanced_manager.get_statistics()
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/monitoring/websocket/stats")
async def get_websocket_statistics():
    """Get detailed WebSocket connection statistics."""
    try:
        return enhanced_manager.get_statistics()
    except Exception as e:
        logger.error(f"Error fetching WebSocket statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/monitoring/websocket/connections")
async def get_websocket_connections():
    """Get information about all active WebSocket connections."""
    try:
        return enhanced_manager.get_all_connections()
    except Exception as e:
        logger.error(f"Error fetching WebSocket connections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/monitoring/websocket/broadcast")
async def test_websocket_broadcast(
    message: str = Query(..., description="Test message to broadcast"),
    message_type: str = Query("test", description="Message type")
):
    """Test endpoint to broadcast a message to all connected WebSocket clients."""
    try:
        test_message = {
            "type": message_type,
            "message": message,
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
        
        sent_count = await enhanced_manager.broadcast_message(test_message)
        
        return {
            "message": "Broadcast sent",
            "recipients": sent_count,
            "sent_message": test_message
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting test message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===== I18N-SPECIFIC ENDPOINTS =====

@app.get("/api/i18n/languages", response_model=List[LanguageInfo])
async def get_supported_languages():
    """Get list of supported languages with metadata."""
    try:
        current_lang = get_current_language()
        languages = []
        
        for lang in SupportedLanguage:
            lang_code = lang.value
            
            # Get language names in different locales
            lang_info = LanguageInfo(
                code=lang_code,
                name=t(f"languages.{lang_code}", fallback=lang_code.upper()),
                name_en=t(f"languages.{lang_code}", language="en", fallback=lang_code.upper()),
                name_local=t(f"languages.{lang_code}", language=lang_code, fallback=lang_code.upper()),
                is_default=lang_code == settings.default_language,
                is_current=lang_code == current_lang,
                switch_url=f"/api/i18n/switch?lang={lang_code}"
            )
            
            languages.append(lang_info)
        
        return languages
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/i18n/switch")
async def switch_language(
    language: str = Query(..., description="Language code to switch to"),
    redirect_url: Optional[str] = Query(None, description="URL to redirect to after switching")
):
    """Switch language and optionally redirect."""
    try:
        # Validate language
        if language not in [lang.value for lang in SupportedLanguage]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {language}. Supported: {[lang.value for lang in SupportedLanguage]}"
            )
        
        # Create response
        response_data = {
            "message": t("api.messages.language_switched", 
                        language=language,
                        fallback=f"Language switched to {language}"),
            "language": language,
            "previous_language": get_current_language(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Create JSON response
        response = JSONResponse(content=response_data)
        
        # Set language cookie
        response.set_cookie(
            key="proscrape_lang",
            value=language,
            max_age=30 * 24 * 3600,  # 30 days
            httponly=True,
            samesite="lax"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching language: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/i18n/translations")
async def get_translations(
    namespace: Optional[str] = Query(None, description="Translation namespace (e.g., 'api', 'properties')"),
    language: Optional[str] = Query(None, description="Language code (defaults to current)")
):
    """Get translations for current or specified language."""
    try:
        target_language = language or get_current_language()
        
        if target_language not in [lang.value for lang in SupportedLanguage]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {target_language}"
            )
        
        # Get all translations for the language
        all_translations = translation_manager.get_translations(target_language)
        
        # Filter by namespace if specified
        if namespace:
            filtered_translations = {
                key: value for key, value in all_translations.items()
                if key.startswith(f"{namespace}.")
            }
        else:
            filtered_translations = all_translations
        
        return {
            "language": target_language,
            "namespace": namespace,
            "translations": filtered_translations,
            "count": len(filtered_translations),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting translations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/i18n/health")
async def i18n_health_check():
    """Health check for i18n system."""
    try:
        health_data = translation_manager.health_check()
        
        # Add additional health metrics
        health_data.update({
            "current_language": get_current_language(),
            "supported_languages": [lang.value for lang in SupportedLanguage],
            "middleware_active": True,
            "translation_cache_stats": translation_manager.cache.get_stats()
        })
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error in i18n health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ===== LOCALIZED VERSIONS OF EXISTING ENDPOINTS =====

@app.get("/api/v1/listings", response_model=LocalizedPaginatedListingResponse)
async def get_localized_listings(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(20, ge=1, le=1000, description="Number of listings per page"),
    city: Optional[str] = Query(None, description="Filter by city"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    listing_type: Optional[str] = Query(None, description="Filter by listing type (sell, rent)"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum area in sqm"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum area in sqm"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    date_from: Optional[datetime] = Query(None, description="Filter scraped after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter scraped before this date"),
    posted_from: Optional[datetime] = Query(None, description="Filter posted after this date"),
    posted_to: Optional[datetime] = Query(None, description="Filter posted before this date"),
    north: Optional[float] = Query(None, description="Northern boundary latitude"),
    south: Optional[float] = Query(None, description="Southern boundary latitude"),
    east: Optional[float] = Query(None, description="Eastern boundary longitude"),
    west: Optional[float] = Query(None, description="Western boundary longitude"),
    has_coordinates: Optional[bool] = Query(None, description="Filter listings with coordinates"),
    sort_by: str = Query("scraped_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """Get localized listings with filtering and pagination."""
    try:
        # Get standard listings using existing logic
        standard_response = await get_listings(
            page=page, limit=limit, city=city, property_type=property_type,
            listing_type=listing_type, min_price=min_price, max_price=max_price,
            min_area=min_area, max_area=max_area, source_site=source_site,
            date_from=date_from, date_to=date_to, posted_from=posted_from,
            posted_to=posted_to, north=north, south=south, east=east, west=west,
            has_coordinates=has_coordinates, sort_by=sort_by, sort_order=sort_order
        )
        
        # Convert to localized response
        localized_items = [
            LocalizedListingResponse(**item.model_dump()) 
            for item in standard_response.items
        ]
        
        return LocalizedPaginatedListingResponse(
            items=localized_items,
            total=standard_response.total,
            page=standard_response.page,
            limit=standard_response.limit,
            total_pages=standard_response.total_pages,
            has_next=standard_response.has_next,
            has_prev=standard_response.has_prev
        )
        
    except Exception as e:
        logger.error(f"Error fetching localized listings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/listings/{listing_id}", response_model=LocalizedListingResponse)
async def get_localized_listing(listing_id: str):
    """Get a localized listing by ID."""
    try:
        # Get standard listing
        standard_listing = await get_listing(listing_id)
        
        # Convert to localized response
        return LocalizedListingResponse(**standard_listing.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching localized listing {listing_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/stats", response_model=LocalizedStatisticsResponse)
async def get_localized_statistics():
    """Get localized database statistics."""
    try:
        # Get standard statistics
        standard_stats = await get_statistics()
        
        # Convert to localized response
        return LocalizedStatisticsResponse(
            total_listings=standard_stats["total_listings"],
            by_source=standard_stats["by_source"],
            by_property_type=standard_stats["by_property_type"],
            by_listing_type=standard_stats["by_listing_type"],
            top_cities=standard_stats["top_cities"],
            price_stats=standard_stats["price_stats"]
        )
        
    except Exception as e:
        logger.error(f"Error fetching localized statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/export/csv")
async def export_localized_listings_csv(
    city: Optional[str] = Query(None, description="Filter by city"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    listing_type: Optional[str] = Query(None, description="Filter by listing type"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum area"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum area"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    date_from: Optional[datetime] = Query(None, description="Filter scraped after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter scraped before this date"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of listings")
):
    """Export localized listings to CSV format."""
    try:
        current_lang = get_current_language()
        collection = async_db.get_collection("listings")
        
        # Build filter query (reuse existing logic)
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
        
        # Get listings
        cursor = collection.find(filter_query).sort("scraped_at", -1).limit(limit)
        listings = await cursor.to_list(length=limit)
        
        # Create localized CSV content
        output = io.StringIO()
        if listings:
            # Localized column headers
            fieldnames = [
                'listing_id', 'title', 'price', 'price_formatted', 'area_sqm', 'area_formatted',
                'property_type', 'property_type_localized', 'listing_type', 'listing_type_localized',
                'city', 'district', 'address', 'source_site', 'url', 'scraped_at', 'posted_date'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            
            # Write localized headers
            header_row = {}
            for field in fieldnames:
                header_key = f"api.fields.{field}"
                header_row[field] = t(header_key, fallback=field.replace('_', ' ').title())
            writer.writerow(header_row)
            
            # Write data rows with localization
            from utils.i18n import LocalizedFormatter
            formatter = LocalizedFormatter(current_lang)
            
            for listing in listings:
                # Apply localized formatting
                formatted_listing = formatter.format_listing_data(listing)
                
                row = {field: formatted_listing.get(field, '') for field in fieldnames}
                
                # Add localized versions
                if listing.get('property_type'):
                    row['property_type_localized'] = t(
                        f"properties.types.{listing['property_type'].lower()}",
                        fallback=listing['property_type'].title()
                    )
                if listing.get('listing_type'):
                    row['listing_type_localized'] = t(
                        f"properties.listing_types.{listing['listing_type'].lower()}",
                        fallback=listing['listing_type'].title()
                    )
                
                # Convert datetime objects to strings
                for date_field in ['scraped_at', 'posted_date']:
                    if row.get(date_field):
                        if isinstance(row[date_field], datetime):
                            row[date_field] = row[date_field].isoformat()
                        else:
                            row[date_field] = str(row[date_field])
                
                writer.writerow(row)
        
        output.seek(0)
        
        # Create filename with language code
        filename = f"listings_export_{current_lang}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting localized CSV: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=docker_settings.api_host,
        port=docker_settings.api_port,
        reload=docker_settings.enable_auto_reload,
        log_level="debug" if docker_settings.enable_debug_logs else "info"
    )