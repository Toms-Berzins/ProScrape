# ProScrape Vue.js Frontend

A comprehensive Vue.js 3 internationalization system for the ProScrape real estate platform, supporting English (EN), Latvian (LV), and Russian (RU) languages.

## 🌟 Features

### Internationalization (i18n)
- **Multi-language Support**: English, Latvian, and Russian
- **Dynamic Language Switching**: Language switcher with persistent settings
- **Localized URLs**: Language-based routing (`/en/`, `/lv/`, `/ru/`)
- **Locale-specific Formatting**: Prices, dates, areas, and numbers
- **Real Estate Terminology**: Comprehensive translations for property types, features, and amenities
- **Geographic Translations**: City and district names in all supported languages

### Property Search & Display
- **Advanced Property Search**: Multi-criteria filtering with real-time results
- **Property Cards**: Responsive, localized property cards with image galleries
- **Interactive Map**: Leaflet-based map with localized markers and clustering
- **Property Details**: Comprehensive property detail pages with image galleries
- **Saved Properties**: Local storage-based favorites system

### Technical Features
- **Vue 3 Composition API**: Modern Vue.js with TypeScript support
- **Pinia State Management**: Centralized state for language, search, and saved properties
- **Vue Router**: Dynamic routing with language detection
- **API Integration**: Full integration with ProScrape FastAPI i18n endpoints
- **Performance Optimized**: Lazy loading, code splitting, and image optimization
- **Responsive Design**: Mobile-first design with Tailwind CSS
- **Accessibility**: WCAG compliant with proper ARIA labels and keyboard navigation

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn
- ProScrape FastAPI backend running on `http://localhost:8000`

### Installation

```bash
# Navigate to Vue frontend directory
cd vue-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`.

### Development Scripts

```bash
# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check

# Linting and formatting
npm run lint
npm run format

# Extract i18n keys (for translation analysis)
npm run i18n:extract
```

## 🏗️ Project Structure

```
vue-frontend/
├── src/
│   ├── components/          # Reusable Vue components
│   │   ├── layout/         # Header, footer, navigation
│   │   ├── property/       # Property cards, details, galleries
│   │   ├── search/         # Search components and filters
│   │   ├── map/           # Map components and popups
│   │   └── common/        # Generic components
│   ├── views/             # Page components
│   ├── stores/            # Pinia stores
│   │   ├── language.ts    # Language and locale management
│   │   ├── search.ts      # Search state and history
│   │   ├── savedListings.ts # Saved properties
│   │   └── app.ts         # Global app state
│   ├── plugins/           # Vue plugins and configurations
│   │   └── i18n.ts        # Vue i18n setup and utilities
│   ├── services/          # API services
│   │   └── api.ts         # FastAPI integration
│   ├── locales/           # Translation files
│   │   ├── en.json        # English translations
│   │   ├── lv.json        # Latvian translations
│   │   └── ru.json        # Russian translations
│   ├── router/            # Vue Router configuration
│   │   └── index.ts       # Routes with language prefixes
│   └── assets/            # Static assets and styles
│       └── css/           # Global styles and Tailwind config
├── public/                # Static files
└── dist/                  # Production build output
```

## 🌍 Internationalization

### Supported Languages

| Language | Code | Native Name | Features |
|----------|------|-------------|----------|
| English  | `en` | English     | Default language, no URL prefix |
| Latvian  | `lv` | Latviešu    | Complete property terminology |
| Russian  | `ru` | Русский     | Cyrillic support, proper pluralization |

### URL Structure

- **English (default)**: `/search`, `/property/123`, `/map`
- **Latvian**: `/lv/search`, `/lv/property/123`, `/lv/map`  
- **Russian**: `/ru/search`, `/ru/property/123`, `/ru/map`

### Translation Keys

```javascript
// Property types
$t('types.apartment')      // Apartment / Dzīvoklis / Квартира
$t('types.house')          // House / Māja / Дом

// Features
$t('features.balcony')     // Balcony / Balkons / Балкон
$t('features.parking')     // Parking / Autostāvvieta / Парковка

// Cities
$t('cities.riga')          // Riga / Rīga / Рига
$t('cities.jurmala')       // Jurmala / Jūrmala / Юрмала

// Search interface
$t('search.filters.price_range')  // Price Range / Cenu diapazons / Диапазон цен
```

### Locale-specific Formatting

```javascript
// Currency (EUR with proper locale formatting)
formatCurrency(125000)
// EN: EUR 125,000
// LV: 125 000 EUR  
// RU: 125 000 EUR

// Area
formatArea(75.5)
// EN: 75.5 m²
// LV: 75,5 m²
// RU: 75,5 м²

// Dates
formatDate(new Date())
// EN: 2024-01-15
// LV: 15.01.2024
// RU: 15.01.2024
```

## 🔧 API Integration

The frontend integrates seamlessly with the ProScrape FastAPI backend:

### Endpoints Used
- `GET /i18n/listings` - Localized property listings
- `GET /i18n/listings/{id}` - Individual property details
- `GET /i18n/search` - Property search with localization
- `GET /i18n/stats` - Statistics with localized labels
- `GET /i18n/languages` - Supported languages info

### Request Headers
All API requests automatically include:
- `Accept-Language`: Proper language preference header
- `lang`: Query parameter with current locale

### Response Format
All responses include localized data:
```json
{
  "id": "123",
  "title": "Beautiful apartment in Riga",
  "property_type": "apartment",
  "property_type_localized": "Dzīvoklis",
  "city": "riga", 
  "city_localized": "Rīga",
  "price_formatted": "125 000 EUR",
  "language": "lv"
}
```

## 🗺️ Map Integration

Interactive property map with Leaflet:

### Features
- **Property Markers**: Custom markers with price and type
- **Clustering**: Automatic marker clustering for performance
- **Localized Labels**: Map controls and popups in current language
- **Multiple Layers**: Street, satellite, and terrain views
- **Property Popups**: Detailed property info with quick actions
- **Search in Area**: Search properties within current map bounds

### Map Controls
- Zoom controls with accessibility support
- Layer switcher (Street/Satellite/Terrain)
- Clustering toggle
- Search in current area button

## 📱 Responsive Design

### Breakpoints
- **Mobile**: 320px - 767px (single column, collapsible filters)
- **Tablet**: 768px - 1023px (two columns, sidebar filters)
- **Desktop**: 1024px+ (multi-column, expanded layout)

### Mobile Features
- Touch-optimized property cards
- Collapsible filter panels
- Mobile-friendly map controls
- Swipe gesture support for image galleries

## ⚡ Performance Optimizations

### Code Splitting
- Route-based code splitting
- Component lazy loading
- Dynamic i18n message loading

### Image Optimization
- Lazy loading for property images
- WebP format support with fallbacks
- Responsive image sizing

### Caching
- Translation caching in localStorage
- API response caching
- Service worker for offline support (planned)

## 🎯 SEO & Accessibility

### SEO Features
- Proper meta tags with localized content
- Language alternate links (`hreflang`)
- Canonical URLs
- Structured data markup (planned)
- Sitemap generation (planned)

### Accessibility
- WCAG 2.1 AA compliance
- Proper heading structure
- ARIA labels and descriptions
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support

## 🧪 Testing

### Unit Tests
```bash
# Run unit tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

### E2E Tests
```bash
# Run Playwright E2E tests
npm run test:e2e

# Run E2E tests in headed mode
npm run test:e2e:headed
```

## 🚢 Deployment

### Environment Variables
Create a `.env` file:
```env
VITE_API_URL=http://localhost:8000
VITE_MAP_TILES_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

### Production Build
```bash
# Build for production
npm run build

# Preview production build locally
npm run preview
```

### Docker Deployment
```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🔮 Future Enhancements

### Planned Features
- [ ] PWA support with offline capabilities
- [ ] Real-time property updates via WebSocket
- [ ] Advanced map features (drawing tools, custom areas)
- [ ] Property comparison tool
- [ ] Saved searches with email alerts
- [ ] Social sharing integration
- [ ] PDF property reports
- [ ] Virtual tour integration
- [ ] Mortgage calculator
- [ ] Property valuation estimates

### Performance Improvements
- [ ] Service worker implementation
- [ ] Image CDN integration
- [ ] GraphQL API migration
- [ ] Edge caching with Cloudflare
- [ ] Bundle size optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Translation Contributions
We welcome translation improvements! Please update the JSON files in `src/locales/` and ensure all property-specific terminology is accurate.

## 📄 License

This project is part of the ProScrape real estate platform. All rights reserved.

## 🆘 Support

For issues and questions:
- Check the [API Documentation](../api/README.md)
- Review [Backend Integration](../README.md)
- Open an issue in the repository