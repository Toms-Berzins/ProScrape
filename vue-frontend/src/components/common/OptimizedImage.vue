<template>
  <div 
    :class="containerClassName"
    :style="containerStyle"
  >
    <!-- Blur placeholder -->
    <div
      v-if="blurUp && !imageLoaded"
      class="absolute inset-0 bg-gray-200 animate-pulse"
      :style="blurPlaceholderStyle"
    />
    
    <!-- Main image -->
    <img
      ref="imageRef"
      :src="optimizedSrc"
      :alt="alt"
      :loading="loading"
      :decoding="critical ? 'sync' : 'async'"
      :fetchpriority="priority"
      :class="className"
      :style="imageStyle"
      @load="handleLoad"
      @error="handleError"
    />
    
    <!-- Loading indicator -->
    <div
      v-if="showLoadingIndicator && !imageLoaded && !imageError"
      class="absolute inset-0 flex items-center justify-center bg-gray-100"
    >
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-400" />
    </div>
    
    <!-- Error state -->
    <div
      v-if="imageError"
      class="absolute inset-0 flex items-center justify-center bg-gray-100 text-gray-400"
    >
      <div class="text-center">
        <PhotoIcon class="h-8 w-8 mx-auto mb-2" />
        <p class="text-sm">Image unavailable</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { PhotoIcon } from '@heroicons/vue/24/outline'

interface Props {
  src: string
  alt: string
  width?: number
  height?: number
  aspectRatio?: string
  quality?: number
  loading?: 'lazy' | 'eager'
  priority?: 'high' | 'low'
  critical?: boolean
  blurUp?: boolean
  progressive?: boolean
  sizes?: string
  className?: string
  containerClassName?: string
  showLoadingIndicator?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  quality: 80,
  loading: 'lazy',
  priority: 'low',
  critical: false,
  blurUp: true,
  progressive: true,
  showLoadingIndicator: true,
  className: '',
  containerClassName: 'relative overflow-hidden'
})

const emit = defineEmits<{
  load: [event: { loadTime: number; url: string }]
  error: [event: { error: Event; url: string }]
}>()

// State
const imageRef = ref<HTMLImageElement>()
const imageLoaded = ref(false)
const imageError = ref(false)
const loadStartTime = ref<number>(0)

// Computed
const optimizedSrc = computed(() => {
  // In a real implementation, this would integrate with an image CDN
  // like Cloudinary, ImageKit, or a custom image optimization service
  const baseUrl = props.src
  
  // For now, we'll simulate optimization by adding query parameters
  const url = new URL(baseUrl, window.location.origin)
  
  if (props.width) url.searchParams.set('w', props.width.toString())
  if (props.height) url.searchParams.set('h', props.height.toString())
  if (props.quality) url.searchParams.set('q', props.quality.toString())
  if (props.progressive) url.searchParams.set('fm', 'webp')
  
  return url.toString()
})

const containerStyle = computed(() => {
  const styles: Record<string, string> = {}
  
  if (props.aspectRatio) {
    const [width, height] = props.aspectRatio.split(':').map(Number)
    styles.aspectRatio = `${width} / ${height}`
  } else if (props.width && props.height) {
    styles.aspectRatio = `${props.width} / ${props.height}`
  }
  
  return styles
})

const imageStyle = computed(() => {
  const styles: Record<string, string> = {}
  
  if (!imageLoaded.value && !imageError.value) {
    styles.opacity = '0'
  } else {
    styles.opacity = '1'
    styles.transition = 'opacity 0.3s ease'
  }
  
  return styles
})

const blurPlaceholderStyle = computed(() => {
  if (!props.blurUp) return {}
  
  return {
    filter: 'blur(10px)',
    transform: 'scale(1.1)', // Slightly scale to hide blur edges
    transition: 'opacity 0.3s ease',
    opacity: imageLoaded.value ? '0' : '1'
  }
})

// Methods
const handleLoad = (event: Event) => {
  const loadTime = performance.now() - loadStartTime.value
  imageLoaded.value = true
  imageError.value = false
  
  emit('load', {
    loadTime,
    url: props.src
  })
  
  // Performance tracking
  if (props.critical) {
    // Track LCP candidate
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry) => {
        console.debug('LCP candidate:', entry)
      })
    })
    observer.observe({ entryTypes: ['largest-contentful-paint'] })
  }
}

const handleError = (event: Event) => {
  imageError.value = true
  imageLoaded.value = false
  
  emit('error', {
    error: event,
    url: props.src
  })
}

const preloadImage = () => {
  if (props.critical || props.priority === 'high') {
    const link = document.createElement('link')
    link.rel = 'preload'
    link.as = 'image'
    link.href = optimizedSrc.value
    if (props.sizes) {
      link.setAttribute('imagesizes', props.sizes)
    }
    document.head.appendChild(link)
  }
}

// Watchers
watch(() => props.src, () => {
  imageLoaded.value = false
  imageError.value = false
  loadStartTime.value = performance.now()
}, { immediate: true })

// Lifecycle
onMounted(() => {
  loadStartTime.value = performance.now()
  
  // Preload critical images
  if (props.critical) {
    preloadImage()
  }
  
  // Intersection Observer for lazy loading optimization
  if (props.loading === 'lazy' && imageRef.value) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Image is in viewport, prioritize loading
            loadStartTime.value = performance.now()
            observer.unobserve(entry.target)
          }
        })
      },
      { rootMargin: '50px' } // Start loading 50px before entering viewport
    )
    
    observer.observe(imageRef.value)
  }
})
</script>

<style scoped>
/* Prevent layout shift during image loading */
img {
  display: block;
  max-width: 100%;
  height: auto;
}

/* Smooth transitions */
.image-container {
  position: relative;
  overflow: hidden;
}

/* Performance optimizations */
img {
  will-change: opacity;
}

/* Responsive image sizing */
@media (max-width: 640px) {
  img {
    height: auto;
  }
}
</style>