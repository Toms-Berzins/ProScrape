from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId for MongoDB integration with Pydantic."""
    
    @classmethod
    def __get_pydantic_json_schema__(cls, _source_type, _handler):
        return {"type": "string"}
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class ListingBase(BaseModel):
    """Base model for real estate listings."""
    
    listing_id: str = Field(..., description="Unique identifier from source site")
    source_site: str = Field(..., description="Source website (ss.com, city24.lv, pp.lv)")
    title: str = Field(..., description="Property title")
    description: Optional[str] = Field(None, description="Property description")
    
    # Price information
    price: Optional[Decimal] = Field(None, description="Price in EUR")
    price_currency: str = Field("EUR", description="Price currency")
    price_per_sqm: Optional[Decimal] = Field(None, description="Price per square meter")
    
    # Property details
    property_type: Optional[str] = Field(None, description="Type of property (apartment, house, land)")
    listing_type: Optional[str] = Field(None, description="Listing type (sell, rent)")
    area_sqm: Optional[float] = Field(None, description="Area in square meters")
    rooms: Optional[int] = Field(None, description="Number of rooms")
    floor: Optional[int] = Field(None, description="Floor number")
    total_floors: Optional[int] = Field(None, description="Total floors in building")
    
    # Location
    address: Optional[str] = Field(None, description="Property address")
    city: Optional[str] = Field(None, description="City")
    district: Optional[str] = Field(None, description="District/neighborhood")
    postal_code: Optional[str] = Field(None, description="Postal code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    
    # Additional features
    features: List[str] = Field(default_factory=list, description="Property features")
    amenities: List[str] = Field(default_factory=list, description="Available amenities")
    
    # Media
    image_urls: List[str] = Field(default_factory=list, description="Property image URLs")
    video_urls: List[str] = Field(default_factory=list, description="Property video URLs")
    
    # Metadata
    posted_date: Optional[datetime] = Field(None, description="Date when listing was posted")
    updated_date: Optional[datetime] = Field(None, description="Last update date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")
    source_url: str = Field(..., description="Original listing URL")
    
    # Additional data from source
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw data from source")
    
    @field_validator('price', 'price_per_sqm', mode='before')
    @classmethod
    def parse_price(cls, v):
        """Parse price values to Decimal for precision."""
        if v is None:
            return v
        if isinstance(v, str):
            # Remove currency symbols and spaces
            v = v.replace('€', '').replace('EUR', '').replace(',', '').replace(' ', '')
            try:
                return Decimal(v)
            except:
                return None
        return Decimal(str(v))
    
    @field_validator('source_site')
    @classmethod
    def validate_source_site(cls, v):
        """Validate source site is one of the supported sites."""
        allowed_sites = {'ss.com', 'city24.lv', 'pp.lv'}
        if v not in allowed_sites:
            raise ValueError(f'Source site must be one of {allowed_sites}')
        return v
    
    @field_validator('listing_type')
    @classmethod
    def validate_listing_type(cls, v):
        """Validate listing type is either sell or rent."""
        if v is None:
            return v
        allowed_types = {'sell', 'rent'}
        if v.lower() not in allowed_types:
            raise ValueError(f'Listing type must be one of {allowed_types}')
        return v.lower()
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Listing(ListingBase):
    """Full listing model with MongoDB ObjectId."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ListingCreate(ListingBase):
    """Model for creating new listings."""
    pass


class ListingUpdate(BaseModel):
    """Model for updating existing listings."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    price_currency: Optional[str] = None
    listing_type: Optional[str] = None
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    features: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    updated_date: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True


class ListingResponse(ListingBase):
    """Model for API responses."""
    
    id: str
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class PaginatedListingResponse(BaseModel):
    """Paginated response for listings API."""
    
    items: List[ListingResponse]
    total: int = Field(..., description="Total number of items matching the query")
    page: int = Field(..., description="Current page number (1-based)")
    limit: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
    
    class Config:
        populate_by_name = True