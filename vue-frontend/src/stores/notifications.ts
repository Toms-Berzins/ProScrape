import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
  persistent?: boolean
  actions?: NotificationAction[]
  timestamp: number
}

export interface NotificationAction {
  label: string
  action: () => void
  variant?: 'primary' | 'secondary' | 'danger'
}

export const useNotificationStore = defineStore('notifications', () => {
  // === State ===
  const notifications = ref<Notification[]>([])
  
  // === Computed ===
  const hasNotifications = computed(() => notifications.value.length > 0)
  const unreadCount = computed(() => notifications.value.length)
  
  // === Actions ===
  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp: Date.now(),
      duration: notification.duration ?? 5000
    }
    
    notifications.value.unshift(newNotification)
    
    // Auto-remove non-persistent notifications
    if (!notification.persistent && newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, newNotification.duration)
    }
    
    return id
  }
  
  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }
  
  const clearAllNotifications = () => {
    notifications.value = []
  }
  
  // Convenience methods
  const success = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'success',
      title,
      message,
      ...options
    })
  }
  
  const error = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'error',
      title,
      message,
      persistent: true, // Errors are persistent by default
      ...options
    })
  }
  
  const warning = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'warning',
      title,
      message,
      ...options
    })
  }
  
  const info = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'info',
      title,
      message,
      ...options
    })
  }
  
  return {
    // State
    notifications,
    
    // Computed
    hasNotifications,
    unreadCount,
    
    // Actions
    addNotification,
    removeNotification,
    clearAllNotifications,
    success,
    error,
    warning,
    info
  }
})

export type NotificationStore = ReturnType<typeof useNotificationStore>