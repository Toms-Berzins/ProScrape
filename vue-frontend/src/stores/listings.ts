import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { debounce } from 'lodash-es'
import type { ListingResponse, SearchFilters, PaginatedResponse } from '@/services/api'
import { listingsApi } from '@/services/api'
import { usePerformanceStore } from './performance'
import { useNotificationStore } from './notifications'

export const useListingsStore = defineStore('listings', () => {
  // === State ===
  const listings = ref<ListingResponse[]>([])
  const totalListings = ref(0)
  const currentPage = ref(1)
  const totalPages = ref(0)
  const hasNext = ref(false)
  const hasPrev = ref(false)
  const isLoading = ref(false)
  const isLoadingMore = ref(false)
  const error = ref<string | null>(null)
  
  // Advanced filtering and search state
  const activeFilters = ref<SearchFilters>({})
  const searchQuery = ref('')
  const facetedFilters = ref<Record<string, any>>({})
  const lastSearchTimestamp = ref<number>(0)
  
  // Real-time state
  const realtimeListings = ref<Map<string, ListingResponse>>(new Map())
  const priceChangeAnimations = ref<Map<string, { oldPrice: number; newPrice: number; timestamp: number }>>(new Map())
  
  // Performance optimization
  const cache = ref<Map<string, { data: PaginatedResponse<ListingResponse>; timestamp: number }>>(new Map())
  const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  // === Computed Properties ===
  const hasListings = computed(() => listings.value.length > 0)
  const isEmpty = computed(() => !isLoading.value && listings.value.length === 0)
  const canLoadMore = computed(() => hasNext.value && !isLoading.value && !isLoadingMore.value)
  
  const activeFiltersCount = computed(() => {
    return Object.values(activeFilters.value).filter(value => 
      value !== undefined && value !== null && value !== '' && value !== false
    ).length
  })

  const enhancedListings = computed(() => {
    return listings.value.map(listing => {
      const cached = realtimeListings.value.get(listing.id)
      if (cached) {
        return { ...listing, ...cached }
      }
      return listing
    })
  })

  const priceRangeStats = computed(() => {
    if (!listings.value.length) return null
    
    const prices = listings.value
      .map(l => l.price)
      .filter(p => p && p > 0)
      .sort((a, b) => a - b)
    
    if (!prices.length) return null
    
    return {
      min: prices[0],
      max: prices[prices.length - 1],
      median: prices[Math.floor(prices.length / 2)],
      average: Math.round(prices.reduce((sum, p) => sum + p, 0) / prices.length)
    }
  })

  // === Actions ===
  const setLoading = (loading: boolean) => {
    isLoading.value = loading
    if (loading) {
      error.value = null
    }
  }

  const setLoadingMore = (loading: boolean) => {
    isLoadingMore.value = loading
  }

  const setError = (errorMessage: string | null) => {
    error.value = errorMessage
    const notificationStore = useNotificationStore()
    if (errorMessage) {
      notificationStore.addNotification({
        type: 'error',
        title: 'Search Error',
        message: errorMessage,
        duration: 5000
      })
    }
  }

  const generateCacheKey = (filters: SearchFilters): string => {
    return JSON.stringify(filters)
  }

  const getCachedData = (cacheKey: string): PaginatedResponse<ListingResponse> | null => {
    const cached = cache.value.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return cached.data
    }
    return null
  }

  const setCachedData = (cacheKey: string, data: PaginatedResponse<ListingResponse>) => {
    cache.value.set(cacheKey, {
      data,
      timestamp: Date.now()
    })
    
    // Clean old cache entries
    if (cache.value.size > 50) {
      const entries = Array.from(cache.value.entries())
      entries.sort((a, b) => a[1].timestamp - b[1].timestamp)
      for (let i = 0; i < 10; i++) {
        cache.value.delete(entries[i][0])
      }
    }
  }

  const fetchListings = async (filters: SearchFilters = {}, append = false) => {
    const performanceStore = usePerformanceStore()
    const startTime = performance.now()
    
    try {
      if (append) {
        setLoadingMore(true)
      } else {
        setLoading(true)
      }

      // Check cache first
      const cacheKey = generateCacheKey(filters)
      const cachedData = getCachedData(cacheKey)
      
      if (cachedData && !append) {
        setListingsFromResponse(cachedData, append)
        setLoading(false)
        performanceStore.recordMetric('listing_fetch_cached', performance.now() - startTime)
        return cachedData
      }

      const response = await listingsApi.getAll(filters)
      
      // Cache the response
      setCachedData(cacheKey, response)
      
      setListingsFromResponse(response, append)
      activeFilters.value = { ...filters }
      lastSearchTimestamp.value = Date.now()
      
      performanceStore.recordMetric('listing_fetch_api', performance.now() - startTime)
      
      return response
    } catch (err: any) {
      setError(err.message || 'Failed to fetch listings')
      performanceStore.recordError('listing_fetch_error', err.message)
      throw err
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  const setListingsFromResponse = (response: PaginatedResponse<ListingResponse>, append = false) => {
    if (append) {
      listings.value = [...listings.value, ...response.items]
    } else {
      listings.value = response.items
    }
    
    totalListings.value = response.total
    currentPage.value = response.page
    totalPages.value = response.total_pages
    hasNext.value = response.has_next
    hasPrev.value = response.has_prev
  }

  const loadMore = async () => {
    if (!canLoadMore.value) return
    
    const nextPageFilters = {
      ...activeFilters.value,
      page: currentPage.value + 1
    }
    
    await fetchListings(nextPageFilters, true)
  }

  const refreshListings = async () => {
    // Clear cache for current filters
    const cacheKey = generateCacheKey(activeFilters.value)
    cache.value.delete(cacheKey)
    
    await fetchListings(activeFilters.value, false)
  }

  const searchListings = debounce(async (query: string, additionalFilters: SearchFilters = {}) => {
    searchQuery.value = query
    const searchFilters = {
      ...additionalFilters,
      search: query,
      page: 1
    }
    
    await fetchListings(searchFilters, false)
  }, 300)

  const updateListing = (updatedListing: ListingResponse) => {
    const index = listings.value.findIndex(l => l.id === updatedListing.id)
    if (index !== -1) {
      listings.value[index] = updatedListing
    }
    
    // Update realtime data
    realtimeListings.value.set(updatedListing.id, updatedListing)
  }

  const addListing = (newListing: ListingResponse) => {
    listings.value.unshift(newListing)
    totalListings.value += 1
    realtimeListings.value.set(newListing.id, newListing)
  }

  const removeListing = (listingId: string) => {
    listings.value = listings.value.filter(l => l.id !== listingId)
    totalListings.value = Math.max(0, totalListings.value - 1)
    realtimeListings.value.delete(listingId)
  }

  const updateListingPrice = (listingId: string, oldPrice: number, newPrice: number) => {
    const listing = listings.value.find(l => l.id === listingId)
    if (listing) {
      listing.price = newPrice
      
      // Add price change animation
      priceChangeAnimations.value.set(listingId, {
        oldPrice,
        newPrice,
        timestamp: Date.now()
      })
      
      // Remove animation after 10 seconds
      setTimeout(() => {
        priceChangeAnimations.value.delete(listingId)
      }, 10000)
    }
  }

  const clearListings = () => {
    listings.value = []
    totalListings.value = 0
    currentPage.value = 1
    totalPages.value = 0
    hasNext.value = false
    hasPrev.value = false
    error.value = null
  }

  const clearCache = () => {
    cache.value.clear()
  }

  const applyFacetedFilter = (filterKey: string, filterValue: any) => {
    facetedFilters.value[filterKey] = filterValue
    
    const newFilters = {
      ...activeFilters.value,
      ...facetedFilters.value,
      page: 1
    }
    
    fetchListings(newFilters, false)
  }

  const removeFacetedFilter = (filterKey: string) => {
    delete facetedFilters.value[filterKey]
    
    const newFilters = {
      ...activeFilters.value,
      ...facetedFilters.value,
      page: 1
    }
    
    fetchListings(newFilters, false)
  }

  const clearAllFilters = () => {
    activeFilters.value = {}
    facetedFilters.value = {}
    searchQuery.value = ''
    fetchListings({}, false)
  }

  // === Watchers ===
  watch(
    () => activeFilters.value,
    (newFilters) => {
      // Auto-save filters to localStorage
      localStorage.setItem('proscrape-active-filters', JSON.stringify(newFilters))
    },
    { deep: true }
  )

  // === Initialization ===
  const initialize = () => {
    // Load saved filters
    try {
      const savedFilters = localStorage.getItem('proscrape-active-filters')
      if (savedFilters) {
        activeFilters.value = JSON.parse(savedFilters)
      }
    } catch (error) {
      console.warn('Failed to load saved filters:', error)
    }
  }

  return {
    // State
    listings: enhancedListings,
    totalListings,
    currentPage,
    totalPages,
    hasNext,
    hasPrev,
    isLoading,
    isLoadingMore,
    error,
    activeFilters,
    searchQuery,
    facetedFilters,
    priceChangeAnimations,
    
    // Computed
    hasListings,
    isEmpty,
    canLoadMore,
    activeFiltersCount,
    priceRangeStats,
    
    // Actions
    fetchListings,
    loadMore,
    refreshListings,
    searchListings,
    updateListing,
    addListing,
    removeListing,
    updateListingPrice,
    clearListings,
    clearCache,
    applyFacetedFilter,
    removeFacetedFilter,
    clearAllFilters,
    initialize
  }
})

export type ListingsStore = ReturnType<typeof useListingsStore>