import { ref } from 'vue'

export interface HapticFeedbackOptions {
  enabled?: boolean
  patterns?: {
    light: number[]
    medium: number[]
    heavy: number[]
    success: number[]
    warning: number[]
    error: number[]
    custom?: Record<string, number[]>
  }
}

/**
 * Composable for haptic feedback on mobile devices
 * Provides standardized haptic patterns for different interaction types
 */
export function useHapticFeedback(options: HapticFeedbackOptions = {}) {
  const {
    enabled = true,
    patterns = {
      light: [10],
      medium: [20],
      heavy: [30],
      success: [10, 50, 10],
      warning: [20, 100, 20],
      error: [50, 50, 50, 50, 50],
      custom: {}
    }
  } = options

  // Check if haptic feedback is supported
  const isSupported = ref(
    typeof navigator !== 'undefined' && 
    'vibrate' in navigator
  )

  // Check if we're on iOS for Taptic Engine support
  const isIOS = ref(
    typeof navigator !== 'undefined' &&
    /iPad|iPhone|iPod/.test(navigator.userAgent)
  )

  // Modern devices support more sophisticated haptic feedback
  const hasAdvancedHaptics = ref(
    isIOS.value || 
    (typeof window !== 'undefined' && 'HapticFeedback' in window)
  )

  /**
   * Trigger haptic feedback with specified pattern
   */
  const triggerHaptic = (
    type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error' | string,
    force = false
  ) => {
    if (!enabled && !force) return
    if (!isSupported.value) return

    let pattern: number[]

    // Get pattern from predefined types or custom patterns
    if (type in patterns) {
      pattern = patterns[type as keyof typeof patterns] as number[]
    } else if (patterns.custom?.[type]) {
      pattern = patterns.custom[type]
    } else {
      console.warn(`Unknown haptic pattern: ${type}`)
      pattern = patterns.light
    }

    try {
      // Use modern Haptic API if available (iOS Safari)
      if (hasAdvancedHaptics.value && 'HapticFeedback' in window) {
        const hapticType = mapToHapticType(type)
        // @ts-ignore - HapticFeedback is not in TypeScript types yet
        window.HapticFeedback.impact(hapticType)
      } else {
        // Fallback to vibration API
        navigator.vibrate(pattern)
      }
    } catch (error) {
      console.warn('Haptic feedback failed:', error)
    }
  }

  /**
   * Map our haptic types to native iOS haptic types
   */
  const mapToHapticType = (type: string): string => {
    const mapping: Record<string, string> = {
      light: 'light',
      medium: 'medium',
      heavy: 'heavy',
      success: 'light',
      warning: 'medium',
      error: 'heavy'
    }
    return mapping[type] || 'light'
  }

  /**
   * Trigger contextual haptic feedback for UI interactions
   */
  const triggerSelectionHaptic = () => {
    if (isIOS.value) {
      triggerHaptic('light')
    } else {
      triggerHaptic('medium')
    }
  }

  const triggerImpactHaptic = (intensity: 'light' | 'medium' | 'heavy' = 'medium') => {
    triggerHaptic(intensity)
  }

  const triggerNotificationHaptic = (type: 'success' | 'warning' | 'error') => {
    triggerHaptic(type)
  }

  /**
   * Custom haptic patterns for specific interactions
   */
  const hapticPatterns = {
    // UI Interactions
    buttonTap: () => triggerHaptic('light'),
    buttonHold: () => triggerHaptic('medium'),
    swipeSuccess: () => triggerHaptic('success'),
    swipeCancel: () => triggerHaptic('light'),
    
    // Navigation
    pageTransition: () => triggerHaptic('light'),
    tabSwitch: () => triggerHaptic('light'),
    modalOpen: () => triggerHaptic('medium'),
    modalClose: () => triggerHaptic('light'),
    
    // Content Interactions
    itemSelect: () => triggerHaptic('light'),
    itemDeselect: () => triggerHaptic('light'),
    itemDelete: () => triggerHaptic('warning'),
    itemFavorite: () => triggerHaptic('success'),
    itemUnfavorite: () => triggerHaptic('light'),
    
    // Form Interactions
    inputFocus: () => triggerHaptic('light'),
    inputError: () => triggerHaptic('error'),
    formSubmitSuccess: () => triggerHaptic('success'),
    formSubmitError: () => triggerHaptic('error'),
    
    // Gestures
    pullToRefresh: () => triggerHaptic('medium'),
    longPress: () => triggerHaptic('heavy'),
    dragStart: () => triggerHaptic('light'),
    dragEnd: () => triggerHaptic('light'),
    
    // Media
    photoCapture: () => triggerHaptic('medium'),
    videoStart: () => triggerHaptic('light'),
    videoStop: () => triggerHaptic('light'),
    
    // Notifications
    messageReceived: () => triggerHaptic('light'),
    callIncoming: () => triggerHaptic('heavy'),
    alertCritical: () => triggerHaptic('error')
  }

  /**
   * Enable/disable haptic feedback
   */
  const enable = () => {
    // @ts-ignore
    enabled = true
  }

  const disable = () => {
    // @ts-ignore
    enabled = false
  }

  /**
   * Test haptic feedback with different patterns
   */
  const testHaptics = async () => {
    if (!isSupported.value) {
      console.log('Haptic feedback not supported')
      return
    }

    console.log('Testing haptic patterns...')
    
    const testPatterns = ['light', 'medium', 'heavy', 'success', 'warning', 'error']
    
    for (const pattern of testPatterns) {
      console.log(`Testing ${pattern} haptic`)
      triggerHaptic(pattern)
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
  }

  /**
   * Register custom haptic pattern
   */
  const registerCustomPattern = (name: string, pattern: number[]) => {
    if (!patterns.custom) {
      patterns.custom = {}
    }
    patterns.custom[name] = pattern
  }

  /**
   * Get device haptic capabilities
   */
  const getCapabilities = () => {
    return {
      isSupported: isSupported.value,
      isIOS: isIOS.value,
      hasAdvancedHaptics: hasAdvancedHaptics.value,
      supportsCustomPatterns: !isIOS.value, // iOS uses predefined patterns
      availablePatterns: Object.keys(patterns)
    }
  }

  return {
    // Core functions
    triggerHaptic,
    triggerSelectionHaptic,
    triggerImpactHaptic,
    triggerNotificationHaptic,
    
    // Contextual patterns
    hapticPatterns,
    
    // Utility functions
    enable,
    disable,
    testHaptics,
    registerCustomPattern,
    getCapabilities,
    
    // State
    isSupported,
    isIOS,
    hasAdvancedHaptics
  }
}

/**
 * Simplified haptic composable for basic interactions
 */
export function useSimpleHaptics() {
  const { triggerHaptic, hapticPatterns, isSupported } = useHapticFeedback()
  
  return {
    // Simple triggers
    light: () => triggerHaptic('light'),
    medium: () => triggerHaptic('medium'),
    heavy: () => triggerHaptic('heavy'),
    success: () => triggerHaptic('success'),
    error: () => triggerHaptic('error'),
    
    // Common patterns
    tap: hapticPatterns.buttonTap,
    select: hapticPatterns.itemSelect,
    favorite: hapticPatterns.itemFavorite,
    delete: hapticPatterns.itemDelete,
    
    // State
    isSupported
  }
}

/**
 * Vue directive for haptic feedback
 * Usage: v-haptic="'light'" or v-haptic="{ type: 'medium', event: 'mousedown' }"
 */
export const vHaptic = {
  mounted(el: HTMLElement, binding: any) {
    const { triggerHaptic } = useHapticFeedback()
    
    const config = typeof binding.value === 'string' 
      ? { type: binding.value, event: 'click' }
      : { type: 'light', event: 'click', ...binding.value }
    
    const handler = () => {
      triggerHaptic(config.type)
    }
    
    el.addEventListener(config.event, handler)
    
    // Store handler for cleanup
    // @ts-ignore
    el._hapticHandler = handler
    // @ts-ignore
    el._hapticEvent = config.event
  },
  
  unmounted(el: HTMLElement) {
    // @ts-ignore
    if (el._hapticHandler && el._hapticEvent) {
      // @ts-ignore
      el.removeEventListener(el._hapticEvent, el._hapticHandler)
    }
  }
}

export default useHapticFeedback