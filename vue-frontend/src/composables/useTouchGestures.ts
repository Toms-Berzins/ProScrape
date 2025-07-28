import { ref, computed } from 'vue'

export interface TouchGestureOptions {
  threshold?: number
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  onSwipeUp?: () => void
  onSwipeDown?: () => void
  onSwipeProgress?: (progress: number, direction: string) => void
  onSwipeEnd?: () => void
  onPinch?: (scale: number) => void
  onRotate?: (angle: number) => void
  enablePinch?: boolean
  enableRotation?: boolean
  preventDefault?: boolean
}

export interface TouchState {
  startX: number
  startY: number
  startTime: number
  currentX: number
  currentY: number
  deltaX: number
  deltaY: number
  distance: number
  angle: number
  velocity: number
  isActive: boolean
  touchCount: number
}

/**
 * Advanced touch gesture composable for mobile interactions
 * Supports swipe, pinch, and rotation gestures with performance optimizations
 */
export function useTouchGestures(options: TouchGestureOptions = {}) {
  const {
    threshold = 50,
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onSwipeDown,
    onSwipeProgress,
    onSwipeEnd,
    onPinch,
    onRotate,
    enablePinch = false,
    enableRotation = false,
    preventDefault = true
  } = options

  // Touch state
  const touchState = ref<TouchState>({
    startX: 0,
    startY: 0,
    startTime: 0,
    currentX: 0,
    currentY: 0,
    deltaX: 0,
    deltaY: 0,
    distance: 0,
    angle: 0,
    velocity: 0,
    isActive: false,
    touchCount: 0
  })

  // Multi-touch state for pinch and rotate
  const multiTouchState = ref({
    initialDistance: 0,
    initialAngle: 0,
    currentDistance: 0,
    currentAngle: 0,
    scale: 1,
    rotation: 0,
    center: { x: 0, y: 0 }
  })

  // Computed properties
  const swipeDirection = computed(() => {
    const { deltaX, deltaY } = touchState.value
    const absDeltaX = Math.abs(deltaX)
    const absDeltaY = Math.abs(deltaY)

    if (absDeltaX > absDeltaY) {
      return deltaX > 0 ? 'right' : 'left'
    } else {
      return deltaY > 0 ? 'down' : 'up'
    }
  })

  const swipeProgress = computed(() => {
    const { deltaX, deltaY } = touchState.value
    const direction = swipeDirection.value

    switch (direction) {
      case 'left':
        return Math.min(0, deltaX)
      case 'right':
        return Math.max(0, deltaX)
      case 'up':
        return Math.min(0, deltaY)
      case 'down':
        return Math.max(0, deltaY)
      default:
        return 0
    }
  })

  const isSwipeThresholdMet = computed(() => {
    return Math.abs(swipeProgress.value) >= threshold
  })

  // Utility functions
  const getTouchCoordinates = (event: TouchEvent) => {
    const touch = event.touches[0]
    return {
      x: touch.clientX,
      y: touch.clientY
    }
  }

  const getMultiTouchData = (event: TouchEvent) => {
    if (event.touches.length < 2) return null

    const touch1 = event.touches[0]
    const touch2 = event.touches[1]

    const deltaX = touch2.clientX - touch1.clientX
    const deltaY = touch2.clientY - touch1.clientY
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
    const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI)

    const center = {
      x: (touch1.clientX + touch2.clientX) / 2,
      y: (touch1.clientY + touch2.clientY) / 2
    }

    return { distance, angle, center }
  }

  const calculateVelocity = (distance: number, time: number) => {
    return time > 0 ? distance / time : 0
  }

  // Event handlers
  const onTouchStart = (event: TouchEvent) => {
    if (preventDefault) {
      event.preventDefault()
    }

    const { x, y } = getTouchCoordinates(event)
    const now = Date.now()

    touchState.value = {
      startX: x,
      startY: y,
      startTime: now,
      currentX: x,
      currentY: y,
      deltaX: 0,
      deltaY: 0,
      distance: 0,
      angle: 0,
      velocity: 0,
      isActive: true,
      touchCount: event.touches.length
    }

    // Handle multi-touch gestures
    if ((enablePinch || enableRotation) && event.touches.length === 2) {
      const multiTouch = getMultiTouchData(event)
      if (multiTouch) {
        multiTouchState.value.initialDistance = multiTouch.distance
        multiTouchState.value.initialAngle = multiTouch.angle
        multiTouchState.value.center = multiTouch.center
      }
    }
  }

  const onTouchMove = (event: TouchEvent) => {
    if (!touchState.value.isActive) return

    if (preventDefault) {
      event.preventDefault()
    }

    const { x, y } = getTouchCoordinates(event)
    const deltaX = x - touchState.value.startX
    const deltaY = y - touchState.value.startY
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
    const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI)

    touchState.value.currentX = x
    touchState.value.currentY = y
    touchState.value.deltaX = deltaX
    touchState.value.deltaY = deltaY
    touchState.value.distance = distance
    touchState.value.angle = angle
    touchState.value.touchCount = event.touches.length

    // Handle swipe progress callback
    if (onSwipeProgress && distance > 10) {
      onSwipeProgress(swipeProgress.value, swipeDirection.value)
    }

    // Handle multi-touch gestures
    if ((enablePinch || enableRotation) && event.touches.length === 2) {
      const multiTouch = getMultiTouchData(event)
      if (multiTouch) {
        multiTouchState.value.currentDistance = multiTouch.distance
        multiTouchState.value.currentAngle = multiTouch.angle
        multiTouchState.value.center = multiTouch.center

        if (enablePinch) {
          const scale = multiTouch.distance / multiTouchState.value.initialDistance
          multiTouchState.value.scale = scale
          onPinch?.(scale)
        }

        if (enableRotation) {
          const rotation = multiTouch.angle - multiTouchState.value.initialAngle
          multiTouchState.value.rotation = rotation
          onRotate?.(rotation)
        }
      }
    }
  }

  const onTouchEnd = (event: TouchEvent) => {
    if (!touchState.value.isActive) return

    if (preventDefault) {
      event.preventDefault()
    }

    const now = Date.now()
    const timeDelta = now - touchState.value.startTime
    const velocity = calculateVelocity(touchState.value.distance, timeDelta)

    touchState.value.velocity = velocity

    // Determine if swipe threshold was met
    if (isSwipeThresholdMet.value || velocity > 0.5) {
      const direction = swipeDirection.value

      switch (direction) {
        case 'left':
          onSwipeLeft?.()
          break
        case 'right':
          onSwipeRight?.()
          break
        case 'up':
          onSwipeUp?.()
          break
        case 'down':
          onSwipeDown?.()
          break
      }
    }

    // Call end callback
    onSwipeEnd?.()

    // Reset state
    touchState.value.isActive = false
    multiTouchState.value = {
      initialDistance: 0,
      initialAngle: 0,
      currentDistance: 0,
      currentAngle: 0,
      scale: 1,
      rotation: 0,
      center: { x: 0, y: 0 }
    }
  }

  const onTouchCancel = (event: TouchEvent) => {
    touchState.value.isActive = false
    onSwipeEnd?.()
  }

  // Advanced gesture recognition
  const recognizeGesture = () => {
    const { deltaX, deltaY, velocity, distance } = touchState.value

    // Swipe detection
    if (distance > threshold) {
      const absDeltaX = Math.abs(deltaX)
      const absDeltaY = Math.abs(deltaY)

      if (absDeltaX > absDeltaY) {
        return deltaX > 0 ? 'swipe-right' : 'swipe-left'
      } else {
        return deltaY > 0 ? 'swipe-down' : 'swipe-up'
      }
    }

    // Fast swipe (flick) detection
    if (velocity > 1.0 && distance > 20) {
      return 'flick'
    }

    // Tap detection
    if (distance < 10 && velocity < 0.3) {
      return 'tap'
    }

    return 'unknown'
  }

  // Haptic feedback integration
  const triggerHapticFeedback = (type: 'light' | 'medium' | 'heavy' = 'light') => {
    if ('vibrate' in navigator) {
      const patterns = {
        light: [10],
        medium: [20],
        heavy: [30, 10, 30]
      }
      navigator.vibrate(patterns[type])
    }
  }

  // Performance optimization: throttled touch move
  let touchMoveThrottled = false
  const throttledTouchMove = (event: TouchEvent) => {
    if (touchMoveThrottled) return
    
    touchMoveThrottled = true
    requestAnimationFrame(() => {
      onTouchMove(event)
      touchMoveThrottled = false
    })
  }

  return {
    // State
    touchState: touchState.value,
    multiTouchState: multiTouchState.value,
    
    // Computed
    swipeDirection,
    swipeProgress,
    isSwipeThresholdMet,
    
    // Event handlers
    onTouchStart,
    onTouchMove: throttledTouchMove,
    onTouchEnd,
    onTouchCancel,
    
    // Utilities
    recognizeGesture,
    triggerHapticFeedback,
    
    // Raw event handlers (for direct use)
    handleTouchStart: onTouchStart,
    handleTouchMove: onTouchMove,
    handleTouchEnd: onTouchEnd
  }
}

/**
 * Simplified swipe-only composable for basic use cases
 */
export function useSwipeGestures(options: {
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  onSwipeUp?: () => void
  onSwipeDown?: () => void
  threshold?: number
}) {
  return useTouchGestures({
    ...options,
    enablePinch: false,
    enableRotation: false
  })
}

/**
 * Pinch-to-zoom composable
 */
export function usePinchGesture(options: {
  onPinch: (scale: number) => void
  onPinchStart?: () => void
  onPinchEnd?: () => void
}) {
  const { onPinch, onPinchStart, onPinchEnd } = options

  return useTouchGestures({
    enablePinch: true,
    onPinch: (scale) => {
      if (scale !== 1) {
        onPinch(scale)
      }
    },
    onTouchStart: onPinchStart,
    onSwipeEnd: onPinchEnd
  })
}

export type { TouchGestureOptions, TouchState }