import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SearchFilters, ListingResponse, PaginatedResponse } from '@/services/api'

export const useSearchStore = defineStore('search', () => {
  // State
  const searchResults = ref<ListingResponse[]>([])
  const totalResults = ref(0)
  const currentPage = ref(1)
  const totalPages = ref(0)
  const isLoading = ref(false)
  const hasNext = ref(false)
  const hasPrev = ref(false)
  const currentFilters = ref<SearchFilters>({})
  const searchHistory = ref<string[]>([])
  const recentSearches = ref<Array<{ query: string; filters: SearchFilters; timestamp: Date }>>([])

  // Getters
  const hasResults = computed(() => searchResults.value.length > 0)
  const isEmpty = computed(() => !isLoading.value && searchResults.value.length === 0)
  const canLoadMore = computed(() => hasNext.value && !isLoading.value)
  
  // Actions
  const setSearchResults = (response: PaginatedResponse<ListingResponse>) => {
    searchResults.value = response.items
    totalResults.value = response.total
    currentPage.value = response.page
    totalPages.value = response.total_pages
    hasNext.value = response.has_next
    hasPrev.value = response.has_prev
  }

  const appendSearchResults = (response: PaginatedResponse<ListingResponse>) => {
    searchResults.value.push(...response.items)
    totalResults.value = response.total
    currentPage.value = response.page
    totalPages.value = response.total_pages
    hasNext.value = response.has_next
    hasPrev.value = response.has_prev
  }

  const setLoading = (loading: boolean) => {
    isLoading.value = loading
  }

  const setFilters = (filters: SearchFilters) => {
    currentFilters.value = { ...filters }
  }

  const clearResults = () => {
    searchResults.value = []
    totalResults.value = 0
    currentPage.value = 1
    totalPages.value = 0
    hasNext.value = false
    hasPrev.value = false
  }

  const addToSearchHistory = (query: string) => {
    if (query.trim()) {
      // Remove existing occurrence
      const index = searchHistory.value.indexOf(query)
      if (index > -1) {
        searchHistory.value.splice(index, 1)
      }
      
      // Add to beginning
      searchHistory.value.unshift(query)
      
      // Keep only last 10 searches
      if (searchHistory.value.length > 10) {
        searchHistory.value = searchHistory.value.slice(0, 10)
      }
      
      saveSearchHistory()
    }
  }

  const addToRecentSearches = (query: string, filters: SearchFilters) => {
    const search = {
      query,
      filters: { ...filters },
      timestamp: new Date()
    }
    
    // Remove existing similar search
    const existingIndex = recentSearches.value.findIndex(
      s => s.query === query && JSON.stringify(s.filters) === JSON.stringify(filters)
    )
    
    if (existingIndex > -1) {
      recentSearches.value.splice(existingIndex, 1)
    }
    
    // Add to beginning
    recentSearches.value.unshift(search)
    
    // Keep only last 20 searches
    if (recentSearches.value.length > 20) {
      recentSearches.value = recentSearches.value.slice(0, 20)
    }
    
    saveRecentSearches()
  }

  const removeFromSearchHistory = (query: string) => {
    const index = searchHistory.value.indexOf(query)
    if (index > -1) {
      searchHistory.value.splice(index, 1)
      saveSearchHistory()
    }
  }

  const clearSearchHistory = () => {
    searchHistory.value = []
    saveSearchHistory()
  }

  const clearRecentSearches = () => {
    recentSearches.value = []
    saveRecentSearches()
  }

  // Storage methods
  const saveSearchHistory = () => {
    try {
      localStorage.setItem('proscrape-search-history', JSON.stringify(searchHistory.value))
    } catch (error) {
      console.error('Error saving search history:', error)
    }
  }

  const loadSearchHistory = () => {
    try {
      const stored = localStorage.getItem('proscrape-search-history')
      if (stored) {
        searchHistory.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Error loading search history:', error)
      searchHistory.value = []
    }
  }

  const saveRecentSearches = () => {
    try {
      localStorage.setItem('proscrape-recent-searches', JSON.stringify(recentSearches.value))
    } catch (error) {
      console.error('Error saving recent searches:', error)
    }
  }

  const loadRecentSearches = () => {
    try {
      const stored = localStorage.getItem('proscrape-recent-searches')
      if (stored) {
        const parsed = JSON.parse(stored)
        // Convert timestamp strings back to Date objects
        recentSearches.value = parsed.map((search: any) => ({
          ...search,
          timestamp: new Date(search.timestamp)
        }))
      }
    } catch (error) {
      console.error('Error loading recent searches:', error)
      recentSearches.value = []
    }
  }

  // Update a specific listing in results (useful for saved/unsaved state changes)
  const updateListingInResults = (updatedListing: ListingResponse) => {
    const index = searchResults.value.findIndex(listing => listing.id === updatedListing.id)
    if (index > -1) {
      searchResults.value[index] = updatedListing
    }
  }

  // Initialize store
  const initialize = () => {
    loadSearchHistory()
    loadRecentSearches()
  }

  return {
    // State
    searchResults,
    totalResults,
    currentPage,
    totalPages,
    isLoading,
    hasNext,
    hasPrev,
    currentFilters,
    searchHistory,
    recentSearches,
    
    // Getters
    hasResults,
    isEmpty,
    canLoadMore,
    
    // Actions
    setSearchResults,
    appendSearchResults,
    setLoading,
    setFilters,
    clearResults,
    addToSearchHistory,
    addToRecentSearches,
    removeFromSearchHistory,
    clearSearchHistory,
    clearRecentSearches,
    updateListingInResults,
    initialize,
  }
})

export type SearchStore = ReturnType<typeof useSearchStore>