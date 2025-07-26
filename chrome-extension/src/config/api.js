// API Configuration for Chrome Extension Docker Integration

// Environment detection
const isDevelopment = process.env.NODE_ENV === 'development';
const isDocker = process.env.DOCKER_ENV === 'true';

// API Base URLs for different environments
const API_CONFIGS = {
  development: {
    baseURL: 'http://localhost:8000',
    wsURL: 'ws://localhost:8000/ws',
    timeout: 10000,
  },
  docker: {
    baseURL: 'http://localhost:8000',
    wsURL: 'ws://localhost:8000/ws', 
    timeout: 15000,
  },
  production: {
    baseURL: 'https://api.proscrape.com',
    wsURL: 'wss://api.proscrape.com/ws',
    timeout: 20000,
  }
};

// Get current configuration
const getCurrentConfig = () => {
  if (isDevelopment && isDocker) return API_CONFIGS.docker;
  if (isDevelopment) return API_CONFIGS.development;
  return API_CONFIGS.production;
};

const config = getCurrentConfig();

// API Client Configuration
export const API_CONFIG = {
  ...config,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: true,
};

// WebSocket Configuration
export const WS_CONFIG = {
  url: config.wsURL,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  heartbeatInterval: 30000,
};

// Chrome Extension Specific Configuration
export const EXTENSION_CONFIG = {
  manifestVersion: 3,
  permissions: [
    'activeTab',
    'storage',
    'scripting'
  ],
  hostPermissions: [
    'http://localhost:8000/*',
    'http://127.0.0.1:8000/*',
    'https://api.proscrape.com/*'
  ],
  contentSecurityPolicy: {
    extension_pages: "script-src 'self'; object-src 'self';"
  }
};

// API Endpoints
export const ENDPOINTS = {
  // Core endpoints
  health: '/health',
  listings: '/listings',
  search: '/listings/search',
  stats: '/stats',
  
  // Export endpoints
  exportCSV: '/export/csv',
  exportJSON: '/export/json',
  
  // Monitoring endpoints
  proxyStats: '/proxy/stats',
  deadLetterQueue: '/monitoring/dead-letter-queue',
  alerts: '/monitoring/alerts',
  systemHealth: '/monitoring/health',
  
  // WebSocket
  websocket: '/ws',
};

// HTTP Methods
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  DELETE: 'DELETE',
  PATCH: 'PATCH',
  OPTIONS: 'OPTIONS',
};

// Error handling configuration
export const ERROR_CONFIG = {
  retryAttempts: 3,
  retryDelay: 1000,
  networkTimeout: 30000,
};

// Docker health check helper
export const dockerHealthCheck = async () => {
  try {
    const response = await fetch(`${API_CONFIG.baseURL}/health`, {
      method: 'GET',
      headers: API_CONFIG.headers,
      signal: AbortSignal.timeout(5000)
    });
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    
    const data = await response.json();
    return {
      success: true,
      data,
      dockerEnabled: data.docker_enabled || false,
      services: data.services || {}
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      dockerEnabled: false
    };
  }
};

// API request helper with Docker-specific error handling
export const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_CONFIG.baseURL}${endpoint}`;
  const config = {
    ...API_CONFIG,
    ...options,
    headers: {
      ...API_CONFIG.headers,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }
    
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  } catch (error) {
    console.error(`API request to ${endpoint} failed:`, error);
    throw error;
  }
};

// WebSocket connection helper
export class WebSocketManager {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.isConnecting = false;
    this.listeners = new Map();
  }

  connect() {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;
    
    try {
      this.ws = new WebSocket(WS_CONFIG.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected to ProScrape API');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners(data.type, data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.isConnecting = false;
        this.stopHeartbeat();
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.isConnecting = false;
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.stopHeartbeat();
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  subscribe(type, callback) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type).add(callback);
  }

  unsubscribe(type, callback) {
    if (this.listeners.has(type)) {
      this.listeners.get(type).delete(callback);
    }
  }

  notifyListeners(type, data) {
    if (this.listeners.has(type)) {
      this.listeners.get(type).forEach(callback => callback(data));
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, WS_CONFIG.heartbeatInterval);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < WS_CONFIG.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect WebSocket (${this.reconnectAttempts}/${WS_CONFIG.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect();
      }, WS_CONFIG.reconnectInterval * this.reconnectAttempts);
    } else {
      console.error('Max WebSocket reconnection attempts reached');
    }
  }
}

// Global WebSocket manager instance
export const wsManager = new WebSocketManager();

// Initialize connection for extension
if (typeof chrome !== 'undefined' && chrome.runtime) {
  // Chrome extension context - initialize on extension load
  chrome.runtime.onStartup.addListener(() => {
    wsManager.connect();
  });
  
  chrome.runtime.onInstalled.addListener(() => {
    wsManager.connect();
  });
}

export default {
  API_CONFIG,
  WS_CONFIG,
  EXTENSION_CONFIG,
  ENDPOINTS,
  HTTP_METHODS,
  ERROR_CONFIG,
  dockerHealthCheck,
  apiRequest,
  WebSocketManager,
  wsManager
};