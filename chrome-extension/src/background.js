/**
 * ProScrape Chrome Extension Background Script
 * Handles Docker API connectivity, WebSocket management, and background tasks
 */

import { wsManager, dockerHealthCheck, API_CONFIG, ENDPOINTS } from './config/api.js';

// Extension state management
let extensionState = {
  isConnected: false,
  apiHealth: 'unknown',
  dockerEnabled: false,
  lastHealthCheck: null,
  connectionRetries: 0,
  maxRetries: 5
};

// Configuration
const HEALTH_CHECK_INTERVAL = 60000; // 1 minute
const CONNECTION_RETRY_DELAY = 5000; // 5 seconds
const NOTIFICATION_TIMEOUT = 5000; // 5 seconds

/**
 * Initialize extension on startup/install
 */
chrome.runtime.onStartup.addListener(async () => {
  console.log('ProScrape Extension: Starting up...');
  await initializeExtension();
});

chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('ProScrape Extension: Installed/Updated', details);
  await initializeExtension();
  
  // Show welcome notification on first install
  if (details.reason === 'install') {
    await showNotification('ProScrape Extension Installed', 'Click to configure API connection');
  }
});

/**
 * Initialize extension components
 */
async function initializeExtension() {
  try {
    // Load saved settings
    await loadSettings();
    
    // Start health monitoring
    await startHealthMonitoring();
    
    // Initialize WebSocket connection
    wsManager.connect();
    
    // Set up periodic health checks
    chrome.alarms.create('healthCheck', { periodInMinutes: 1 });
    
    console.log('ProScrape Extension: Initialization complete');
  } catch (error) {
    console.error('ProScrape Extension: Initialization failed:', error);
  }
}

/**
 * Load extension settings from storage
 */
async function loadSettings() {
  try {
    const result = await chrome.storage.sync.get({
      apiUrl: API_CONFIG.baseURL,
      wsUrl: API_CONFIG.wsURL,
      enableNotifications: true,
      autoConnect: true,
      healthCheckInterval: HEALTH_CHECK_INTERVAL
    });
    
    // Update API configuration with saved settings
    if (result.apiUrl !== API_CONFIG.baseURL) {
      API_CONFIG.baseURL = result.apiUrl;
      console.log('ProScrape Extension: Updated API URL to', result.apiUrl);
    }
    
    extensionState.settings = result;
    return result;
  } catch (error) {
    console.error('ProScrape Extension: Failed to load settings:', error);
    return {};
  }
}

/**
 * Start health monitoring of Docker services
 */
async function startHealthMonitoring() {
  try {
    const healthResult = await dockerHealthCheck();
    
    extensionState.isConnected = healthResult.success;
    extensionState.apiHealth = healthResult.success ? 'healthy' : 'unhealthy';
    extensionState.dockerEnabled = healthResult.dockerEnabled;
    extensionState.lastHealthCheck = new Date().toISOString();
    
    if (healthResult.success) {
      extensionState.connectionRetries = 0;
      console.log('ProScrape Extension: Connected to Docker API');
      
      // Update badge to show connected status
      await updateBadge('✓', '#22c55e'); // Green checkmark
      
      // Show success notification if previously disconnected
      if (extensionState.settings?.enableNotifications) {
        await showNotification('ProScrape Connected', 'Successfully connected to Docker API');
      }
    } else {
      console.warn('ProScrape Extension: Failed to connect to Docker API:', healthResult.error);
      
      // Update badge to show error status
      await updateBadge('✗', '#ef4444'); // Red X
      
      // Attempt reconnection
      await attemptReconnection();
    }
    
    // Save state to storage
    await chrome.storage.local.set({ extensionState });
    
  } catch (error) {
    console.error('ProScrape Extension: Health monitoring failed:', error);
    extensionState.apiHealth = 'error';
    await updateBadge('!', '#f59e0b'); // Orange warning
  }
}

/**
 * Attempt to reconnect to the API
 */
async function attemptReconnection() {
  if (extensionState.connectionRetries >= extensionState.maxRetries) {
    console.error('ProScrape Extension: Max reconnection attempts reached');
    
    if (extensionState.settings?.enableNotifications) {
      await showNotification(
        'ProScrape Connection Failed', 
        'Unable to connect to Docker API after multiple attempts'
      );
    }
    return;
  }
  
  extensionState.connectionRetries++;
  console.log(`ProScrape Extension: Attempting reconnection ${extensionState.connectionRetries}/${extensionState.maxRetries}`);
  
  setTimeout(async () => {
    await startHealthMonitoring();
  }, CONNECTION_RETRY_DELAY * extensionState.connectionRetries);
}

/**
 * Handle periodic alarms
 */
chrome.alarms.onAlarm.addListener(async (alarm) => {
  switch (alarm.name) {
    case 'healthCheck':
      await startHealthMonitoring();
      break;
    default:
      console.log('ProScrape Extension: Unknown alarm:', alarm.name);
  }
});

/**
 * Update extension badge
 */
async function updateBadge(text, color) {
  try {
    await chrome.action.setBadgeText({ text });
    await chrome.action.setBadgeBackgroundColor({ color });
  } catch (error) {
    console.error('ProScrape Extension: Failed to update badge:', error);
  }
}

/**
 * Show notification to user
 */
async function showNotification(title, message) {
  try {
    const notificationId = `proscrape_${Date.now()}`;
    
    await chrome.notifications.create(notificationId, {
      type: 'basic',
      iconUrl: 'icons/icon-48.png',
      title,
      message
    });
    
    // Auto-clear notification after timeout
    setTimeout(() => {
      chrome.notifications.clear(notificationId);
    }, NOTIFICATION_TIMEOUT);
    
  } catch (error) {
    console.error('ProScrape Extension: Failed to show notification:', error);
  }
}

/**
 * Handle messages from popup/content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.action) {
    case 'getExtensionState':
      sendResponse(extensionState);
      break;
      
    case 'checkHealth':
      startHealthMonitoring().then(() => {
        sendResponse(extensionState);
      });
      return true; // Indicate async response
      
    case 'updateSettings':
      updateSettings(message.settings).then(() => {
        sendResponse({ success: true });
      }).catch(error => {
        sendResponse({ success: false, error: error.message });
      });
      return true;
      
    case 'connectWebSocket':
      wsManager.connect();
      sendResponse({ success: true });
      break;
      
    case 'disconnectWebSocket':
      wsManager.disconnect();
      sendResponse({ success: true });
      break;
      
    case 'apiRequest':
      handleApiRequest(message.endpoint, message.options)
        .then(result => sendResponse({ success: true, data: result }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    default:
      console.warn('ProScrape Extension: Unknown message action:', message.action);
      sendResponse({ success: false, error: 'Unknown action' });
  }
});

/**
 * Update extension settings
 */
async function updateSettings(newSettings) {
  try {
    // Merge with existing settings
    const currentSettings = await loadSettings();
    const updatedSettings = { ...currentSettings, ...newSettings };
    
    // Save to storage
    await chrome.storage.sync.set(updatedSettings);
    
    // Update extension state
    extensionState.settings = updatedSettings;
    
    // Update API configuration if needed
    if (newSettings.apiUrl && newSettings.apiUrl !== API_CONFIG.baseURL) {
      API_CONFIG.baseURL = newSettings.apiUrl;
      console.log('ProScrape Extension: Updated API URL to', newSettings.apiUrl);
      
      // Trigger health check with new URL
      await startHealthMonitoring();
    }
    
    console.log('ProScrape Extension: Settings updated successfully');
  } catch (error) {
    console.error('ProScrape Extension: Failed to update settings:', error);
    throw error;
  }
}

/**
 * Handle API requests from popup/content scripts
 */
async function handleApiRequest(endpoint, options = {}) {
  try {
    const url = `${API_CONFIG.baseURL}${endpoint}`;
    const config = {
      ...API_CONFIG,
      ...options,
      headers: {
        ...API_CONFIG.headers,
        ...options.headers,
      },
    };

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
    console.error(`ProScrape Extension: API request to ${endpoint} failed:`, error);
    throw error;
  }
}

/**
 * Handle WebSocket events
 */
wsManager.subscribe('new_listing', (data) => {
  console.log('ProScrape Extension: New listing received:', data);
  
  if (extensionState.settings?.enableNotifications) {
    showNotification(
      'New Property Listing',
      `${data.data?.title || 'New listing'} - ${data.data?.price || 'Price unknown'}`
    );
  }
});

wsManager.subscribe('pong', (data) => {
  console.log('ProScrape Extension: WebSocket heartbeat received');
  extensionState.isConnected = true;
});

/**
 * Handle external connections (from frontend)
 */
chrome.runtime.onConnectExternal.addListener((port) => {
  console.log('ProScrape Extension: External connection established');
  
  port.onMessage.addListener(async (message) => {
    switch (message.action) {
      case 'getListings':
        try {
          const listings = await handleApiRequest(ENDPOINTS.listings, message.params);
          port.postMessage({ success: true, data: listings });
        } catch (error) {
          port.postMessage({ success: false, error: error.message });
        }
        break;
        
      case 'searchListings':
        try {
          const results = await handleApiRequest(ENDPOINTS.search, {
            method: 'GET',
            ...message.params
          });
          port.postMessage({ success: true, data: results });
        } catch (error) {
          port.postMessage({ success: false, error: error.message });
        }
        break;
        
      default:
        port.postMessage({ success: false, error: 'Unknown action' });
    }
  });
  
  port.onDisconnect.addListener(() => {
    console.log('ProScrape Extension: External connection disconnected');
  });
});

/**
 * Export functions for testing
 */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initializeExtension,
    startHealthMonitoring,
    updateSettings,
    handleApiRequest
  };
}

console.log('ProScrape Extension: Background script loaded');