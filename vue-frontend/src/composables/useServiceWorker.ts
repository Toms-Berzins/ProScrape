import { ref, computed, onMounted } from 'vue'

export interface ServiceWorkerState {
  isSupported: boolean
  isRegistered: boolean
  isUpdateAvailable: boolean
  isOffline: boolean
  registration: ServiceWorkerRegistration | null
  worker: ServiceWorker | null
}

export interface CacheStrategy {
  name: string
  pattern: RegExp | string
  strategy: 'cache-first' | 'network-first' | 'stale-while-revalidate'
  maxAge?: number
  maxEntries?: number
}

/**
 * Service Worker composable for PWA functionality
 * Handles registration, updates, caching, and offline functionality
 */
export function useServiceWorker() {
  // State
  const state = ref<ServiceWorkerState>({
    isSupported: 'serviceWorker' in navigator,
    isRegistered: false,
    isUpdateAvailable: false,
    isOffline: !navigator.onLine,
    registration: null,
    worker: null
  })

  const updatePrompt = ref(false)
  const installPrompt = ref<BeforeInstallPromptEvent | null>(null)
  const isInstalled = ref(false)
  const isInstallable = ref(false)

  // Computed
  const canInstall = computed(() => 
    isInstallable.value && !isInstalled.value
  )

  const swStatus = computed(() => {
    if (!state.value.isSupported) return 'unsupported'
    if (state.value.isOffline) return 'offline'
    if (state.value.isUpdateAvailable) return 'update-available'
    if (state.value.isRegistered) return 'active'
    return 'inactive'
  })

  // Service Worker registration
  const register = async (swPath = '/sw.js') => {
    if (!state.value.isSupported) {
      console.warn('Service Workers are not supported')
      return null
    }

    try {
      const registration = await navigator.serviceWorker.register(swPath, {
        scope: '/',
        updateViaCache: 'none'
      })

      state.value.registration = registration
      state.value.isRegistered = true

      console.log('Service Worker registered:', registration)

      // Handle different SW states
      if (registration.installing) {
        console.log('Service Worker installing')
        trackInstalling(registration.installing)
      } else if (registration.waiting) {
        console.log('Service Worker waiting')
        state.value.isUpdateAvailable = true
      } else if (registration.active) {
        console.log('Service Worker active')
        state.value.worker = registration.active
      }

      // Listen for updates
      registration.addEventListener('updatefound', () => {
        console.log('Service Worker update found')
        const newWorker = registration.installing
        if (newWorker) {
          trackInstalling(newWorker)
        }
      })

      return registration
    } catch (error) {
      console.error('Service Worker registration failed:', error)
      return null
    }
  }

  // Track installing service worker
  const trackInstalling = (worker: ServiceWorker) => {
    worker.addEventListener('statechange', () => {
      if (worker.state === 'installed' && navigator.serviceWorker.controller) {
        console.log('New Service Worker installed, update available')
        state.value.isUpdateAvailable = true
        updatePrompt.value = true
      } else if (worker.state === 'activated') {
        console.log('Service Worker activated')
        state.value.worker = worker
        window.location.reload()
      }
    })
  }

  // Apply update
  const applyUpdate = async () => {
    if (!state.value.registration?.waiting) return false

    try {
      // Send message to waiting SW to skip waiting
      state.value.registration.waiting.postMessage({ type: 'SKIP_WAITING' })
      
      // Wait for the new SW to take control
      await new Promise((resolve) => {
        const handleControllerChange = () => {
          navigator.serviceWorker.removeEventListener('controllerchange', handleControllerChange)
          resolve(true)
        }
        navigator.serviceWorker.addEventListener('controllerchange', handleControllerChange)
      })

      updatePrompt.value = false
      state.value.isUpdateAvailable = false
      
      // Reload page to use new SW
      window.location.reload()
      return true
    } catch (error) {
      console.error('Failed to apply update:', error)
      return false
    }
  }

  // Skip update
  const skipUpdate = () => {
    updatePrompt.value = false
  }

  // PWA Installation
  const handleInstallPrompt = (event: BeforeInstallPromptEvent) => {
    event.preventDefault()
    installPrompt.value = event
    isInstallable.value = true
  }

  const installPWA = async () => {
    if (!installPrompt.value) return false

    try {
      const result = await installPrompt.value.prompt()
      console.log('PWA install prompt result:', result.outcome)
      
      if (result.outcome === 'accepted') {
        isInstalled.value = true
        isInstallable.value = false
        installPrompt.value = null
        return true
      }
      return false
    } catch (error) {
      console.error('PWA installation failed:', error)
      return false
    }
  }

  // Cache management
  const clearCache = async (cacheName?: string) => {
    if (!('caches' in window)) return false

    try {
      if (cacheName) {
        const deleted = await caches.delete(cacheName)
        console.log(`Cache ${cacheName} ${deleted ? 'deleted' : 'not found'}`)
        return deleted
      } else {
        const cacheNames = await caches.keys()
        const deletePromises = cacheNames.map(name => caches.delete(name))
        await Promise.all(deletePromises)
        console.log('All caches cleared')
        return true
      }
    } catch (error) {
      console.error('Failed to clear cache:', error)
      return false
    }
  }

  const getCacheSize = async () => {
    if (!('caches' in window)) return 0

    try {
      const cacheNames = await caches.keys()
      let totalSize = 0

      for (const cacheName of cacheNames) {
        const cache = await caches.open(cacheName)
        const requests = await cache.keys()
        
        for (const request of requests) {
          const response = await cache.match(request)
          if (response) {
            const blob = await response.blob()
            totalSize += blob.size
          }
        }
      }

      return totalSize
    } catch (error) {
      console.error('Failed to calculate cache size:', error)
      return 0
    }
  }

  const preloadRoutes = async (routes: string[]) => {
    if (!('caches' in window) || !state.value.isRegistered) return

    try {
      const cache = await caches.open('proscrape-routes-v1')
      const requests = routes.map(route => new Request(route))
      
      await Promise.all(
        requests.map(async (request) => {
          try {
            const response = await fetch(request)
            if (response.ok) {
              await cache.put(request, response)
            }
          } catch (error) {
            console.warn(`Failed to preload route: ${request.url}`, error)
          }
        })
      )

      console.log(`Preloaded ${routes.length} routes`)
    } catch (error) {
      console.error('Failed to preload routes:', error)
    }
  }

  // Background sync
  const requestBackgroundSync = (tag: string) => {
    if (!state.value.registration?.sync) {
      console.warn('Background Sync not supported')
      return false
    }

    return state.value.registration.sync.register(tag)
      .then(() => {
        console.log(`Background sync registered: ${tag}`)
        return true
      })
      .catch((error) => {
        console.error('Background sync registration failed:', error)
        return false
      })
  }

  // Push notifications
  const requestNotificationPermission = async () => {
    if (!('Notification' in window)) {
      console.warn('Notifications not supported')
      return false
    }

    const permission = await Notification.requestPermission()
    return permission === 'granted'
  }

  const subscribeToPush = async () => {
    if (!state.value.registration) {
      console.error('Service Worker not registered')
      return null
    }

    try {
      const subscription = await state.value.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: import.meta.env.VITE_VAPID_PUBLIC_KEY
      })

      console.log('Push subscription created:', subscription)
      return subscription
    } catch (error) {
      console.error('Push subscription failed:', error)
      return null
    }
  }

  // Offline handling
  const handleOnlineStatus = () => {
    const updateOnlineStatus = () => {
      state.value.isOffline = !navigator.onLine
      console.log('Network status:', navigator.onLine ? 'online' : 'offline')
    }

    window.addEventListener('online', updateOnlineStatus)
    window.addEventListener('offline', updateOnlineStatus)

    return () => {
      window.removeEventListener('online', updateOnlineStatus)
      window.removeEventListener('offline', updateOnlineStatus)
    }
  }

  // Message handling
  const sendMessage = (message: any) => {
    if (!state.value.worker) return false

    state.value.worker.postMessage(message)
    return true
  }

  const onMessage = (callback: (event: MessageEvent) => void) => {
    navigator.serviceWorker.addEventListener('message', callback)
    
    return () => {
      navigator.serviceWorker.removeEventListener('message', callback)
    }
  }

  // Performance monitoring
  const getPerformanceMetrics = async () => {
    if (!state.value.registration) return null

    try {
      const cacheSize = await getCacheSize()
      const cacheNames = await caches.keys()
      
      return {
        cacheSize: Math.round(cacheSize / 1024 / 1024 * 100) / 100, // MB
        cacheCount: cacheNames.length,
        isRegistered: state.value.isRegistered,
        isUpdateAvailable: state.value.isUpdateAvailable,
        isOffline: state.value.isOffline,
        swScope: state.value.registration.scope,
        swState: state.value.worker?.state || 'unknown'
      }
    } catch (error) {
      console.error('Failed to get performance metrics:', error)
      return null
    }
  }

  // Auto-initialization
  onMounted(() => {
    // Handle install prompt
    window.addEventListener('beforeinstallprompt', handleInstallPrompt)
    
    // Handle app installed
    window.addEventListener('appinstalled', () => {
      console.log('PWA installed')
      isInstalled.value = true
      isInstallable.value = false
      installPrompt.value = null
    })

    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      isInstalled.value = true
    }

    // Handle online/offline status
    const cleanupOnlineHandler = handleOnlineStatus()

    // Auto-register service worker
    if (state.value.isSupported) {
      register()
    }

    // Cleanup
    return () => {
      cleanupOnlineHandler()
      window.removeEventListener('beforeinstallprompt', handleInstallPrompt)
    }
  })

  return {
    // State
    state,
    updatePrompt,
    installPrompt,
    isInstalled,
    isInstallable,
    
    // Computed
    canInstall,
    swStatus,
    
    // Methods
    register,
    applyUpdate,
    skipUpdate,
    installPWA,
    clearCache,
    getCacheSize,
    preloadRoutes,
    requestBackgroundSync,
    requestNotificationPermission,
    subscribeToPush,
    sendMessage,
    onMessage,
    getPerformanceMetrics
  }
}

// Global service worker instance
let globalSW: ReturnType<typeof useServiceWorker> | null = null

export function getServiceWorker() {
  if (!globalSW) {
    globalSW = useServiceWorker()
  }
  return globalSW
}

export default useServiceWorker