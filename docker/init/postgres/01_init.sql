-- PostgreSQL initialization script for ProScrape
-- This script creates the database schema and initial data

-- Create the main database if it doesn't exist
SELECT 'CREATE DATABASE proscrape_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'proscrape_db')\gexec

-- Connect to the proscrape database
\c proscrape_db;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Create schema for scraping metadata
CREATE SCHEMA IF NOT EXISTS scraping;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Table for tracking spider runs
CREATE TABLE IF NOT EXISTS scraping.spider_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    spider_name VARCHAR(50) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'running',
    items_scraped INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    settings JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for proxy health monitoring
CREATE TABLE IF NOT EXISTS monitoring.proxy_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proxy_url VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_checked TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER,
    success_rate DECIMAL(5,2) DEFAULT 100.00,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_error TEXT,
    country_code VARCHAR(2),
    anonymity_level VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for system alerts and notifications
CREATE TABLE IF NOT EXISTS monitoring.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    is_resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for tracking failed items (dead letter queue)
CREATE TABLE IF NOT EXISTS scraping.failed_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    spider_name VARCHAR(50) NOT NULL,
    item_data JSONB NOT NULL,
    error_message TEXT,
    error_type VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_retry_at TIMESTAMP WITH TIME ZONE,
    is_resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for API usage tracking
CREATE TABLE IF NOT EXISTS monitoring.api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    user_agent TEXT,
    ip_address INET,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_spider_runs_spider_name ON scraping.spider_runs(spider_name);
CREATE INDEX IF NOT EXISTS idx_spider_runs_start_time ON scraping.spider_runs(start_time);
CREATE INDEX IF NOT EXISTS idx_spider_runs_status ON scraping.spider_runs(status);

CREATE INDEX IF NOT EXISTS idx_proxy_health_proxy_url ON monitoring.proxy_health(proxy_url);
CREATE INDEX IF NOT EXISTS idx_proxy_health_is_active ON monitoring.proxy_health(is_active);
CREATE INDEX IF NOT EXISTS idx_proxy_health_last_checked ON monitoring.proxy_health(last_checked);

CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON monitoring.alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON monitoring.alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_is_resolved ON monitoring.alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON monitoring.alerts(created_at);

CREATE INDEX IF NOT EXISTS idx_failed_items_spider_name ON scraping.failed_items(spider_name);
CREATE INDEX IF NOT EXISTS idx_failed_items_is_resolved ON scraping.failed_items(is_resolved);
CREATE INDEX IF NOT EXISTS idx_failed_items_created_at ON scraping.failed_items(created_at);

CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON monitoring.api_usage(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON monitoring.api_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_api_usage_status_code ON monitoring.api_usage(status_code);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_spider_runs_updated_at BEFORE UPDATE ON scraping.spider_runs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proxy_health_updated_at BEFORE UPDATE ON monitoring.proxy_health FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON monitoring.alerts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_failed_items_updated_at BEFORE UPDATE ON scraping.failed_items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for development
INSERT INTO monitoring.proxy_health (proxy_url, is_active, success_rate, country_code, anonymity_level) VALUES
    ('http://proxy1.example.com:8080', true, 95.50, 'US', 'anonymous'),
    ('http://proxy2.example.com:8080', true, 87.25, 'UK', 'elite'),
    ('http://proxy3.example.com:8080', false, 45.00, 'DE', 'transparent')
ON CONFLICT DO NOTHING;

INSERT INTO monitoring.alerts (alert_type, severity, title, message, metadata) VALUES
    ('proxy_failure', 'warning', 'Proxy Server Down', 'Proxy proxy3.example.com:8080 has been marked as inactive', '{"proxy_url": "http://proxy3.example.com:8080", "consecutive_failures": 5}'),
    ('spider_error', 'error', 'Spider Crash', 'ss_spider crashed with memory error', '{"spider_name": "ss_spider", "error_type": "MemoryError"}'),
    ('rate_limit', 'info', 'Rate Limit Reached', 'Rate limit reached for city24.lv', '{"domain": "city24.lv", "requests_per_hour": 1000}')
ON CONFLICT DO NOTHING;

-- Create a view for spider statistics
CREATE OR REPLACE VIEW scraping.spider_stats AS
SELECT 
    spider_name,
    COUNT(*) as total_runs,
    AVG(items_scraped) as avg_items_scraped,
    AVG(EXTRACT(EPOCH FROM (end_time - start_time))/60) as avg_duration_minutes,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_runs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
    MAX(start_time) as last_run_time
FROM scraping.spider_runs 
WHERE end_time IS NOT NULL
GROUP BY spider_name;

-- Create a view for proxy statistics
CREATE OR REPLACE VIEW monitoring.proxy_stats AS
SELECT 
    proxy_url,
    is_active,
    success_rate,
    total_requests,
    successful_requests,
    consecutive_failures,
    country_code,
    anonymity_level,
    CASE 
        WHEN consecutive_failures >= 5 THEN 'critical'
        WHEN consecutive_failures >= 3 THEN 'warning'
        WHEN success_rate < 80 THEN 'warning'
        ELSE 'healthy'
    END as health_status,
    last_checked,
    EXTRACT(EPOCH FROM (NOW() - last_checked))/60 as minutes_since_check
FROM monitoring.proxy_health;

-- Grant permissions
GRANT USAGE ON SCHEMA scraping TO PUBLIC;
GRANT USAGE ON SCHEMA monitoring TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA scraping TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA monitoring TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA scraping TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA monitoring TO PUBLIC;

-- Create user for the application
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'proscrape_user') THEN
        CREATE ROLE proscrape_user WITH LOGIN PASSWORD 'proscrape_password';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE proscrape_db TO proscrape_user;
GRANT USAGE ON SCHEMA scraping, monitoring TO proscrape_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA scraping, monitoring TO proscrape_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA scraping, monitoring TO proscrape_user;