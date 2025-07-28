import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // State
  const isGlobalLoading = ref(false)
  const isOnline = ref(true)
  const sidebarOpen = ref(false)
  const notifications = ref<Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
    timestamp: Date
    persistent?: boolean
  }>>([])

  // Getters
  const hasNotifications = computed(() => notifications.value.length > 0)
  const unreadNotifications = computed(() => 
    notifications.value.filter(n => !n.persistent)
  )

  // Actions
  const setGlobalLoading = (loading: boolean) => {
    isGlobalLoading.value = loading
  }

  const setConnectionStatus = (online: boolean) => {
    isOnline.value = online
  }

  const toggleSidebar = () => {
    sidebarOpen.value = !sidebarOpen.value
  }

  const closeSidebar = () => {
    sidebarOpen.value = false
  }

  const openSidebar = () => {
    sidebarOpen.value = true
  }

  const addNotification = (notification: Omit<typeof notifications.value[0], 'id' | 'timestamp'>) => {
    const id = Date.now().toString()
    notifications.value.push({
      id,
      timestamp: new Date(),
      ...notification
    })

    // Auto-remove non-persistent notifications after 5 seconds
    if (!notification.persistent) {
      setTimeout(() => {
        removeNotification(id)
      }, 5000)
    }

    return id
  }

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clearNotifications = () => {
    notifications.value = []
  }

  const showSuccess = (title: string, message?: string) => {
    return addNotification({
      type: 'success',
      title,
      message: message || ''
    })
  }

  const showError = (title: string, message?: string, persistent = false) => {
    return addNotification({
      type: 'error',
      title,
      message: message || '',
      persistent
    })
  }

  const showWarning = (title: string, message?: string) => {
    return addNotification({
      type: 'warning',
      title,
      message: message || ''
    })
  }

  const showInfo = (title: string, message?: string) => {
    return addNotification({
      type: 'info',
      title,
      message: message || ''
    })
  }

  return {
    // State
    isGlobalLoading,
    isOnline,
    sidebarOpen,
    notifications,

    // Getters
    hasNotifications,
    unreadNotifications,

    // Actions
    setGlobalLoading,
    setConnectionStatus,
    toggleSidebar,
    closeSidebar,
    openSidebar,
    addNotification,
    removeNotification,
    clearNotifications,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  }
})

export type AppStore = ReturnType<typeof useAppStore>