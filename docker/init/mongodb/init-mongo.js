// MongoDB initialization script for ProScrape
// This script creates the database, collections, and indexes

// Switch to proscrape database
db = db.getSiblingDB('proscrape');

// Create collections with validation schemas
db.createCollection('listings', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['listing_id', 'title', 'spider_source'],
            properties: {
                listing_id: {
                    bsonType: 'string',
                    description: 'Unique identifier for the listing'
                },
                title: {
                    bsonType: 'string',
                    description: 'Title of the listing'
                },
                price: {
                    bsonType: ['number', 'null'],
                    description: 'Price in EUR'
                },
                area: {
                    bsonType: ['number', 'null'],
                    description: 'Area in square meters'
                },
                location: {
                    bsonType: ['string', 'null'],
                    description: 'Location description'
                },
                coordinates: {
                    bsonType: ['object', 'null'],
                    properties: {
                        lat: { bsonType: 'number' },
                        lng: { bsonType: 'number' }
                    }
                },
                features: {
                    bsonType: ['array', 'null'],
                    items: { bsonType: 'string' }
                },
                posted_date: {
                    bsonType: ['date', 'null'],
                    description: 'Date when listing was posted'
                },
                image_urls: {
                    bsonType: ['array', 'null'],
                    items: { bsonType: 'string' }
                },
                spider_source: {
                    bsonType: 'string',
                    enum: ['ss_spider', 'city24_spider', 'pp_spider'],
                    description: 'Source spider that scraped this listing'
                },
                scraped_at: {
                    bsonType: 'date',
                    description: 'Timestamp when item was scraped'
                },
                url: {
                    bsonType: ['string', 'null'],
                    description: 'Original URL of the listing'
                }
            }
        }
    }
});

// Create indexes for listings collection
db.listings.createIndex({ 'listing_id': 1 }, { unique: true });
db.listings.createIndex({ 'spider_source': 1 });
db.listings.createIndex({ 'scraped_at': -1 });
db.listings.createIndex({ 'posted_date': -1 });
db.listings.createIndex({ 'price': 1 });
db.listings.createIndex({ 'area': 1 });
db.listings.createIndex({ 'location': 'text', 'title': 'text' });
db.listings.createIndex({ 'coordinates.lat': 1, 'coordinates.lng': 1 });

// Create geospatial index for location-based queries
db.listings.createIndex({ 'coordinates': '2dsphere' });

// Create collection for scraping sessions
db.createCollection('scraping_sessions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['session_id', 'spider_name', 'start_time'],
            properties: {
                session_id: {
                    bsonType: 'string',
                    description: 'Unique session identifier'
                },
                spider_name: {
                    bsonType: 'string',
                    enum: ['ss_spider', 'city24_spider', 'pp_spider']
                },
                start_time: {
                    bsonType: 'date'
                },
                end_time: {
                    bsonType: ['date', 'null']
                },
                status: {
                    bsonType: 'string',
                    enum: ['running', 'completed', 'failed', 'cancelled'],
                    description: 'Session status'
                },
                items_scraped: {
                    bsonType: 'int',
                    minimum: 0
                },
                items_failed: {
                    bsonType: 'int',
                    minimum: 0
                },
                settings: {
                    bsonType: ['object', 'null'],
                    description: 'Spider settings used for this session'
                },
                error_messages: {
                    bsonType: ['array', 'null'],
                    items: { bsonType: 'string' }
                }
            }
        }
    }
});

// Create indexes for scraping sessions
db.scraping_sessions.createIndex({ 'session_id': 1 }, { unique: true });
db.scraping_sessions.createIndex({ 'spider_name': 1 });
db.scraping_sessions.createIndex({ 'start_time': -1 });
db.scraping_sessions.createIndex({ 'status': 1 });

// Create collection for duplicate tracking
db.createCollection('duplicate_listings', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['original_id', 'duplicate_id', 'detected_at'],
            properties: {
                original_id: {
                    bsonType: 'string',
                    description: 'ID of the original listing'
                },
                duplicate_id: {
                    bsonType: 'string',
                    description: 'ID of the duplicate listing'
                },
                similarity_score: {
                    bsonType: 'number',
                    minimum: 0,
                    maximum: 1
                },
                matching_fields: {
                    bsonType: 'array',
                    items: { bsonType: 'string' }
                },
                detected_at: {
                    bsonType: 'date'
                }
            }
        }
    }
});

// Create indexes for duplicate tracking
db.duplicate_listings.createIndex({ 'original_id': 1 });
db.duplicate_listings.createIndex({ 'duplicate_id': 1 });
db.duplicate_listings.createIndex({ 'detected_at': -1 });

// Create collection for data quality metrics
db.createCollection('data_quality_metrics', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['metric_name', 'spider_source', 'calculated_at'],
            properties: {
                metric_name: {
                    bsonType: 'string',
                    enum: ['completeness', 'accuracy', 'consistency', 'timeliness']
                },
                spider_source: {
                    bsonType: 'string',
                    enum: ['ss_spider', 'city24_spider', 'pp_spider', 'all']
                },
                value: {
                    bsonType: 'number',
                    minimum: 0,
                    maximum: 100
                },
                calculated_at: {
                    bsonType: 'date'
                },
                details: {
                    bsonType: ['object', 'null'],
                    description: 'Additional metric details'
                }
            }
        }
    }
});

// Create indexes for data quality metrics
db.data_quality_metrics.createIndex({ 'metric_name': 1, 'spider_source': 1 });
db.data_quality_metrics.createIndex({ 'calculated_at': -1 });

// Insert sample data for development
db.listings.insertMany([
    {
        listing_id: 'ss_sample_001',
        title: 'Sample Apartment in Riga Center',
        price: 150000,
        area: 65.5,
        location: 'Riga, Center',
        coordinates: { lat: 56.9496, lng: 24.1052 },
        features: ['2 rooms', 'renovated', 'balcony'],
        posted_date: new Date('2024-01-15'),
        image_urls: ['https://example.com/image1.jpg'],
        spider_source: 'ss_spider',
        scraped_at: new Date(),
        url: 'https://ss.com/en/real-estate/sample-001'
    },
    {
        listing_id: 'city24_sample_001',
        title: 'Modern House in Jurmala',
        price: 320000,
        area: 120.0,
        location: 'Jurmala, Majori',
        coordinates: { lat: 56.9680, lng: 23.7794 },
        features: ['4 rooms', 'garden', 'garage', 'sea view'],
        posted_date: new Date('2024-01-18'),
        image_urls: ['https://example.com/image2.jpg', 'https://example.com/image3.jpg'],
        spider_source: 'city24_spider',
        scraped_at: new Date(),
        url: 'https://city24.lv/en/sample-001'
    },
    {
        listing_id: 'pp_sample_001',
        title: 'Cozy Studio in Vecriga',
        price: 85000,
        area: 28.5,
        location: 'Riga, Old Town',
        coordinates: { lat: 56.9489, lng: 24.1077 },
        features: ['studio', 'historical building', 'high ceilings'],
        posted_date: new Date('2024-01-20'),
        image_urls: ['https://example.com/image4.jpg'],
        spider_source: 'pp_spider',
        scraped_at: new Date(),
        url: 'https://pp.lv/lv/sample-001'
    }
]);

// Insert sample scraping sessions
db.scraping_sessions.insertMany([
    {
        session_id: 'session_ss_001',
        spider_name: 'ss_spider',
        start_time: new Date('2024-01-25T10:00:00Z'),
        end_time: new Date('2024-01-25T10:15:00Z'),
        status: 'completed',
        items_scraped: 150,
        items_failed: 2,
        settings: {
            download_delay: 1,
            concurrent_requests: 8,
            proxy_enabled: true
        }
    },
    {
        session_id: 'session_city24_001',
        spider_name: 'city24_spider',
        start_time: new Date('2024-01-25T11:00:00Z'),
        end_time: new Date('2024-01-25T11:25:00Z'),
        status: 'completed',
        items_scraped: 89,
        items_failed: 5,
        settings: {
            download_delay: 2,
            concurrent_requests: 4,
            playwright_enabled: true
        }
    }
]);

// Insert sample data quality metrics
db.data_quality_metrics.insertMany([
    {
        metric_name: 'completeness',
        spider_source: 'ss_spider',
        value: 95.5,
        calculated_at: new Date(),
        details: {
            total_fields: 9,
            missing_fields: 0.5,
            most_missing: 'coordinates'
        }
    },
    {
        metric_name: 'accuracy',
        spider_source: 'city24_spider',
        value: 92.3,
        calculated_at: new Date(),
        details: {
            price_accuracy: 98.5,
            location_accuracy: 87.2,
            coordinate_accuracy: 91.1
        }
    }
]);

// Create user for the application
db.createUser({
    user: 'proscrape_user',
    pwd: 'proscrape_password',
    roles: [
        {
            role: 'readWrite',
            db: 'proscrape'
        }
    ]
});

print('MongoDB initialization completed successfully');
print('Collections created: listings, scraping_sessions, duplicate_listings, data_quality_metrics');
print('Indexes created for optimal query performance');
print('Sample data inserted for development testing');
print('User proscrape_user created with readWrite permissions');