# Frontend Docker Setup Guide

This guide covers the setup and configuration of the ProScrape frontend with Docker integration.

## Overview

The ProScrape frontend is a modern web application built with:
- **Svelte**: Reactive UI framework
- **Vite**: Fast build tool and dev server
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework

## Docker Integration

### Environment Configuration

The frontend automatically detects and adapts to Docker environments using environment variables:

```bash
# Frontend .env.development
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
DOCKER_ENV=true
```

### API Configuration

The frontend uses a dynamic API configuration that adapts to different environments:

```javascript
// Automatic environment detection
const isDevelopment = process.env.NODE_ENV === 'development';
const isDocker = process.env.DOCKER_ENV === 'true';

// API endpoints adjust based on environment
const API_CONFIGS = {
  development: { baseURL: 'http://localhost:8000' },
  docker: { baseURL: 'http://localhost:8000' },
  production: { baseURL: 'https://api.proscrape.com' }
};
```

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
# Local development
npm run dev

# Docker development (with API connectivity)
DOCKER_ENV=true npm run dev
```

### 3. Build for Production

```bash
npm run build
```

## Docker Services Integration

### API Connectivity

The frontend automatically connects to the FastAPI backend running in Docker:

- **API Base URL**: `http://localhost:8000`
- **WebSocket URL**: `ws://localhost:8000/ws`
- **Health Check**: Automatic API health monitoring
- **CORS**: Properly configured for Docker networking

### Real-time Features

WebSocket connection for real-time updates:

```javascript
import { wsManager } from './config/api.js';

// Connect to WebSocket
wsManager.connect();

// Subscribe to listing updates
wsManager.subscribe('new_listing', (data) => {
  console.log('New listing:', data);
});
```

### Error Handling

Robust error handling for Docker connectivity issues:

```javascript
// Automatic health checks
const healthResult = await dockerHealthCheck();

if (!healthResult.success) {
  // Handle API unavailability
  showErrorMessage('API service unavailable');
}
```

## Development Workflow

### 1. Start Docker Services

```bash
# Start API and database services
docker-compose up -d api mongodb redis

# Verify services are running
docker-compose ps
```

### 2. Start Frontend Development

```bash
# In frontend directory
npm run dev
```

### 3. Test Integration

```bash
# Test API connectivity
curl http://localhost:8000/health

# Test WebSocket
wscat -c ws://localhost:8000/ws
```

## Configuration Files

### Vite Configuration

```javascript
// vite.config.ts
export default defineConfig({
  server: {
    host: true, // Bind to all interfaces for Docker
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
});
```

### Environment Variables

```bash
# .env.development
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_TIMEOUT=15000
DOCKER_ENV=true

# .env.production
VITE_API_URL=https://api.proscrape.com
VITE_WS_URL=wss://api.proscrape.com/ws
DOCKER_ENV=false
```

## Features

### Listing Management

- **Real-time Updates**: New listings appear automatically
- **Advanced Filtering**: Filter by price, area, location, etc.
- **Export Options**: CSV and JSON export functionality
- **Search**: Full-text search across all listing fields

### API Integration

- **Automatic Reconnection**: Handles API disconnections gracefully
- **Health Monitoring**: Displays API status in UI
- **Error Recovery**: Automatic retry for failed requests
- **Loading States**: User-friendly loading indicators

### Chrome Extension Integration

The frontend is designed to work with the ProScrape Chrome extension:

```javascript
// External connection handling
chrome.runtime.onConnectExternal.addListener((port) => {
  port.onMessage.addListener((message) => {
    // Handle extension requests
  });
});
```

## Troubleshooting

### Common Issues

#### API Connection Failed

```bash
# Check API service status
docker-compose logs api

# Verify API is accessible
curl http://localhost:8000/health
```

#### WebSocket Connection Failed

```bash
# Check WebSocket endpoint
wscat -c ws://localhost:8000/ws

# Verify nginx proxy (if used)
docker-compose logs nginx
```

#### CORS Errors

CORS is automatically configured for Docker environments. If you encounter CORS errors:

1. Check the API's CORS configuration
2. Verify the frontend origin is allowed
3. Ensure credentials are properly handled

### Debug Mode

Enable debug mode for detailed logging:

```bash
VITE_LOG_LEVEL=debug npm run dev
```

### Health Checks

The frontend includes built-in health checks:

```javascript
// Manual health check
const health = await dockerHealthCheck();
console.log('API Health:', health);

// Continuous monitoring
setInterval(async () => {
  const health = await dockerHealthCheck();
  updateHealthStatus(health);
}, 60000);
```

## Performance Optimization

### Build Optimization

```bash
# Production build with optimization
npm run build

# Analyze bundle size
npm run build -- --analyze
```

### Docker Optimization

```dockerfile
# Multi-stage Docker build
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

## Monitoring

### Frontend Metrics

- **API Response Times**: Tracked automatically
- **WebSocket Connection Status**: Real-time monitoring
- **Error Rates**: Automatic error tracking
- **User Interactions**: Usage analytics

### Health Dashboard

Access the health dashboard at `http://localhost:3000/health` to view:

- API connectivity status
- WebSocket connection status
- Recent errors and warnings
- Performance metrics

## Security Considerations

### Environment Variables

Never expose sensitive data in frontend environment variables:

```bash
# ✅ Safe - API endpoints
VITE_API_URL=http://localhost:8000

# ❌ Unsafe - API keys or secrets
VITE_API_SECRET=secret-key
```

### Content Security Policy

The frontend implements CSP headers for security:

```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; connect-src 'self' http://localhost:8000 ws://localhost:8000;">
```

### HTTPS in Production

Always use HTTPS in production:

```bash
# Production environment
VITE_API_URL=https://api.proscrape.com
VITE_WS_URL=wss://api.proscrape.com/ws
```

## VS Code Integration

### Recommended Extensions

```json
{
  "recommendations": [
    "svelte.svelte-vscode",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-typescript-next",
    "esbenp.prettier-vscode"
  ]
}
```

### Debug Configuration

Use the provided VS Code launch configuration for debugging:

```json
{
  "name": "Frontend: Node.js Debug",
  "type": "node",
  "request": "attach",
  "port": 9229
}
```

### Tasks

Common VS Code tasks are provided:

- `Frontend: Install Dependencies`
- `Frontend: Start Dev Server`
- `Frontend: Build for Production`

## Deployment

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://api:8000
    depends_on:
      - api
```

### Production Build

```bash
# Build for production
npm run build

# Serve with static server
npx serve -s dist -l 3000
```

This guide provides comprehensive information for setting up and using the ProScrape frontend with Docker integration. For additional help, refer to the main project documentation or open an issue on the project repository.