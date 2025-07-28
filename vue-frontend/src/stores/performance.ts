import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface PerformanceMetric {
  name: string
  value: number
  timestamp: number
  type: 'timing' | 'counter' | 'gauge'
}

interface ErrorMetric {
  type: string
  message: string
  timestamp: number
  stack?: string
}

export const usePerformanceStore = defineStore('performance', () => {
  // === State ===
  const metrics = ref<PerformanceMetric[]>([])
  const errors = ref<ErrorMetric[]>([])
  const isMonitoring = ref(true)
  const maxMetrics = ref(1000) // Keep last 1000 metrics
  const maxErrors = ref(100) // Keep last 100 errors

  // === Computed ===
  const averageApiResponse = computed(() => {
    const apiMetrics = metrics.value
      .filter(m => m.name.includes('api') && m.type === 'timing')
      .slice(-20) // Last 20 API calls
    
    if (apiMetrics.length === 0) return 0
    
    return Math.round(
      apiMetrics.reduce((sum, m) => sum + m.value, 0) / apiMetrics.length
    )
  })

  const errorRate = computed(() => {
    const recentErrors = errors.value.filter(
      e => Date.now() - e.timestamp < 60000 // Last minute
    )
    const recentMetrics = metrics.value.filter(
      m => m.name.includes('api') && Date.now() - m.timestamp < 60000
    )
    
    if (recentMetrics.length === 0) return 0
    
    return (recentErrors.length / recentMetrics.length) * 100
  })

  const coreWebVitals = computed(() => {
    const lcp = metrics.value
      .filter(m => m.name === 'largest_contentful_paint')
      .slice(-1)[0]?.value || 0
    
    const fid = metrics.value
      .filter(m => m.name === 'first_input_delay')
      .slice(-1)[0]?.value || 0
    
    const cls = metrics.value
      .filter(m => m.name === 'cumulative_layout_shift')
      .slice(-1)[0]?.value || 0

    return {
      lcp: {
        value: lcp,
        score: lcp < 2500 ? 'good' : lcp < 4000 ? 'needs_improvement' : 'poor'
      },
      fid: {
        value: fid,
        score: fid < 100 ? 'good' : fid < 300 ? 'needs_improvement' : 'poor'
      },
      cls: {
        value: cls,
        score: cls < 0.1 ? 'good' : cls < 0.25 ? 'needs_improvement' : 'poor'
      }
    }
  })

  // === Actions ===
  const recordMetric = (name: string, value: number, type: 'timing' | 'counter' | 'gauge' = 'timing') => {
    if (!isMonitoring.value) return

    metrics.value.push({
      name,
      value,
      timestamp: Date.now(),
      type
    })

    // Cleanup old metrics
    if (metrics.value.length > maxMetrics.value) {
      metrics.value = metrics.value.slice(-maxMetrics.value)
    }
  }

  const recordError = (type: string, message: string, stack?: string) => {
    errors.value.push({
      type,
      message,
      timestamp: Date.now(),
      stack
    })

    // Cleanup old errors
    if (errors.value.length > maxErrors.value) {
      errors.value = errors.value.slice(-maxErrors.value)
    }

    // Send to external monitoring service if configured
    if (import.meta.env.VITE_SENTRY_DSN) {
      // Integration with Sentry or other error tracking
      console.error(`[${type}] ${message}`, stack)
    }
  }

  const measureFunction = async <T>(name: string, fn: () => Promise<T>): Promise<T> => {
    const startTime = performance.now()
    try {
      const result = await fn()
      recordMetric(name, performance.now() - startTime)
      return result
    } catch (error: any) {
      recordError(`${name}_error`, error.message, error.stack)
      throw error
    }
  }

  const initializeWebVitalsMonitoring = () => {
    if (typeof window === 'undefined') return

    // Largest Contentful Paint
    new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const lastEntry = entries[entries.length - 1]
      recordMetric('largest_contentful_paint', lastEntry.startTime)
    }).observe({ entryTypes: ['largest-contentful-paint'] })

    // First Input Delay
    new PerformanceObserver((list) => {
      list.getEntries().forEach((entry: any) => {
        recordMetric('first_input_delay', entry.processingStart - entry.startTime)
      })
    }).observe({ entryTypes: ['first-input'] })

    // Cumulative Layout Shift
    let clsValue = 0
    new PerformanceObserver((list) => {
      list.getEntries().forEach((entry: any) => {
        if (!entry.hadRecentInput) {
          clsValue += entry.value
          recordMetric('cumulative_layout_shift', clsValue)
        }
      })
    }).observe({ entryTypes: ['layout-shift'] })

    // Navigation timing
    window.addEventListener('load', () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      
      recordMetric('time_to_first_byte', navigation.responseStart - navigation.requestStart)
      recordMetric('dom_content_loaded', navigation.domContentLoadedEventEnd - navigation.navigationStart)
      recordMetric('load_complete', navigation.loadEventEnd - navigation.navigationStart)
    })
  }

  const getPerformanceReport = () => {
    const now = Date.now()
    const last5Minutes = now - 5 * 60 * 1000

    const recentMetrics = metrics.value.filter(m => m.timestamp > last5Minutes)
    const recentErrors = errors.value.filter(e => e.timestamp > last5Minutes)

    const apiMetrics = recentMetrics.filter(m => m.name.includes('api'))
    const renderMetrics = recentMetrics.filter(m => m.name.includes('render'))

    return {
      timestamp: now,
      metrics: {
        api: {
          count: apiMetrics.length,
          averageTime: apiMetrics.length > 0 
            ? Math.round(apiMetrics.reduce((sum, m) => sum + m.value, 0) / apiMetrics.length)
            : 0,
          slowest: apiMetrics.length > 0 
            ? Math.max(...apiMetrics.map(m => m.value))
            : 0
        },
        rendering: {
          count: renderMetrics.length,
          averageTime: renderMetrics.length > 0
            ? Math.round(renderMetrics.reduce((sum, m) => sum + m.value, 0) / renderMetrics.length)
            : 0
        },
        errors: {
          count: recentErrors.length,
          types: [...new Set(recentErrors.map(e => e.type))]
        }
      },
      webVitals: coreWebVitals.value
    }
  }

  const clearMetrics = () => {
    metrics.value = []
    errors.value = []
  }

  const toggleMonitoring = () => {
    isMonitoring.value = !isMonitoring.value
  }

  // Initialize monitoring on store creation
  if (typeof window !== 'undefined') {
    initializeWebVitalsMonitoring()
  }

  return {
    // State
    metrics,
    errors,
    isMonitoring,
    
    // Computed
    averageApiResponse,
    errorRate,
    coreWebVitals,
    
    // Actions
    recordMetric,
    recordError,
    measureFunction,
    getPerformanceReport,
    clearMetrics,
    toggleMonitoring
  }
})

export type PerformanceStore = ReturnType<typeof usePerformanceStore>