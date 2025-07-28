# Enhanced WebSocket Docker Deployment Guide

This guide provides comprehensive instructions for deploying the ProScrape application with the enhanced WebSocket manager using Docker.

## Prerequisites

1. **Docker Desktop** installed and running
2. **Docker Compose** v2.0+ 
3. **MongoDB Atlas** connection (or local MongoDB)
4. **Environment files** configured

## Quick Start

### 1. Start Core Services (Redis + API)

```bash
# Start Redis and API with enhanced WebSocket support
docker-compose -f docker-compose.websocket.yml --env-file .env.docker up -d redis api

# Check service health
docker-compose -f docker-compose.websocket.yml ps
```

### 2. Test WebSocket Connection

```bash
# Test the enhanced WebSocket endpoint
python test_websocket_stability.py
```

### 3. Start Full Stack (Production)

```bash
# Start all services including Nginx proxy
docker-compose -f docker-compose.websocket.yml --env-file .env.docker --profile production up -d
```

## Configuration Files

### Environment Configuration (.env.docker)

The deployment uses `.env.docker` with optimized settings for the enhanced WebSocket manager:

```bash
# Enhanced WebSocket Manager Settings
WEBSOCKET_PING_INTERVAL=30          # Ping every 30 seconds
WEBSOCKET_PING_TIMEOUT=10           # 10 second ping timeout
WEBSOCKET_MAX_PING_FAILURES=3       # Max 3 ping failures before disconnect

# Redis Configuration (required for enhanced manager)
REDIS_URL=redis://redis:6379/0

# CORS Configuration (include WebSocket origins)
CORS_ORIGINS=ws://localhost:8000,wss://localhost:8000
```

### Docker Compose Services

#### 1. Redis Service
```yaml
redis:
  image: redis:7.2-alpine
  container_name: proscrape_redis
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 15s
```

#### 2. Enhanced API Service
```yaml
api:
  build:
    dockerfile: docker/Dockerfile.api
    target: production
  container_name: proscrape_api_enhanced
  environment:
    - REDIS_URL=redis://redis:6379/0
    - WEBSOCKET_PING_INTERVAL=30
  volumes:
    - ./websocket:/app/websocket:ro  # Enhanced WebSocket manager
```

#### 3. Nginx WebSocket Proxy
```yaml
nginx:
  image: nginx:alpine
  volumes:
    - ./docker/nginx/websocket.conf:/etc/nginx/conf.d/default.conf:ro
```

## Deployment Modes

### Development Mode

```bash
# Start with development settings
BUILD_TARGET=development VOLUME_MODE= docker-compose -f docker-compose.websocket.yml up -d
```

Features:
- Hot-reload enabled
- Debug logging
- Source code mounted as volumes

### Production Mode

```bash
# Start with production optimizations
BUILD_TARGET=production docker-compose -f docker-compose.websocket.yml --profile production up -d
```

Features:
- Optimized builds
- Nginx reverse proxy
- Resource limits
- Health monitoring

## WebSocket Features

### Enhanced Connection Manager

The containerized deployment includes:

1. **Connection State Tracking**
   - Unique connection IDs
   - Connection lifecycle management
   - Real-time statistics

2. **Health Monitoring**
   - Automatic ping/pong (30s intervals)
   - Connection health checks
   - Background cleanup tasks

3. **Monitoring Endpoints**
   - `/monitoring/websocket/stats` - Connection statistics
   - `/health` - Overall system health
   - Real-time metrics collection

### WebSocket Client Integration

The enhanced manager is fully compatible with existing frontend clients:

```typescript
// Frontend WebSocket client (websocket.ts)
const wsManager = new WebSocketManager('ws://localhost:8000/ws');
wsManager.connect();

// Subscribe to real-time updates
wsManager.addEventListener('new_listing', (data) => {
    console.log('New listing received:', data);
});
```

## Testing WebSocket Deployment

### 1. Connection Stability Test

```bash
# Run comprehensive stability tests
python test_websocket_stability.py
```

Expected results:
- ✅ Multiple simultaneous connections
- ✅ Ping/pong health monitoring
- ✅ Graceful reconnection handling
- ✅ Real-time statistics

### 2. Frontend Integration Test

```bash
# Test frontend WebSocket client compatibility
python test_frontend_ws.py
```

Expected results:
- ✅ Successful connection establishment
- ✅ Subscription confirmation
- ✅ Language switching support
- ✅ Heartbeat mechanism

### 3. Load Testing (Optional)

```bash
# Install websocket-client for load testing
pip install websocket-client

# Run load test with multiple connections
python -c "
import asyncio
import websockets
import json
from concurrent.futures import ThreadPoolExecutor

async def create_connections(num_connections=10):
    connections = []
    for i in range(num_connections):
        try:
            ws = await websockets.connect('ws://localhost:8000/ws')
            connections.append(ws)
            print(f'Connection {i+1}: Created')
        except Exception as e:
            print(f'Connection {i+1}: Failed - {e}')
    
    # Keep connections alive for testing
    await asyncio.sleep(60)
    
    # Close all connections
    for i, ws in enumerate(connections):
        await ws.close()
        print(f'Connection {i+1}: Closed')

asyncio.run(create_connections(10))
"
```

## Monitoring and Troubleshooting

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check WebSocket statistics
curl http://localhost:8000/monitoring/websocket/stats

# Check Docker service health
docker-compose -f docker-compose.websocket.yml ps
```

### Log Analysis

```bash
# API logs
docker-compose -f docker-compose.websocket.yml logs -f api

# Redis logs
docker-compose -f docker-compose.websocket.yml logs -f redis

# Nginx logs (if using production profile)
docker-compose -f docker-compose.websocket.yml logs -f nginx
```

### Common Issues

#### 1. WebSocket Connection Refused
```bash
# Check if API service is running
docker-compose -f docker-compose.websocket.yml ps api

# Check API logs for errors
docker-compose -f docker-compose.websocket.yml logs api

# Verify Redis connectivity
docker-compose -f docker-compose.websocket.yml exec redis redis-cli ping
```

#### 2. High Memory Usage
```bash
# Check container resource usage
docker stats proscrape_api_enhanced proscrape_redis

# Monitor WebSocket connections
curl http://localhost:8000/monitoring/websocket/stats
```

#### 3. Connection Drops
```bash
# Check enhanced manager logs
docker-compose -f docker-compose.websocket.yml logs api | grep "websocket"

# Verify ping/pong mechanism
curl -s http://localhost:8000/monitoring/websocket/stats | jq '.ping_interval'
```

## Performance Optimization

### Resource Limits

The deployment includes optimized resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 512M        # API container limit
    reservations:
      memory: 256M        # Guaranteed memory
```

### Redis Configuration

Redis is optimized for WebSocket background tasks:

```bash
# Memory limit and eviction policy
redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Nginx Proxy Settings

WebSocket-specific Nginx configuration:

```nginx
# Extended timeouts for WebSocket connections
proxy_send_timeout 3600s;
proxy_read_timeout 3600s;

# Buffer settings
proxy_buffering off;
proxy_cache off;
```

## Production Considerations

### SSL/HTTPS Support

For production deployments with SSL:

1. **Update Nginx configuration** with SSL certificates
2. **Configure WSS** (WebSocket Secure) endpoints
3. **Update CORS origins** to include HTTPS/WSS URLs

### Scaling

For high-traffic deployments:

1. **Horizontal scaling**: Deploy multiple API containers
2. **Load balancing**: Use Nginx upstream configuration
3. **Redis clustering**: Consider Redis Cluster for high availability

### Security

1. **Network isolation**: Use Docker networks
2. **Resource limits**: Prevent resource exhaustion
3. **Health monitoring**: Automated health checks
4. **Log aggregation**: Centralized logging system

## Conclusion

The enhanced WebSocket implementation is fully containerized and production-ready. The Docker deployment provides:

- ✅ **Stable WebSocket connections** with automatic health monitoring
- ✅ **Scalable architecture** with Redis backend
- ✅ **Production-ready configuration** with Nginx proxy
- ✅ **Comprehensive monitoring** and health checks
- ✅ **Development/production modes** for different environments

This resolves the original "Connected (Unstable)" WebSocket issues through a robust, containerized deployment architecture.