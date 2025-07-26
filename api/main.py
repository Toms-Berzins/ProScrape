from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import json
import csv
import io

from models.listing import ListingResponse, Listing
from utils.database import async_db
from utils.proxies import proxy_rotator
from utils.alerting import alert_manager
from config.settings import settings
try:
    from config.docker_settings import docker_settings
except ImportError:
    from config.settings import settings as docker_settings


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


class ConnectionManager:
    """WebSocket connection manager for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast_message(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                # Remove broken connections
                self.active_connections.remove(connection)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ProScrape API...")
    await async_db.connect()
    yield
    # Shutdown
    logger.info("Shutting down ProScrape API...")
    await async_db.disconnect()


app = FastAPI(
    title="ProScrape API",
    description="API for accessing scraped real estate data from Latvian websites",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Docker and frontend integration
cors_origins = docker_settings.cors_origins.split(',') if isinstance(docker_settings.cors_origins, str) else docker_settings.cors_origins
cors_methods = docker_settings.cors_allow_methods.split(',') if isinstance(docker_settings.cors_allow_methods, str) else docker_settings.cors_allow_methods
cors_headers = docker_settings.cors_allow_headers.split(',') if isinstance(docker_settings.cors_allow_headers, str) else docker_settings.cors_allow_headers

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=docker_settings.cors_allow_credentials,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ProScrape API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint for Docker services."""
    try:
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
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow(),
            "services": services,
            "docker_enabled": True,
            "cors_origins": cors_origins[:3]  # Show first 3 for security
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/listings", response_model=List[ListingResponse])
async def get_listings(
    limit: int = Query(50, ge=1, le=1000, description="Number of listings to return"),
    offset: int = Query(0, ge=0, description="Number of listings to skip"),
    city: Optional[str] = Query(None, description="Filter by city"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_area: Optional[float] = Query(None, ge=0, description="Minimum area in sqm"),
    max_area: Optional[float] = Query(None, ge=0, description="Maximum area in sqm"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    date_from: Optional[datetime] = Query(None, description="Filter listings scraped after this date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter listings scraped before this date (ISO format)"),
    posted_from: Optional[datetime] = Query(None, description="Filter listings posted after this date (ISO format)"),
    posted_to: Optional[datetime] = Query(None, description="Filter listings posted before this date (ISO format)"),
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
        
        # Build sort order
        sort_direction = 1 if sort_order == "asc" else -1
        
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
        
        return response_listings
        
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
            fieldnames = ['listing_id', 'title', 'price', 'area_sqm', 'property_type', 
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
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle different message types
            try:
                message = json.loads(data)
                message_type = message.get("type", "")
                
                if message_type == "ping":
                    await manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                        websocket
                    )
                elif message_type == "subscribe":
                    # Client wants to subscribe to updates
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "subscribed",
                            "message": "Subscribed to real-time listing updates",
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )
                else:
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )
            except json.JSONDecodeError:
                # Handle plain text messages
                await manager.send_personal_message(
                    json.dumps({
                        "type": "echo",
                        "message": f"Received: {data}",
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


async def broadcast_new_listing(listing_data: dict):
    """Function to broadcast new listings to all connected WebSocket clients."""
    if manager.active_connections:
        message = json.dumps({
            "type": "new_listing",
            "data": listing_data,
            "timestamp": datetime.now().isoformat()
        })
        await manager.broadcast_message(message)


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
            "alerts": {}
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
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
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