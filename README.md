# ProScrape - Latvian Real Estate Aggregator

A comprehensive web scraping pipeline and frontend for aggregating real estate listings from Latvia's top property websites.

## 🏗️ Architecture

```
ProScrape/
├── spiders/              # Scrapy spiders for data collection
├── models/               # Pydantic data models
├── api/                  # FastAPI backend application
├── frontend/             # SvelteKit frontend application
├── tasks/                # Celery task queue
├── utils/                # Database, proxies, normalization
└── config/               # Environment configuration
```

## 🎯 Target Sites

- **ss.com/en/real-estate/** - Static HTML scraping with BeautifulSoup/XPath
- **city24.lv/en/** - Dynamic JavaScript scraping with Playwright
- **pp.lv/lv/landing/nekustamais-ipasums** - Dynamic JavaScript scraping with Playwright

## ✅ Current Status

### Backend (✅ Complete)
- **Scrapy Spiders** - All three site scrapers implemented and tested
- **FastAPI API** - Full REST API with pagination, filtering, export
- **MongoDB Storage** - Atlas cluster with data validation
- **Celery Tasks** - Background job processing with Redis
- **Proxy Rotation** - Intelligent proxy health monitoring
- **Error Handling** - Dead letter queues and alerting system
- **WebSocket Support** - Real-time updates for live data

### Frontend (✅ Complete - Basic)
- **SvelteKit + TypeScript** - Modern web framework setup
- **TailwindCSS** - Responsive design system
- **API Integration** - Full REST client and WebSocket manager
- **Component Library** - Listing cards, grids, layout components
- **Type Safety** - Complete TypeScript coverage
- **Development Ready** - Environment configuration and build system

## 🚀 Quick Start

### Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt
python -m playwright install chromium

# Start services
start_redis.bat                    # Redis server
python run.py api                  # FastAPI server
python run.py worker               # Celery worker
python run.py beat                 # Celery scheduler

# Test scrapers
python -m scrapy crawl ss_spider
python -m scrapy crawl city24_spider
python -m scrapy crawl pp_spider
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev                        # Development server on :3000
```

## 🔧 Configuration

### Environment Variables
```env
# Backend (.env)
MONGODB_URL=mongodb+srv://...
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO

# Frontend (frontend/.env)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## 📊 API Endpoints

### Core Endpoints
- `GET /` - API root
- `GET /health` - Health check
- `GET /listings` - Paginated listings with filters
- `GET /listings/{id}` - Individual listing details
- `GET /listings/search` - Text search
- `GET /stats` - Database statistics

### Real-time & Export
- `WebSocket /ws` - Live listing updates
- `GET /export/csv` - CSV export with filtering
- `GET /export/json` - JSON export with filtering

### Monitoring
- `GET /proxy/stats` - Proxy health statistics
- `GET /monitoring/health` - System health check
- `GET /monitoring/alerts` - Alert system status

## 🎨 Frontend Features

### Implemented
- **Homepage** - Hero section with search and stats
- **Listings Page** - Grid/list view with infinite scroll
- **Navigation** - Responsive header with mobile menu
- **Property Cards** - Rich display with images and details
- **Loading States** - Skeleton screens and error handling
- **Type Safety** - Full TypeScript integration

### Planned
- **Advanced Search** - Multi-criteria filtering interface
- **Individual Listings** - Detailed property pages with galleries
- **Map Integration** - Leaflet-based geographic search
- **User Preferences** - Saved listings and alerts
- **Real-time Updates** - WebSocket integration for live data

## 🛠️ Development

### Backend Testing
```bash
python test_connection.py          # MongoDB connectivity
python test_celery_worker.py       # Celery worker health
pytest tests/                      # Unit tests
```

### Frontend Development
```bash
cd frontend
npm run dev                        # Development server
npm run build                      # Production build
npm run check                      # Type checking
```

## 🔄 Deployment

### Production Setup
```bash
# Docker deployment
docker-compose -f docker-compose.redis.yml up -d

# Manual deployment
# See DEPLOYMENT.md for detailed instructions
```

### Frontend Deployment
Ready for deployment to:
- Vercel (recommended)
- Netlify
- Static hosting
- Node.js servers

## 📈 Monitoring

- **Flower** - Celery task monitoring on :5555
- **System Health** - Comprehensive health checks
- **Proxy Statistics** - Rotation and success rates
- **Dead Letter Queue** - Failed item tracking
- **Alert System** - Email/webhook notifications

## 🔒 Security Features

- **Proxy Rotation** - Intelligent IP management
- **Rate Limiting** - Request throttling per site
- **User-Agent Rotation** - Realistic browser simulation
- **Error Handling** - Graceful failure recovery
- **Data Validation** - Pydantic model validation

## 📝 Documentation

- **CLAUDE.md** - Comprehensive project documentation
- **FRONTEND.md** - Frontend implementation plan
- **DEPLOYMENT.md** - Production deployment guide

## 🤝 Integration

The system provides a complete real estate aggregation solution:
1. **Data Collection** - Automated scraping from multiple sources
2. **Data Processing** - Normalization and validation
3. **API Layer** - RESTful access with real-time updates
4. **Frontend Interface** - Modern web application for browsing
5. **Monitoring** - Health checks and performance metrics

Perfect for real estate platforms, property search engines, or market analysis tools.
