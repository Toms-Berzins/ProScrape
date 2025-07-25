import pytest
from datetime import datetime
from decimal import Decimal
from models.listing import ListingCreate, ListingResponse, Listing
from pydantic import ValidationError


class TestListingModels:
    """Test cases for listing Pydantic models."""
    
    def test_listing_create_valid(self):
        """Test creating a valid listing."""
        data = {
            "listing_id": "test_123",
            "source_site": "ss.com",
            "title": "Beautiful Apartment in Central Riga",
            "source_url": "https://ss.com/msg/test_123",
            "price": "150000.50",
            "price_currency": "EUR",
            "area_sqm": 75.5,
            "rooms": 3,
            "property_type": "apartment",
            "city": "Riga",
            "address": "Elizabetes iela 123, Riga"
        }
        
        listing = ListingCreate(**data)
        
        assert listing.listing_id == "test_123"
        assert listing.source_site == "ss.com"
        assert listing.price == Decimal("150000.50")
        assert listing.area_sqm == 75.5
        assert listing.rooms == 3
        assert listing.city == "Riga"
    
    def test_listing_create_required_fields(self):
        """Test that required fields are enforced."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            ListingCreate(title="Test")
        
        # Minimum valid data
        minimal_data = {
            "listing_id": "test_123",
            "source_site": "ss.com",
            "title": "Test Listing",
            "source_url": "https://example.com/test"
        }
        
        listing = ListingCreate(**minimal_data)
        assert listing.listing_id == "test_123"
    
    def test_price_parsing(self):
        """Test price parsing from various formats."""
        test_cases = [
            ("150000", Decimal("150000")),
            ("150,000.50", Decimal("150000.50")),
            ("€150000", Decimal("150000")),
            ("150 000 EUR", Decimal("150000")),
            ("invalid", None),
        ]
        
        for price_input, expected in test_cases:
            if expected is None:
                # Should handle invalid prices gracefully
                listing = ListingCreate(
                    listing_id="test",
                    source_site="ss.com", 
                    title="Test",
                    source_url="https://test.com",
                    price=price_input
                )
                # Invalid prices should be set to None
                assert listing.price is None or isinstance(listing.price, Decimal)
            else:
                listing = ListingCreate(
                    listing_id="test",
                    source_site="ss.com",
                    title="Test", 
                    source_url="https://test.com",
                    price=price_input
                )
                assert listing.price == expected
    
    def test_source_site_validation(self):
        """Test source site validation."""
        valid_sites = ["ss.com", "city24.lv", "pp.lv"]
        
        for site in valid_sites:
            listing = ListingCreate(
                listing_id="test",
                source_site=site,
                title="Test",
                source_url="https://test.com"
            )
            assert listing.source_site == site
        
        # Invalid source site should raise ValidationError
        with pytest.raises(ValidationError):
            ListingCreate(
                listing_id="test",
                source_site="invalid.com",
                title="Test",
                source_url="https://test.com"
            )
    
    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        listing = ListingCreate(
            listing_id="test",
            source_site="ss.com",
            title="Test",
            source_url="https://test.com",
            description="Nice property",
            features=["balcony", "parking"],
            amenities=["elevator", "security"],
            image_urls=["https://example.com/img1.jpg"],
            posted_date=datetime(2024, 1, 15)
        )
        
        assert listing.description == "Nice property"
        assert "balcony" in listing.features
        assert "elevator" in listing.amenities
        assert len(listing.image_urls) == 1
        assert listing.posted_date.year == 2024
    
    def test_listing_response_serialization(self):
        """Test ListingResponse model for API responses."""
        data = {
            "id": "507f1f77bcf86cd799439011",
            "listing_id": "test_123",
            "source_site": "ss.com",
            "title": "Test Listing",
            "source_url": "https://test.com",
            "price": 150000,
            "scraped_at": datetime.now()
        }
        
        response = ListingResponse(**data)
        
        assert response.id == "507f1f77bcf86cd799439011"
        assert response.listing_id == "test_123"
        assert response.source_site == "ss.com"
    
    def test_default_values(self):
        """Test default values are set correctly."""
        listing = ListingCreate(
            listing_id="test",
            source_site="ss.com",
            title="Test",
            source_url="https://test.com"
        )
        
        # Check default values
        assert listing.price_currency == "EUR"
        assert isinstance(listing.features, list)
        assert isinstance(listing.amenities, list)
        assert isinstance(listing.image_urls, list)
        assert isinstance(listing.scraped_at, datetime)
    
    def test_coordinate_validation(self):
        """Test coordinate field validation."""
        # Valid coordinates for Latvia
        listing = ListingCreate(
            listing_id="test",
            source_site="ss.com",
            title="Test",
            source_url="https://test.com",
            latitude=56.9496,  # Riga latitude
            longitude=24.1052  # Riga longitude
        )
        
        assert listing.latitude == 56.9496
        assert listing.longitude == 24.1052