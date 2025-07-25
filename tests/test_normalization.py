import pytest
from datetime import datetime
from utils.normalization import DataNormalizer, normalize_listing_data


class TestDataNormalizationUtilities:
    """Test cases for data normalization utilities."""
    
    def test_normalize_price(self):
        """Test price normalization from various formats."""
        test_cases = [
            ("150000", "EUR", {"price": 150000.0, "currency": "EUR"}),
            ("€150,000.50", "EUR", {"price": 150000.5, "currency": "EUR"}),
            ("150 000 EUR", "EUR", {"price": 150000.0, "currency": "EUR"}),
            ("$100000", "USD", {"price": 85000.0, "currency": "EUR"}),  # USD to EUR conversion
            ("invalid", "EUR", None),
            ("", "EUR", None),
        ]
        
        for price_text, currency, expected in test_cases:
            result = DataNormalizer.normalize_price(price_text, currency)
            
            if expected is None:
                assert result is None
            else:
                assert result is not None
                assert result["price"] == expected["price"]
                assert result["currency"] == expected["currency"]
    
    def test_normalize_area(self):
        """Test area normalization from various formats."""
        test_cases = [
            ("75.5 m²", {"area_sqm": 75.5}),
            ("75.5 m2", {"area_sqm": 75.5}),
            ("75.5 sqm", {"area_sqm": 75.5}),
            ("1 ha", {"area_sqm": 10000.0}),
            ("2 acres", {"area_sqm": 8093.72}),
            ("75", {"area_sqm": 75.0}),  # Assume m² if no unit
            ("invalid", None),
            ("", None),
        ]
        
        for area_text, expected in test_cases:
            result = DataNormalizer.normalize_area(area_text)
            
            if expected is None:
                assert result is None
            else:
                assert result is not None
                assert result["area_sqm"] == expected["area_sqm"]
    
    def test_normalize_address(self):
        """Test address normalization and component extraction."""
        test_cases = [
            (
                "Elizabetes iela 123, Rīga, LV-1050",
                {
                    "full_address": "Elizabetes iela 123, Rīga, LV-1050",
                    "city": "Riga",
                    "postal_code": "LV-1050"
                }
            ),
            (
                "Jūrmalas iela 45, Jūrmala",
                {
                    "full_address": "Jūrmalas iela 45, Jūrmala", 
                    "city": "Jurmala"
                }
            ),
            (
                "Liepāja, Graudu iela 12",
                {
                    "city": "Liepaja"
                }
            ),
        ]
        
        for address_text, expected in test_cases:
            result = DataNormalizer.normalize_address(address_text)
            
            assert result is not None
            for key, value in expected.items():
                assert result.get(key) == value
    
    def test_normalize_property_type(self):
        """Test property type normalization."""
        test_cases = [
            ("apartment", "apartment"),
            ("dzīvoklis", "apartment"),
            ("flat", "apartment"),
            ("house", "house"),
            ("māja", "house"),
            ("villa", "house"),
            ("land", "land"),
            ("zeme", "land"),
            ("office", "commercial"),
            ("garage", "garage"),
            ("unknown type", "other"),
        ]
        
        for input_type, expected in test_cases:
            result = DataNormalizer.normalize_property_type(input_type)
            assert result == expected
    
    def test_normalize_features(self):
        """Test feature normalization."""
        input_features = [
            "balkons",
            "parking",
            "lifts", 
            "mēbelēts",
            "renovēts",
            "custom feature",
            "",  # Empty string should be filtered out
            "a",  # Too short should be filtered out
        ]
        
        result = DataNormalizer.normalize_features(input_features)
        
        assert "balcony" in result
        assert "parking" in result
        assert "elevator" in result
        assert "furnished" in result
        assert "renovated" in result
        assert "custom feature" in result
        assert "" not in result
        assert "a" not in result
    
    def test_normalize_date(self):
        """Test date normalization from various formats."""
        test_cases = [
            ("15.01.2024", datetime(2024, 1, 15)),
            ("2024-01-15", datetime(2024, 1, 15)),
            ("15/01/2024", datetime(2024, 1, 15)),
            ("15.01.2024 14:30", datetime(2024, 1, 15, 14, 30)),
            ("invalid date", None),
            ("", None),
        ]
        
        for date_text, expected in test_cases:
            result = DataNormalizer.normalize_date(date_text)
            
            if expected is None:
                assert result is None
            else:
                assert result == expected
    
    def test_calculate_price_per_sqm(self):
        """Test price per square meter calculation."""
        test_cases = [
            (150000, 75, 2000.0),
            (100000, 50, 2000.0),
            (0, 75, None),  # Zero price
            (150000, 0, None),  # Zero area
            (None, 75, None),  # None price
            (150000, None, None),  # None area
        ]
        
        for price, area, expected in test_cases:
            result = DataNormalizer.calculate_price_per_sqm(price, area)
            assert result == expected
    
    def test_validate_coordinates(self):
        """Test coordinate validation for Latvia."""
        test_cases = [
            (56.9496, 24.1052, True),   # Riga coordinates
            (56.9677, 23.7794, True),   # Jurmala coordinates  
            (56.5055, 21.0106, True),   # Liepaja coordinates
            (0, 0, False),              # Invalid coordinates
            (90, 180, False),           # Out of Latvia bounds
            (-90, -180, False),         # Negative coordinates
        ]
        
        for lat, lng, expected in test_cases:
            result = DataNormalizer.validate_coordinates(lat, lng)
            assert result == expected
    
    def test_normalize_listing_data_complete(self):
        """Test complete listing data normalization."""
        raw_data = {
            "listing_id": "test_123",
            "source_site": "ss.com",
            "title": "Test Apartment",
            "source_url": "https://test.com",
            "price": "150,000 EUR",
            "price_currency": "EUR",
            "area_sqm": "75.5 m²",
            "property_type": "dzīvoklis",
            "address": "Elizabetes iela 123, Rīga",
            "features": ["balkons", "parkošana", "lifts"],
            "posted_date": "15.01.2024",
            "latitude": 56.9496,
            "longitude": 24.1052
        }
        
        result = normalize_listing_data(raw_data)
        
        # Check that all fields were normalized
        assert result["price"] == 150000.0
        assert result["area_sqm"] == 75.5
        assert result["property_type"] == "apartment"
        assert result["city"] == "Riga"
        assert "balcony" in result["features"]
        assert "parking" in result["features"]
        assert "elevator" in result["features"]
        assert isinstance(result["posted_date"], datetime)
        assert result["price_per_sqm"] == 1986.75  # 150000 / 75.5
        assert result["latitude"] == 56.9496
        assert result["longitude"] == 24.1052