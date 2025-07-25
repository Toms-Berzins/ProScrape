import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
from w3lib.html import remove_tags


def clean_text(value):
    """Clean and normalize text values."""
    if not value:
        return None
    return value.strip()


def parse_price(value):
    """Parse price from string to float."""
    if not value:
        return None
    # Remove currency symbols and spaces
    cleaned = value.replace('€', '').replace('EUR', '').replace(',', '').replace(' ', '')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_area(value):
    """Parse area from string to float."""
    if not value:
        return None
    # Extract numbers from area strings like "45.5 m²"
    import re
    match = re.search(r'(\d+\.?\d*)', str(value))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def parse_rooms(value):
    """Parse number of rooms from string to int."""
    if not value:
        return None
    import re
    match = re.search(r'(\d+)', str(value))
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


class ListingItem(scrapy.Item):
    """Scrapy item for real estate listings."""
    
    # Required fields
    listing_id = scrapy.Field()
    source_site = scrapy.Field()
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=TakeFirst()
    )
    source_url = scrapy.Field()
    
    # Price information
    price = scrapy.Field(
        input_processor=MapCompose(clean_text, parse_price),
        output_processor=TakeFirst()
    )
    price_currency = scrapy.Field(
        output_processor=TakeFirst()
    )
    currency = scrapy.Field(  # Added for normalization compatibility
        output_processor=TakeFirst()
    )
    original_price = scrapy.Field(  # Added for normalization
        output_processor=TakeFirst()
    )
    original_currency = scrapy.Field(  # Added for normalization
        output_processor=TakeFirst()
    )
    price_per_sqm = scrapy.Field(
        input_processor=MapCompose(clean_text, parse_price),
        output_processor=TakeFirst()
    )
    
    # Property details
    property_type = scrapy.Field(
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=TakeFirst()
    )
    area_sqm = scrapy.Field(
        input_processor=MapCompose(clean_text, parse_area),
        output_processor=TakeFirst()
    )
    rooms = scrapy.Field(
        input_processor=MapCompose(clean_text, parse_rooms),
        output_processor=TakeFirst()
    )
    floor = scrapy.Field(
        input_processor=MapCompose(clean_text, parse_rooms),
        output_processor=TakeFirst()
    )
    total_floors = scrapy.Field(
        input_processor=MapCompose(clean_text, parse_rooms),
        output_processor=TakeFirst()
    )
    
    # Location
    address = scrapy.Field(
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=TakeFirst()
    )
    full_address = scrapy.Field(  # Added for normalization
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=TakeFirst()
    )
    city = scrapy.Field(
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=TakeFirst()
    )
    district = scrapy.Field(
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=TakeFirst()
    )
    postal_code = scrapy.Field(
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=TakeFirst()
    )
    latitude = scrapy.Field()
    longitude = scrapy.Field()
    
    # Description and features
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, clean_text),
        output_processor=Join('\n')
    )
    features = scrapy.Field()
    amenities = scrapy.Field()
    
    # Media
    image_urls = scrapy.Field()
    video_urls = scrapy.Field()
    
    # Dates
    posted_date = scrapy.Field()
    updated_date = scrapy.Field()
    scraped_at = scrapy.Field()
    
    # Raw data
    raw_data = scrapy.Field()