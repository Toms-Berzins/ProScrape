<template>
  <div class="virtual-property-grid" ref="containerRef">
    <!-- Grid Header with Stats -->
    <div class="grid-header sticky top-0 bg-white z-10 border-b border-gray-200 pb-4 mb-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ totalListings.toLocaleString() }} Properties Found
          </h2>
          <div v-if="priceRangeStats" class="text-sm text-gray-600">
            €{{ priceRangeStats.min.toLocaleString() }} - €{{ priceRangeStats.max.toLocaleString() }}
            (Avg: €{{ priceRangeStats.average.toLocaleString() }})
          </div>
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- View Toggle -->
          <div class="flex bg-gray-100 rounded-lg p-1">
            <button
              @click="setViewMode('grid')"
              :class="[
                'px-3 py-1 rounded text-sm font-medium transition-colors',
                viewMode === 'grid' 
                  ? 'bg-white text-gray-900 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              <GridIcon class="h-4 w-4" />
            </button>
            <button
              @click="setViewMode('list')"
              :class="[
                'px-3 py-1 rounded text-sm font-medium transition-colors',
                viewMode === 'list' 
                  ? 'bg-white text-gray-900 shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              <ListIcon class="h-4 w-4" />
            </button>
          </div>
          
          <!-- Sort Dropdown -->
          <select
            v-model="sortBy"
            @change="handleSortChange"
            class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="posted_date">Newest First</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="area_desc">Largest First</option>
            <option value="area_asc">Smallest First</option>
          </select>
        </div>
      </div>
      
      <!-- Performance Stats (dev mode) -->
      <div v-if="showPerformanceStats" class="mt-2 text-xs text-gray-500">
        Rendered: {{ visibleItems.length }}/{{ totalListings }} | 
        Avg Response: {{ averageApiResponse }}ms | 
        Cache Hit Rate: {{ cacheHitRate }}%
      </div>
    </div>

    <!-- Virtual Scroll Container -->
    <div
      ref="scrollContainer"
      class="virtual-scroll-container"
      :style="{ height: containerHeight + 'px' }"
      @scroll="handleScroll"
    >
      <!-- Spacer for items above viewport -->
      <div :style="{ height: offsetY + 'px' }" />
      
      <!-- Visible Items -->
      <div 
        :class="[
          'property-grid transition-all duration-300',
          {
            'grid-cols-1': viewMode === 'list',
            'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4': viewMode === 'grid' && !isCompact,
            'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5': viewMode === 'grid' && isCompact
          }
        ]"
      >
        <PropertyCard
          v-for="listing in visibleItems"
          :key="`${listing.id}-${listing.updated_date || listing.scraped_at}`"
          :property="listing"
          :compact="isCompact"
          :view-mode="viewMode"
          :priority="isInViewport(listing.id) ? 'high' : 'low'"
          :critical="isAboveFold(listing.id)"
          @favorite-toggled="handleFavoriteToggle"
          @view-on-map="handleViewOnMap"
          @property-clicked="handlePropertyClick"
          class="property-grid-item"
        />
      </div>
      
      <!-- Spacer for items below viewport -->
      <div :style="{ height: offsetBottom + 'px' }" />
      
      <!-- Loading More Indicator -->
      <div v-if="isLoadingMore" class="flex items-center justify-center py-8">
        <div class="flex items-center space-x-2 text-gray-600">
          <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
          <span>Loading more properties...</span>
        </div>
      </div>
      
      <!-- End of Results -->
      <div v-else-if="!hasNext && totalListings > 0" class="text-center py-8 text-gray-500">
        You've seen all {{ totalListings.toLocaleString() }} properties
      </div>
    </div>
    
    <!-- Back to Top Button -->
    <Transition name="fade">
      <button
        v-if="showBackToTop"
        @click="scrollToTop"
        class="fixed bottom-6 right-6 bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors z-50"
        aria-label="Back to top"
      >
        <ChevronUpIcon class="h-5 w-5" />
      </button>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useVirtualList, useIntersectionObserver, useScroll } from '@vueuse/core'
import { 
  GridViewIcon as GridIcon, 
  ListBulletIcon as ListIcon,
  ChevronUpIcon 
} from '@heroicons/vue/24/outline'

import { useListingsStore } from '@/stores/listings'
import { usePerformanceStore } from '@/stores/performance'
import { useUserPreferencesStore } from '@/stores/userPreferences'
import PropertyCard from './PropertyCard.vue'
import type { ListingResponse } from '@/services/api'

// Props
interface Props {
  showPerformanceStats?: boolean
  itemHeight?: number
  containerHeight?: number
  loadMoreThreshold?: number
  isCompact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showPerformanceStats: false,
  itemHeight: 400,
  containerHeight: 800,
  loadMoreThreshold: 200,
  isCompact: false
})

// Composables
const listingsStore = useListingsStore()
const performanceStore = usePerformanceStore()
const userPreferencesStore = useUserPreferencesStore()

// Refs
const containerRef = ref<HTMLElement>()
const scrollContainer = ref<HTMLElement>()

// State
const viewMode = ref<'grid' | 'list'>('grid')
const sortBy = ref('posted_date')
const scrollY = ref(0)
const cacheHitRate = ref(0)

// Computed
const totalListings = computed(() => listingsStore.totalListings)
const hasNext = computed(() => listingsStore.hasNext)
const isLoadingMore = computed(() => listingsStore.isLoadingMore)
const priceRangeStats = computed(() => listingsStore.priceRangeStats)
const averageApiResponse = computed(() => performanceStore.averageApiResponse)

const showBackToTop = computed(() => scrollY.value > 1000)

// Virtual scrolling setup
const { list: virtualList, containerProps, wrapperProps } = useVirtualList(
  computed(() => listingsStore.listings),
  {
    itemHeight: computed(() => {
      if (viewMode.value === 'list') return 200
      return props.isCompact ? 320 : props.itemHeight
    }),
    overscan: 5
  }
)

const visibleItems = computed(() => virtualList.value.map(item => item.data))
const offsetY = computed(() => wrapperProps.value.style.paddingTop)
const offsetBottom = computed(() => wrapperProps.value.style.paddingBottom)

// Scroll handling
const { arrivedState } = useScroll(scrollContainer, {
  throttle: 100,
  onScroll: () => {
    scrollY.value = scrollContainer.value?.scrollTop || 0
  }
})

// Methods
const setViewMode = (mode: 'grid' | 'list') => {
  viewMode.value = mode
  userPreferencesStore.updatePreference('propertyGridViewMode', mode)
}

const handleSortChange = () => {
  const [field, order] = sortBy.value.includes('_') 
    ? sortBy.value.split('_') 
    : [sortBy.value, 'desc']
  
  listingsStore.fetchListings({
    ...listingsStore.activeFilters,
    sort_by: field,
    sort_order: order as 'asc' | 'desc',
    page: 1
  })
}

const handleScroll = async () => {
  if (!scrollContainer.value) return
  
  const { scrollTop, scrollHeight, clientHeight } = scrollContainer.value
  
  // Load more when near bottom
  if (scrollHeight - scrollTop - clientHeight < props.loadMoreThreshold && hasNext.value) {
    try {
      await listingsStore.loadMore()
    } catch (error) {
      console.error('Failed to load more listings:', error)
    }
  }
}

const scrollToTop = () => {
  scrollContainer.value?.scrollTo({
    top: 0,
    behavior: 'smooth'
  })
}

const isInViewport = (listingId: string): boolean => {
  // Implementation to check if listing is in current viewport
  return visibleItems.value.some(item => item.id === listingId)
}

const isAboveFold = (listingId: string): boolean => {
  // Check if listing is in the first few items (above fold)
  const index = listingsStore.listings.findIndex(l => l.id === listingId)
  return index < 8 // First 8 items are above fold
}

const handleFavoriteToggle = (event: { listing: ListingResponse; isFavorited: boolean }) => {
  // Handle favorite toggle - this could trigger analytics events
  performanceStore.recordMetric('user_interaction_favorite', 1, 'counter')
}

const handleViewOnMap = (listing: ListingResponse) => {
  // Handle view on map action
  performanceStore.recordMetric('user_interaction_map', 1, 'counter')
  // Navigate to map view with this property highlighted
}

const handlePropertyClick = (listing: ListingResponse) => {
  // Track property view
  performanceStore.recordMetric('property_view', 1, 'counter')
}

// Intersection Observer for performance optimization
const { stop } = useIntersectionObserver(
  containerRef,
  ([{ isIntersecting }]) => {
    if (isIntersecting) {
      // Grid is visible, continue normal operations
    } else {
      // Grid is not visible, could pause updates
    }
  },
  { threshold: 0.1 }
)

// Watch for view mode changes
watch(viewMode, (newMode) => {
  nextTick(() => {
    // Recalculate virtual list after view mode change
    if (scrollContainer.value) {
      scrollContainer.value.dispatchEvent(new Event('scroll'))
    }
  })
})

// Lifecycle
onMounted(() => {
  // Load user preferences
  const savedViewMode = userPreferencesStore.getPreference('propertyGridViewMode')
  if (savedViewMode) {
    viewMode.value = savedViewMode as 'grid' | 'list'
  }
  
  // Initialize scroll container height
  if (containerRef.value && !props.containerHeight) {
    const rect = containerRef.value.getBoundingClientRect()
    containerRef.value.style.height = `${window.innerHeight - rect.top - 100}px`
  }
})

onUnmounted(() => {
  stop()
})
</script>

<style scoped>
.virtual-property-grid {
  @apply relative;
}

.virtual-scroll-container {
  @apply overflow-auto relative;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e0 #f7fafc;
}

.virtual-scroll-container::-webkit-scrollbar {
  @apply w-2;
}

.virtual-scroll-container::-webkit-scrollbar-track {
  @apply bg-gray-100;
}

.virtual-scroll-container::-webkit-scrollbar-thumb {
  @apply bg-gray-400 rounded;
}

.virtual-scroll-container::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-500;
}

.property-grid {
  @apply grid gap-6;
}

.property-grid-item {
  @apply transform transition-transform duration-200;
}

.property-grid-item:hover {
  @apply scale-[1.02];
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive grid adjustments */
@media (max-width: 640px) {
  .property-grid {
    @apply gap-4;
  }
}

/* Performance optimization for transform animations */
.property-grid-item {
  will-change: transform;
}

/* Smooth scrolling */
.virtual-scroll-container {
  scroll-behavior: smooth;
}
</style>