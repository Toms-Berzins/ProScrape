import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useServiceWorker } from '@/composables/useServiceWorker'

export interface OfflineAction {
  id: string
  type: 'CREATE' | 'UPDATE' | 'DELETE'
  resource: string
  data: any
  timestamp: number
  retryCount: number
  maxRetries: number
  status: 'pending' | 'failed' | 'success'
  error?: string
}

export interface OfflineData {
  [key: string]: {
    data: any
    timestamp: number
    version: number
  }
}

export interface SyncStatus {
  isOnline: boolean
  isSyncing: boolean
  lastSync: number | null
  pendingActions: number
  failedActions: number
  syncErrors: string[]
}

/**
 * Offline-first store for handling data persistence and synchronization
 * Implements optimistic updates with conflict resolution
 */
export const useOfflineStore = defineStore('offline', () => {
  // === State ===
  const isOnline = ref(navigator.onLine)
  const isSyncing = ref(false)
  const lastSync = ref<number | null>(null)
  const syncInProgress = ref(false)
  
  // Offline data storage
  const offlineData = ref<OfflineData>({})
  const pendingActions = ref<OfflineAction[]>([])
  const failedActions = ref<OfflineAction[]>([])
  const syncErrors = ref<string[]>([])
  
  // Configuration
  const maxRetries = ref(3)
  const retryDelay = ref(1000) // ms
  const syncInterval = ref(30000) // 30 seconds
  const maxOfflineAge = ref(7 * 24 * 60 * 60 * 1000) // 7 days
  
  // Service Worker integration
  const { state: swState, sendMessage, onMessage } = useServiceWorker()

  // === Computed ===
  const syncStatus = computed<SyncStatus>(() => ({
    isOnline: isOnline.value,
    isSyncing: isSyncing.value,
    lastSync: lastSync.value,
    pendingActions: pendingActions.value.length,
    failedActions: failedActions.value.length,
    syncErrors: syncErrors.value
  }))

  const hasOfflineData = computed(() => Object.keys(offlineData.value).length > 0)
  const hasPendingActions = computed(() => pendingActions.value.length > 0)
  const hasFailedActions = computed(() => failedActions.value.length > 0)

  const offlineDataSize = computed(() => {
    const jsonString = JSON.stringify(offlineData.value)
    return new Blob([jsonString]).size
  })

  // === Actions ===
  
  /**
   * Store data for offline access
   */
  const storeOfflineData = (key: string, data: any, version = 1) => {
    offlineData.value[key] = {
      data,
      timestamp: Date.now(),
      version
    }
    
    // Persist to IndexedDB
    persistOfflineData(key, offlineData.value[key])
  }

  /**
   * Retrieve offline data
   */
  const getOfflineData = (key: string) => {
    const item = offlineData.value[key]
    if (!item) return null
    
    // Check if data is expired
    if (Date.now() - item.timestamp > maxOfflineAge.value) {
      delete offlineData.value[key]
      removePersistedData(key)
      return null
    }
    
    return item.data
  }

  /**
   * Queue an action for when online
   */
  const queueAction = (action: Omit<OfflineAction, 'id' | 'timestamp' | 'retryCount' | 'status'>) => {
    const queuedAction: OfflineAction = {
      ...action,
      id: generateActionId(),
      timestamp: Date.now(),
      retryCount: 0,
      status: 'pending'
    }
    
    pendingActions.value.push(queuedAction)
    persistPendingActions()
    
    // Try to sync immediately if online
    if (isOnline.value) {
      syncPendingActions()
    }
    
    return queuedAction.id
  }

  /**
   * Execute a single action
   */
  const executeAction = async (action: OfflineAction): Promise<boolean> => {
    try {
      // Mock API call - replace with actual API integration
      const response = await fetch(`/api/${action.resource}`, {
        method: getHttpMethod(action.type),
        headers: { 'Content-Type': 'application/json' },
        body: action.type !== 'DELETE' ? JSON.stringify(action.data) : undefined
      })

      if (response.ok) {
        action.status = 'success'
        return true
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
    } catch (error: any) {
      action.error = error.message
      action.retryCount++
      
      if (action.retryCount >= action.maxRetries) {
        action.status = 'failed'
        failedActions.value.push(action)
        syncErrors.value.push(`Action ${action.id} failed: ${error.message}`)
      }
      
      return false
    }
  }

  /**
   * Sync all pending actions
   */
  const syncPendingActions = async () => {
    if (!isOnline.value || isSyncing.value || pendingActions.value.length === 0) {
      return
    }

    isSyncing.value = true
    syncInProgress.value = true
    
    try {
      const actionsToSync = [...pendingActions.value]
      const syncResults: boolean[] = []
      
      for (const action of actionsToSync) {
        const success = await executeAction(action)
        syncResults.push(success)
        
        if (success) {
          // Remove from pending
          const index = pendingActions.value.findIndex(a => a.id === action.id)
          if (index > -1) {
            pendingActions.value.splice(index, 1)
          }
        }
        
        // Add delay between actions to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      
      // Update last sync time
      lastSync.value = Date.now()
      
      // Persist updated state
      persistPendingActions()
      persistFailedActions()
      
      console.log(`Sync completed: ${syncResults.filter(Boolean).length}/${syncResults.length} actions succeeded`)
      
    } catch (error: any) {
      console.error('Sync failed:', error)
      syncErrors.value.push(`Sync failed: ${error.message}`)
    } finally {
      isSyncing.value = false
      syncInProgress.value = false
    }
  }

  /**
   * Retry failed actions
   */
  const retryFailedActions = async () => {
    if (!isOnline.value || failedActions.value.length === 0) return

    const actionsToRetry = [...failedActions.value]
    failedActions.value = []
    
    // Reset retry count and status
    actionsToRetry.forEach(action => {
      action.retryCount = 0
      action.status = 'pending'
      delete action.error
    })
    
    // Add back to pending queue
    pendingActions.value.push(...actionsToRetry)
    
    // Try to sync
    await syncPendingActions()
  }

  /**
   * Clear offline data
   */
  const clearOfflineData = async (olderThan?: number) => {
    const cutoffTime = olderThan || Date.now() - maxOfflineAge.value
    
    Object.keys(offlineData.value).forEach(key => {
      const item = offlineData.value[key]
      if (item.timestamp < cutoffTime) {
        delete offlineData.value[key]
        removePersistedData(key)
      }
    })
  }

  /**
   * Clear all pending actions
   */
  const clearPendingActions = () => {
    pendingActions.value = []
    failedActions.value = []
    syncErrors.value = []
    persistPendingActions()
    persistFailedActions()
  }

  /**
   * Get conflict resolution strategy
   */
  const resolveConflict = (localData: any, serverData: any, strategy: 'server-wins' | 'client-wins' | 'merge' = 'server-wins') => {
    switch (strategy) {
      case 'client-wins':
        return localData
      case 'merge':
        return { ...serverData, ...localData }
      case 'server-wins':
      default:
        return serverData
    }
  }

  /**
   * Optimistic update with rollback capability
   */
  const optimisticUpdate = <T>(
    key: string,
    updateFn: (data: T) => T,
    apiCall: () => Promise<T>
  ) => {
    // Store original data for rollback
    const originalData = getOfflineData(key)
    
    try {
      // Apply optimistic update
      const currentData = originalData || {}
      const updatedData = updateFn(currentData as T)
      storeOfflineData(key, updatedData)
      
      // Queue API call
      apiCall()
        .then((serverData) => {
          // Update with server response
          storeOfflineData(key, serverData)
        })
        .catch((error) => {
          // Rollback on error
          if (originalData) {
            storeOfflineData(key, originalData.data)
          } else {
            delete offlineData.value[key]
          }
          throw error
        })
        
    } catch (error) {
      // Rollback on immediate error
      if (originalData) {
        storeOfflineData(key, originalData.data)
      }
      throw error
    }
  }

  // === Persistence Layer ===
  
  const persistOfflineData = async (key: string, data: any) => {
    try {
      if ('indexedDB' in window) {
        // Use IndexedDB for larger data
        await saveToIndexedDB('offlineData', key, data)
      } else {
        // Fallback to localStorage
        localStorage.setItem(`proscrape-offline-${key}`, JSON.stringify(data))
      }
    } catch (error) {
      console.warn('Failed to persist offline data:', error)
    }
  }

  const loadPersistedData = async () => {
    try {
      if ('indexedDB' in window) {
        const data = await loadFromIndexedDB('offlineData')
        if (data) {
          offlineData.value = data
        }
      } else {
        // Load from localStorage
        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('proscrape-offline-')) {
            const dataKey = key.replace('proscrape-offline-', '')
            const data = JSON.parse(localStorage.getItem(key) || '{}')
            offlineData.value[dataKey] = data
          }
        })
      }
    } catch (error) {
      console.warn('Failed to load persisted data:', error)
    }
  }

  const persistPendingActions = () => {
    try {
      localStorage.setItem('proscrape-pending-actions', JSON.stringify(pendingActions.value))
    } catch (error) {
      console.warn('Failed to persist pending actions:', error)
    }
  }

  const persistFailedActions = () => {
    try {
      localStorage.setItem('proscrape-failed-actions', JSON.stringify(failedActions.value))
    } catch (error) {
      console.warn('Failed to persist failed actions:', error)
    }
  }

  const loadPersistedActions = () => {
    try {
      const pending = localStorage.getItem('proscrape-pending-actions')
      if (pending) {
        pendingActions.value = JSON.parse(pending)
      }

      const failed = localStorage.getItem('proscrape-failed-actions')
      if (failed) {
        failedActions.value = JSON.parse(failed)
      }
    } catch (error) {
      console.warn('Failed to load persisted actions:', error)
    }
  }

  // === Utility Functions ===
  
  const generateActionId = () => {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  const getHttpMethod = (actionType: OfflineAction['type']) => {
    switch (actionType) {
      case 'CREATE': return 'POST'
      case 'UPDATE': return 'PUT'
      case 'DELETE': return 'DELETE'
      default: return 'GET'
    }
  }

  const removePersistedData = async (key: string) => {
    try {
      if ('indexedDB' in window) {
        await deleteFromIndexedDB('offlineData', key)
      } else {
        localStorage.removeItem(`proscrape-offline-${key}`)
      }
    } catch (error) {
      console.warn('Failed to remove persisted data:', error)
    }
  }

  // === IndexedDB Helpers ===
  
  const saveToIndexedDB = async (storeName: string, key: string, data: any) => {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ProScrapeOffline', 1)
      
      request.onerror = () => reject(request.error)
      
      request.onsuccess = () => {
        const db = request.result
        const transaction = db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const putRequest = store.put(data, key)
        
        putRequest.onsuccess = () => resolve(putRequest.result)
        putRequest.onerror = () => reject(putRequest.error)
      }
      
      request.onupgradeneeded = () => {
        const db = request.result
        if (!db.objectStoreNames.contains(storeName)) {
          db.createObjectStore(storeName)
        }
      }
    })
  }

  const loadFromIndexedDB = async (storeName: string) => {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ProScrapeOffline', 1)
      
      request.onerror = () => reject(request.error)
      
      request.onsuccess = () => {
        const db = request.result
        const transaction = db.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const getAllRequest = store.getAll()
        
        getAllRequest.onsuccess = () => {
          const result: Record<string, any> = {}
          const keys = store.getAllKeys()
          
          keys.onsuccess = () => {
            getAllRequest.result.forEach((value, index) => {
              result[keys.result[index] as string] = value
            })
            resolve(result)
          }
        }
        getAllRequest.onerror = () => reject(getAllRequest.error)
      }
    })
  }

  const deleteFromIndexedDB = async (storeName: string, key: string) => {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ProScrapeOffline', 1)
      
      request.onerror = () => reject(request.error)
      
      request.onsuccess = () => {
        const db = request.result
        const transaction = db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const deleteRequest = store.delete(key)
        
        deleteRequest.onsuccess = () => resolve(deleteRequest.result)
        deleteRequest.onerror = () => reject(deleteRequest.error)
      }
    })
  }

  // === Event Listeners ===
  
  const setupEventListeners = () => {
    // Online/offline status
    const handleOnline = () => {
      isOnline.value = true
      if (hasPendingActions.value) {
        syncPendingActions()
      }
    }
    
    const handleOffline = () => {
      isOnline.value = false
    }
    
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    
    // Service Worker messages
    const handleSWMessage = (event: MessageEvent) => {
      if (event.data.type === 'SYNC_REQUEST') {
        syncPendingActions()
      }
    }
    
    const unsubscribeSW = onMessage(handleSWMessage)
    
    // Periodic sync
    const syncIntervalId = setInterval(() => {
      if (isOnline.value && hasPendingActions.value) {
        syncPendingActions()
      }
    }, syncInterval.value)
    
    // Cleanup
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      unsubscribeSW()
      clearInterval(syncIntervalId)
    }
  }

  // === Watchers ===
  
  watch(
    () => pendingActions.value,
    () => {
      persistPendingActions()
    },
    { deep: true }
  )

  watch(
    () => failedActions.value,
    () => {
      persistFailedActions()
    },
    { deep: true }
  )

  // === Initialization ===
  
  const initialize = async () => {
    await loadPersistedData()
    loadPersistedActions()
    const cleanup = setupEventListeners()
    
    // Initial sync if online
    if (isOnline.value && hasPendingActions.value) {
      setTimeout(() => syncPendingActions(), 1000)
    }
    
    return cleanup
  }

  return {
    // State
    isOnline,
    isSyncing,
    lastSync,
    offlineData,
    pendingActions,
    failedActions,
    syncErrors,
    
    // Computed
    syncStatus,
    hasOfflineData,
    hasPendingActions,
    hasFailedActions,
    offlineDataSize,
    
    // Actions
    storeOfflineData,
    getOfflineData,
    queueAction,
    syncPendingActions,
    retryFailedActions,
    clearOfflineData,
    clearPendingActions,
    resolveConflict,
    optimisticUpdate,
    initialize
  }
})

export type OfflineStore = ReturnType<typeof useOfflineStore>