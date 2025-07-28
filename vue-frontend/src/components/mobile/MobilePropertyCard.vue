<template>
  <article 
    class="mobile-property-card bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden touch-manipulation"
    :class="{
      'mobile-property-card--swiped': swipeState.swiped,
      'mobile-property-card--favorited': isFavorited
    }"
    :style="swipeStyle"
    @touchstart="handleTouchStart"
    @touchmove="handleTouchMove"
    @touchend="handleTouchEnd"
    @click="handleCardClick"
  >
    <!-- Image Container with Swipe Gallery -->
    <div class="relative">
      <!-- Image Slider -->
      <div 
        class="image-slider overflow-hidden rounded-t-lg"
        :style="{ height: imageHeight + 'px' }"
      >
        <div 
          class="flex transition-transform duration-300 ease-out"
          :style="{ 
            transform: `translateX(-${currentImageIndex * 100}%)`,
            width: `${property.image_urls.length * 100}%`
          }"
        >
          <div
            v-for="(imageUrl, index) in property.image_urls"
            :key="index"
            class="w-full flex-shrink-0 relative"
          >
            <OptimizedImage
              :src="imageUrl"
              :alt="`${property.title} - Image ${index + 1}`"
              :loading="index === 0 ? 'eager' : 'lazy'"
              :priority="index === 0 ? 'high' : 'low'"
              :critical="index === 0 && critical"
              aspect-ratio="4:3"
              :quality="index === 0 ? 90 : 75"
              class="w-full h-full object-cover"
              @load="handleImageLoad"
              @error="handleImageError"
            />
            
            <!-- Image Loading Skeleton -->
            <div 
              v-if="!imagesLoaded[index]"
              class="absolute inset-0 bg-gray-200 animate-pulse flex items-center justify-center"
            >
              <PhotoIcon class="h-8 w-8 text-gray-400" />
            </div>
          </div>
        </div>
        
        <!-- No Image Placeholder -->
        <div 
          v-if="!property.image_urls.length"
          class="w-full h-full bg-gray-200 flex items-center justify-center"
        >
          <div class="text-center text-gray-400">
            <PhotoIcon class="h-12 w-12 mx-auto mb-2" />
            <p class="text-sm">No images available</p>
          </div>
        </div>
      </div>
      
      <!-- Image Navigation Dots -->
      <div 
        v-if="property.image_urls.length > 1"
        class="absolute bottom-2 left-1/2 transform -translate-x-1/2 flex space-x-1"
      >
        <button
          v-for="(_, index) in property.image_urls"
          :key="index"
          @click.stop="setCurrentImage(index)"
          class="w-2 h-2 rounded-full transition-colors"
          :class="index === currentImageIndex ? 'bg-white' : 'bg-white bg-opacity-50'"
        />
      </div>
      
      <!-- Overlay Actions -->
      <div class="absolute top-2 left-2 right-2 flex justify-between items-start">
        <!-- Source Badge -->
        <div class="bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded-full">
          {{ property.source_site }}
        </div>
        
        <!-- Action Buttons -->
        <div class="flex space-x-2">
          <!-- Favorite Button -->
          <button
            @click.stop="toggleFavorite"
            class="p-2 bg-black bg-opacity-50 rounded-full transition-colors"
            :class="{ 'text-red-500': isFavorited, 'text-white': !isFavorited }"
          >
            <HeartIcon 
              class="h-5 w-5" 
              :class="{ 'fill-current': isFavorited }"
            />
          </button>
          
          <!-- Share Button -->
          <button
            @click.stop="handleShare"
            class="p-2 bg-black bg-opacity-50 text-white rounded-full hover:bg-opacity-70 transition-opacity"
          >
            <ShareIcon class="h-5 w-5" />
          </button>
        </div>
      </div>
      
      <!-- New Listing Badge -->
      <div 
        v-if="isNew"
        class="absolute top-2 left-1/2 transform -translate-x-1/2 bg-green-500 text-white text-xs px-3 py-1 rounded-full font-medium"
      >
        NEW
      </div>
      
      <!-- Price Change Indicator -->
      <div 
        v-if="priceChange"
        class="absolute bottom-2 right-2 flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium"
        :class="priceChange.isIncrease 
          ? 'bg-red-100 text-red-800' 
          : 'bg-green-100 text-green-800'"
      >
        <component 
          :is="priceChange.isIncrease ? ChevronUpIcon : ChevronDownIcon" 
          class="h-3 w-3" 
        />
        <span>{{ priceChange.percentage }}%</span>
      </div>
    </div>
    
    <!-- Property Content -->
    <div class="p-4 space-y-3">
      <!-- Price -->
      <div class="flex items-center justify-between">
        <div class="text-xl font-bold text-blue-600">
          {{ formatPrice(property.price) }}
          <span v-if="property.listing_type === 'rent'" class="text-sm text-gray-500 font-normal">
            /month
          </span>
        </div>
        <div v-if="property.price_per_sqm" class="text-sm text-gray-500">
          €{{ property.price_per_sqm }}/m²
        </div>
      </div>
      
      <!-- Title -->
      <h3 class="font-semibold text-gray-900 leading-tight line-clamp-2">
        {{ property.title }}
      </h3>
      
      <!-- Key Details Grid -->
      <div class="grid grid-cols-2 gap-2 text-sm text-gray-600">
        <div v-if="property.property_type_localized" class="flex items-center">
          <HomeIcon class="h-4 w-4 mr-1 text-gray-400" />
          <span class="truncate">{{ property.property_type_localized }}</span>
        </div>
        
        <div v-if="property.area_formatted" class="flex items-center">
          <ScaleIcon class="h-4 w-4 mr-1 text-gray-400" />
          <span>{{ property.area_formatted }}</span>
        </div>
        
        <div v-if="property.rooms" class="flex items-center">
          <BuildingOfficeIcon class="h-4 w-4 mr-1 text-gray-400" />
          <span>{{ property.rooms }} rooms</span>
        </div>
        
        <div v-if="property.floor && property.total_floors" class="flex items-center">
          <BuildingStorefrontIcon class="h-4 w-4 mr-1 text-gray-400" />
          <span>{{ property.floor }}/{{ property.total_floors }}</span>
        </div>
      </div>
      
      <!-- Location -->
      <div v-if="displayLocation" class="flex items-start">
        <MapPinIcon class="h-4 w-4 mr-1 text-gray-400 mt-0.5 flex-shrink-0" />
        <span class="text-sm text-gray-600 line-clamp-2">
          {{ displayLocation }}
        </span>
      </div>
      
      <!-- Features (Swipeable) -->
      <div 
        v-if="property.features_localized?.length"
        class="features-container overflow-x-auto scrollbar-hide"
      >
        <div class="flex space-x-2 pb-1">
          <span
            v-for="feature in property.features_localized.slice(0, 5)"
            :key="feature"
            class="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full whitespace-nowrap"
          >
            {{ feature }}
          </span>
          <span
            v-if="property.features_localized.length > 5"
            class="inline-block px-2 py-1 bg-gray-100 text-gray-500 text-xs rounded-full whitespace-nowrap"
          >
            +{{ property.features_localized.length - 5 }}
          </span>
        </div>
      </div>
      
      <!-- Footer Actions -->
      <div class="flex items-center justify-between pt-2 border-t border-gray-100">
        <!-- Posted Date -->
        <div class="text-xs text-gray-500">
          {{ formatRelativeTime(property.posted_date) }}
        </div>
        
        <!-- Quick Actions -->
        <div class="flex space-x-3">
          <button
            v-if="hasCoordinates"
            @click.stop="viewOnMap"
            class="text-blue-600 hover:text-blue-800 transition-colors"
            :title="$t('property.view_on_map')"
          >
            <MapIcon class="h-5 w-5" />
          </button>
          
          <button
            @click.stop="contactAgent"
            class="text-green-600 hover:text-green-800 transition-colors"
            :title="$t('property.contact')"
          >
            <PhoneIcon class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
    
    <!-- Swipe Actions Overlay -->
    <div 
      v-if="swipeState.active"
      class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20 transition-opacity"
      :class="{ 'opacity-100': swipeState.showOverlay, 'opacity-0': !swipeState.showOverlay }"
    >
      <div 
        class="text-white text-lg font-medium px-4 py-2 bg-black bg-opacity-70 rounded-lg"
      >
        {{ swipeState.direction === 'left' ? '❤️ Add to Favorites' : '📍 View on Map' }}
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  HeartIcon,
  ShareIcon,
  PhotoIcon,
  HomeIcon,
  ScaleIcon,
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  MapPinIcon,
  MapIcon,
  PhoneIcon,
  ChevronUpIcon,
  ChevronDownIcon
} from '@heroicons/vue/24/outline'

import { useTouchGestures } from '@/composables/useTouchGestures'
import { useHapticFeedback } from '@/composables/useHapticFeedback'
import { useSavedListingsStore } from '@/stores/savedListings'
import { useAnalyticsStore } from '@/stores/analytics'
import type { ListingResponse } from '@/services/api'
import OptimizedImage from '@/components/common/OptimizedImage.vue'

// Props
interface Props {
  property: ListingResponse
  imageHeight?: number
  critical?: boolean
  showSwipeHints?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  imageHeight: 240,
  critical: false,
  showSwipeHints: false
})

const emit = defineEmits<{
  favorited: [property: ListingResponse]
  unfavorited: [property: ListingResponse]
  clicked: [property: ListingResponse]
  shared: [property: ListingResponse]
  viewOnMap: [property: ListingResponse]
  contact: [property: ListingResponse]
}>()

// Composables
const router = useRouter()
const { t } = useI18n()
const { triggerHaptic } = useHapticFeedback()
const savedListingsStore = useSavedListingsStore()
const analyticsStore = useAnalyticsStore()

// State
const currentImageIndex = ref(0)
const imagesLoaded = ref<Record<number, boolean>>({})
const swipeState = ref({
  active: false,
  swiped: false,
  direction: null as 'left' | 'right' | null,
  showOverlay: false
})

// Touch handling
const swipeThreshold = 50
const swipeStyle = ref({})

const {
  onTouchStart: handleTouchStart,
  onTouchMove: handleTouchMove,
  onTouchEnd: handleTouchEnd
} = useTouchGestures({
  onSwipeLeft: () => handleSwipeAction('left'),
  onSwipeRight: () => handleSwipeAction('right'),
  threshold: swipeThreshold,
  onSwipeProgress: (progress, direction) => {
    swipeState.value.active = true
    swipeState.value.direction = direction as 'left' | 'right'
    swipeState.value.showOverlay = Math.abs(progress) > 30
    
    // Update visual feedback
    const opacity = Math.min(Math.abs(progress) / 100, 0.8)
    const translateX = Math.max(-100, Math.min(100, progress))
    
    swipeStyle.value = {
      transform: `translateX(${translateX * 0.3}px)`,
      opacity: 1 - opacity * 0.2
    }
  },
  onSwipeEnd: () => {
    swipeState.value.active = false
    swipeState.value.showOverlay = false
    swipeStyle.value = {}
  }
})

// Computed properties
const isFavorited = computed(() => 
  savedListingsStore.isListingSaved(props.property.id)
)

const isNew = computed(() => {
  if (!props.property.posted_date) return false
  const postedDate = new Date(props.property.posted_date)
  const now = new Date()
  const diffHours = (now.getTime() - postedDate.getTime()) / (1000 * 60 * 60)
  return diffHours < 24 // Consider new if posted within 24 hours
})

const hasCoordinates = computed(() => 
  props.property.latitude && props.property.longitude
)

const displayLocation = computed(() => {
  const parts = []
  if (props.property.address) parts.push(props.property.address)
  if (props.property.city_localized) parts.push(props.property.city_localized)
  if (props.property.district_localized && !parts.some(p => p.includes(props.property.district_localized!))) {
    parts.push(props.property.district_localized)
  }
  return parts.join(', ')
})

const priceChange = computed(() => {
  // This would come from real-time price tracking
  // Mock implementation for demonstration
  return null
})

// Methods
const formatPrice = (price?: number) => {
  if (!price) return t('common.price_on_request')
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0
  }).format(price)
}

const formatRelativeTime = (dateString?: string) => {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffHours < 1) return t('time.just_now')
  if (diffHours < 24) return t('time.hours_ago', { count: diffHours })
  if (diffDays < 7) return t('time.days_ago', { count: diffDays })
  
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric'
  }).format(date)
}

const setCurrentImage = (index: number) => {
  currentImageIndex.value = index
  triggerHaptic('light')
}

const handleImageLoad = () => {
  // Track image load performance
  analyticsStore.trackEvent('image_load', {
    property_id: props.property.id,
    image_index: currentImageIndex.value
  })
}

const handleImageError = () => {
  analyticsStore.trackEvent('image_error', {
    property_id: props.property.id,
    image_index: currentImageIndex.value
  })
}

const toggleFavorite = () => {
  triggerHaptic('medium')
  
  if (isFavorited.value) {
    savedListingsStore.removeFromSaved(props.property.id)
    emit('unfavorited', props.property)
    analyticsStore.trackEvent('property_unfavorited', {
      property_id: props.property.id,
      source: 'mobile_card'
    })
  } else {
    savedListingsStore.addToSaved(props.property)
    emit('favorited', props.property)
    analyticsStore.trackEvent('property_favorited', {
      property_id: props.property.id,
      source: 'mobile_card'
    })
  }
}

const handleShare = async () => {
  triggerHaptic('light')
  
  const shareData = {
    title: props.property.title,
    text: `Check out this property: ${formatPrice(props.property.price)}`,
    url: `${window.location.origin}/property/${props.property.id}`
  }
  
  if (navigator.share) {
    try {
      await navigator.share(shareData)
      analyticsStore.trackEvent('property_shared', {
        property_id: props.property.id,
        method: 'native_share'
      })
    } catch (error) {
      console.log('Error sharing:', error)
    }
  } else {
    // Fallback: copy to clipboard
    try {
      await navigator.clipboard.writeText(shareData.url)
      // Show toast notification
      analyticsStore.trackEvent('property_shared', {
        property_id: props.property.id,
        method: 'clipboard'
      })
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
    }
  }
  
  emit('shared', props.property)
}

const viewOnMap = () => {
  triggerHaptic('light')
  
  if (hasCoordinates.value) {
    router.push({
      name: 'Map',
      query: {
        lat: props.property.latitude,
        lng: props.property.longitude,
        zoom: '15',
        property: props.property.id
      }
    })
    
    analyticsStore.trackEvent('view_on_map', {
      property_id: props.property.id,
      source: 'mobile_card'
    })
    
    emit('viewOnMap', props.property)
  }
}

const contactAgent = () => {
  triggerHaptic('medium')
  
  // Open contact modal or navigate to contact page
  analyticsStore.trackEvent('contact_agent', {
    property_id: props.property.id,
    source: 'mobile_card'
  })
  
  emit('contact', props.property)
}

const handleCardClick = () => {
  triggerHaptic('light')
  
  router.push(`/property/${props.property.id}`)
  
  analyticsStore.trackEvent('property_view', {
    property_id: props.property.id,
    source: 'mobile_card'
  })
  
  emit('clicked', props.property)
}

const handleSwipeAction = (direction: 'left' | 'right') => {
  triggerHaptic('heavy')
  
  swipeState.value.swiped = true
  
  if (direction === 'left') {
    // Swipe left = Add to favorites
    if (!isFavorited.value) {
      toggleFavorite()
    }
  } else {
    // Swipe right = View on map
    viewOnMap()
  }
  
  // Reset swipe state after animation
  setTimeout(() => {
    swipeState.value.swiped = false
  }, 300)
}

// Auto-advance images (optional)
let imageInterval: number | null = null

const startImageAutoplay = () => {
  if (props.property.image_urls.length <= 1) return
  
  imageInterval = window.setInterval(() => {
    currentImageIndex.value = (currentImageIndex.value + 1) % props.property.image_urls.length
  }, 4000)
}

const stopImageAutoplay = () => {
  if (imageInterval) {
    clearInterval(imageInterval)
    imageInterval = null
  }
}

// Touch image navigation
const handleImageTouchStart = (event: TouchEvent) => {
  stopImageAutoplay()
}

const handleImageTouchEnd = (event: TouchEvent) => {
  // Resume autoplay after 5 seconds of inactivity
  setTimeout(() => {
    if (props.property.image_urls.length > 1) {
      startImageAutoplay()
    }
  }, 5000)
}

// Watchers
watch(
  () => props.property.image_urls,
  (newUrls) => {
    if (newUrls.length > 1 && !imageInterval) {
      startImageAutoplay()
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.mobile-property-card {
  touch-action: manipulation;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.mobile-property-card--swiped {
  transform: scale(0.95);
}

.mobile-property-card--favorited {
  border-color: #ef4444;
}

.features-container {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.features-container::-webkit-scrollbar {
  display: none;
}

.image-slider {
  touch-action: pan-x;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Smooth touch interactions */
@media (hover: none) and (pointer: coarse) {
  .mobile-property-card:active {
    transform: scale(0.98);
  }
}

/* Haptic feedback support */
.mobile-property-card {
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}

/* Performance optimizations */
.mobile-property-card * {
  will-change: transform;
}

.image-slider img {
  will-change: transform;
}
</style>