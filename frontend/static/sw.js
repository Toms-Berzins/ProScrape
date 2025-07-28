/**
 * ProScrape Service Worker
 * 
 * Advanced PWA service worker with intelligent caching strategies:
 * - Cache-first for static assets (JS, CSS, images)
 * - Network-first for API data with fallback to cache
 * - Stale-while-revalidate for property listings
 * - Background sync for offline actions
 * - Push notification handling
 */

import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import { 
  StaleWhileRevalidate, 
  CacheFirst, 
  NetworkFirst,
  NetworkOnly 
} from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { BackgroundSyncPlugin } from 'workbox-background-sync';

const CACHE_NAMES = {
  STATIC: 'proscrape-static-v1',
  DYNAMIC: 'proscrape-dynamic-v1',
  IMAGES: 'proscrape-images-v1',
  API: 'proscrape-api-v1',
  OFFLINE: 'proscrape-offline-v1'
};

const API_BASE_URL = 'http://localhost:8000';

// Precache all build assets
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

/**
 * Cache Strategy 1: Cache First for Static Assets
 * Perfect for JS, CSS, fonts, and static images that rarely change
 */
registerRoute(
  ({ request, url }) => 
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'font' ||
    url.pathname.startsWith('/_app/') ||
    url.pathname.includes('/static/'),
  new CacheFirst({
    cacheName: CACHE_NAMES.STATIC,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
        purgeOnQuotaError: true,
      }),
    ],
  })
);

/**
 * Cache Strategy 2: Stale While Revalidate for Property Images
 * Fast loading with background updates for property photos
 */
registerRoute(
  ({ request, url }) => 
    request.destination === 'image' && (
      url.hostname.includes('ss.com') ||
      url.hostname.includes('city24.lv') ||
      url.hostname.includes('pp.lv') ||
      url.pathname.includes('/property-images/')
    ),
  new StaleWhileRevalidate({
    cacheName: CACHE_NAMES.IMAGES,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 500,
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7 days
        purgeOnQuotaError: true,
      }),
    ],
  })
);

/**
 * Cache Strategy 3: Network First for API Calls
 * Fresh data when online, cached fallback when offline
 */
registerRoute(
  ({ url }) => url.origin === API_BASE_URL && url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: CACHE_NAMES.API,
    networkTimeoutSeconds: 5,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 24 * 60 * 60, // 1 day
        purgeOnQuotaError: true,
      }),
    ],
  })
);

/**
 * Cache Strategy 4: Stale While Revalidate for Property Listings
 * Balance between fresh content and fast loading
 */
registerRoute(
  ({ url }) => 
    url.origin === API_BASE_URL && (
      url.pathname.includes('/listings') ||
      url.pathname.includes('/properties') ||
      url.pathname.includes('/search')
    ),
  new StaleWhileRevalidate({
    cacheName: CACHE_NAMES.DYNAMIC,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 200,
        maxAgeSeconds: 60 * 60, // 1 hour
        purgeOnQuotaError: true,
      }),
    ],
  })
);

/**
 * Navigation Route with Offline Fallback
 * Serve cached pages when offline, with custom offline page
 */
const navigationRoute = new NavigationRoute(
  new NetworkFirst({
    cacheName: CACHE_NAMES.DYNAMIC,
    networkTimeoutSeconds: 5,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
    ],
  }),
  {
    allowlist: [/^\/(?!api\/)/], // Match all navigation except API calls
    denylist: [/\/admin/], // Exclude admin routes from caching
  }
);

registerRoute(navigationRoute);

/**
 * Background Sync for Offline Actions
 * Queue failed requests and retry when back online
 */
const bgSyncPlugin = new BackgroundSyncPlugin('offline-actions', {
  maxRetentionTime: 24 * 60, // 24 hours in minutes
});

registerRoute(
  ({ url, request }) => 
    url.origin === API_BASE_URL && 
    (request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE'),
  new NetworkOnly({
    plugins: [bgSyncPlugin],
  }),
  'POST'
);

/**
 * Advanced Offline Support
 */

// Custom offline page
const OFFLINE_PAGE = '/offline.html';
const OFFLINE_CACHE = CACHE_NAMES.OFFLINE;

// Cache offline page on install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(OFFLINE_CACHE)
      .then((cache) => cache.add(OFFLINE_PAGE))
  );
});

// Serve offline page for navigation requests when offline
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.open(OFFLINE_CACHE)
            .then((cache) => cache.match(OFFLINE_PAGE));
        })
    );
  }
});

/**
 * Push Notification Handling
 */
self.addEventListener('push', (event) => {
  const options = {
    body: 'New properties matching your criteria are available!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: '1'
    },
    actions: [
      {
        action: 'explore',
        title: 'View Properties',
        icon: '/icons/action-explore.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/icons/action-close.png'
      }
    ],
    requireInteraction: true,
    persistent: true
  };

  if (event.data) {
    const notificationData = event.data.json();
    options.body = notificationData.body || options.body;
    options.title = notificationData.title || 'ProScrape';
    options.data = { ...options.data, ...notificationData.data };
  }

  event.waitUntil(
    self.registration.showNotification('ProScrape', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/listings')
    );
  } else if (event.action === 'close') {
    // Just close the notification
    return;
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

/**
 * Intelligent Cache Management
 */

// Update cache when app updates
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_LISTINGS') {
    // Pre-cache important listings
    const listings = event.data.listings;
    event.waitUntil(
      caches.open(CACHE_NAMES.DYNAMIC)
        .then((cache) => {
          const requests = listings.map(listing => 
            new Request(`${API_BASE_URL}/api/listings/${listing.id}`)
          );
          return cache.addAll(requests);
        })
    );
  }
});

// Clean up old caches
self.addEventListener('activate', (event) => {
  const cacheWhitelist = Object.values(CACHE_NAMES);
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

/**
 * Network-aware caching
 */
self.addEventListener('fetch', (event) => {
  // Skip for non-GET requests
  if (event.request.method !== 'GET') return;
  
  // Check connection quality
  const connection = navigator.connection;
  if (connection && (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g')) {
    // For slow connections, prefer cache
    if (event.request.url.includes('/api/listings')) {
      event.respondWith(
        caches.match(event.request)
          .then((response) => {
            return response || fetch(event.request);
          })
      );
    }
  }
});

/**
 * Performance monitoring
 */
self.addEventListener('fetch', (event) => {
  const start = performance.now();
  
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const duration = performance.now() - start;
        
        // Log slow requests for monitoring
        if (duration > 2000) {
          console.warn(`Slow request detected: ${event.request.url} took ${duration}ms`);
          
          // Could send to analytics service
          self.registration.sync.register('slow-request-report');
        }
        
        return response;
      })
      .catch((error) => {
        console.error('Network request failed:', event.request.url, error);
        throw error;
      })
  );
});