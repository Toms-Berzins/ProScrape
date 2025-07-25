from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from models.listing import ListingResponse, Listing
from utils.database import async_db
from config.settings import settings

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Health check endpoint."""
    try:
        # Test database connection
        await async_db.client.admin.command('ping')
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "database": "connected"
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )