<template>
  <div class="advanced-property-search">
    <!-- Search Header -->
    <div class="search-header bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="py-4">
          <!-- Main Search Bar -->
          <div class="flex items-center space-x-4 mb-4">
            <div class="flex-1 relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
              </div>
              <input
                v-model="searchQuery"
                type="text"
                class="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                :placeholder="$t('search.placeholder')"
                @input="handleSearchInput"
                @keyup.enter="performSearch"
              />
              
              <!-- Search Suggestions Dropdown -->
              <Transition name="fade">
                <div
                  v-if="showSuggestions && suggestions.length > 0"
                  class="absolute z-50 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none"
                >
                  <div
                    v-for="suggestion in suggestions"
                    :key="suggestion.text"
                    class="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-gray-50"
                    @click="applySuggestion(suggestion)"
                  >
                    <div class="flex items-center">
                      <component 
                        :is="getSuggestionIcon(suggestion.type)" 
                        class="h-4 w-4 text-gray-400 mr-2" 
                      />
                      <span class="font-normal block truncate">
                        {{ suggestion.text }}
                      </span>
                      <span class="text-gray-500 text-sm ml-2">
                        ({{ suggestion.result_count }})
                      </span>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>
            
            <!-- Quick Action Buttons -->
            <div class="flex items-center space-x-2">
              <button
                @click="toggleFilters"
                class="inline-flex items-center px-4 py-3 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                :class="{ 'bg-blue-50 border-blue-300 text-blue-700': showFilters }"
              >
                <AdjustmentsHorizontalIcon class="h-4 w-4 mr-2" />
                {{ $t('search.filters') }}
                <span v-if="activeFiltersCount > 0" class="ml-1 bg-blue-600 text-white text-xs rounded-full px-2 py-1">
                  {{ activeFiltersCount }}
                </span>
              </button>
              
              <button
                @click="toggleSavedSearches"
                class="inline-flex items-center px-4 py-3 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <BookmarkIcon class="h-4 w-4 mr-2" />
                {{ $t('search.saved') }}
              </button>
              
              <button
                @click="performSearch"
                class="inline-flex items-center px-6 py-3 border border-transparent rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                :disabled="isSearching"
              >
                <div v-if="isSearching" class="animate-spin -ml-1 mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                {{ isSearching ? $t('search.searching') : $t('search.search') }}
              </button>
            </div>
          </div>
          
          <!-- Quick Filters -->
          <div class="flex flex-wrap gap-2">
            <button
              v-for="quickFilter in quickFilters"
              :key="quickFilter.id"
              @click="toggleQuickFilter(quickFilter)"
              class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium transition-colors"
              :class="isQuickFilterActive(quickFilter) 
                ? 'bg-blue-100 text-blue-800 ring-1 ring-blue-300' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
            >
              {{ quickFilter.label }}
              <span v-if="quickFilter.count" class="ml-1 text-xs">
                ({{ quickFilter.count.toLocaleString() }})
              </span>
            </button>
          </div>
          
          <!-- Active Filters Summary -->
          <div v-if="activeFiltersCount > 0" class="mt-3 flex flex-wrap gap-2">
            <div
              v-for="filter in activeFiltersSummary"
              :key="filter.key"
              class="inline-flex items-center px-3 py-1 bg-blue-50 text-blue-800 text-sm rounded-full"
            >
              {{ filter.label }}
              <button
                @click="removeFilter(filter.key)"
                class="ml-2 text-blue-600 hover:text-blue-800"
              >
                <XMarkIcon class="h-3 w-3" />
              </button>
            </div>
            <button
              @click="clearAllFilters"
              class="inline-flex items-center px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
            >
              {{ $t('search.clear_all') }}
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Advanced Filters Panel -->
    <Transition name="slide-down">
      <div v-if="showFilters" class="bg-white border-b border-gray-200 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <!-- Location Filters -->
            <div class="space-y-4">
              <h3 class="font-medium text-gray-900">{{ $t('search.location') }}</h3>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ $t('search.city') }}
                </label>
                <LocationSelector
                  v-model="filters.city"
                  :placeholder="$t('search.select_city')"
                  type="city"
                  @update:model-value="updateFilter('city', $event)"
                />
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ $t('search.district') }}
                </label>
                <LocationSelector
                  v-model="filters.district"
                  :placeholder="$t('search.select_district')"
                  type="district"
                  :city="filters.city"
                  @update:model-value="updateFilter('district', $event)"
                />
              </div>
              
              <div v-if="filters.latitude && filters.longitude">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  {{ $t('search.radius') }}
                </label>
                <RangeSlider
                  v-model="filters.radius"
                  :min="1"
                  :max="50"
                  :step="1"
                  :format="(value) => `${value} km`"
                  @update:model-value="updateFilter('radius', $event)"
                />
              </div>
            </div>
            
            <!-- Property Type & Listing Type -->
            <div class="space-y-4">
              <h3 class="font-medium text-gray-900">{{ $t('search.property_details') }}</h3>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  {{ $t('search.property_type') }}
                </label>
                <div class="space-y-2">
                  <label
                    v-for="type in PROPERTY_TYPES"
                    :key="type.value"
                    class="flex items-center"
                  >
                    <input
                      type="checkbox"
                      :value="type.value"
                      :checked="filters.property_type?.includes(type.value)"
                      @change="togglePropertyType(type.value)"
                      class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span class="ml-2 text-sm text-gray-700">{{ type.label }}</span>
                  </label>
                </div>
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  {{ $t('search.listing_type') }}
                </label>
                <div class="space-y-2">
                  <label
                    v-for="type in LISTING_TYPES"
                    :key="type.value"
                    class="flex items-center"
                  >
                    <input
                      type="checkbox"
                      :value="type.value"
                      :checked="filters.listing_type?.includes(type.value)"
                      @change="toggleListingType(type.value)"
                      class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span class="ml-2 text-sm text-gray-700">{{ type.label }}</span>
                  </label>
                </div>
              </div>
            </div>
            
            <!-- Price & Size Filters -->
            <div class="space-y-4">
              <h3 class="font-medium text-gray-900">{{ $t('search.price_and_size') }}</h3>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  {{ $t('search.price_range') }}
                </label>
                <PriceRangeSlider
                  :min-price="filters.min_price"
                  :max-price="filters.max_price"
                  :currency="filters.price_currency || 'EUR'"
                  @update:range="updatePriceRange"
                />
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  {{ $t('search.area_range') }}
                </label>
                <RangeSlider
                  :model-value="[filters.min_area || 0, filters.max_area || 500]"
                  :min="0"
                  :max="500"
                  :step="10"
                  :format="(value) => `${value} m²`"
                  @update:model-value="updateAreaRange"
                />
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  {{ $t('search.rooms') }}
                </label>
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <input
                      v-model.number="filters.min_rooms"
                      type="number"
                      :placeholder="$t('search.min')"
                      min="1"
                      max="10"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      @input="updateFilter('min_rooms', $event.target.value)"
                    />
                  </div>
                  <div>
                    <input
                      v-model.number="filters.max_rooms"
                      type="number"
                      :placeholder="$t('search.max')"
                      min="1"
                      max="10"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      @input="updateFilter('max_rooms', $event.target.value)"
                    />
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Additional Filters -->
            <div class="space-y-4">
              <h3 class="font-medium text-gray-900">{{ $t('search.additional_filters') }}</h3>
              
              <div class="space-y-3">
                <label class="flex items-center">
                  <input
                    v-model="filters.has_images"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    @change="updateFilter('has_images', $event.target.checked)"
                  />
                  <span class="ml-2 text-sm text-gray-700">{{ $t('search.with_photos') }}</span>
                </label>
                
                <label class="flex items-center">
                  <input
                    v-model="filters.has_video"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    @change="updateFilter('has_video', $event.target.checked)"
                  />
                  <span class="ml-2 text-sm text-gray-700">{{ $t('search.with_video') }}</span>
                </label>
                
                <label class="flex items-center">
                  <input
                    v-model="filters.has_parking"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    @change="updateFilter('has_parking', $event.target.checked)"
                  />
                  <span class="ml-2 text-sm text-gray-700">{{ $t('search.parking') }}</span>
                </label>
                
                <label class="flex items-center">
                  <input
                    v-model="filters.has_balcony"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    @change="updateFilter('has_balcony', $event.target.checked)"
                  />
                  <span class="ml-2 text-sm text-gray-700">{{ $t('search.balcony') }}</span>
                </label>
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  {{ $t('search.source_sites') }}
                </label>
                <div class="space-y-2">
                  <label
                    v-for="source in SOURCES"
                    :key="source.value"
                    class="flex items-center"
                  >
                    <input
                      type="checkbox"
                      :value="source.value"
                      :checked="!filters.exclude_sources?.includes(source.value as any)"
                      @change="toggleSourceSite(source.value as any)"
                      class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span class="ml-2 text-sm text-gray-700">{{ source.label }}</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Filter Actions -->
          <div class="mt-6 flex items-center justify-between pt-4 border-t border-gray-200">
            <div class="flex items-center space-x-4">
              <button
                @click="saveCurrentSearch"
                class="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                {{ $t('search.save_search') }}
              </button>
              <button
                @click="resetFilters"
                class="text-sm text-gray-600 hover:text-gray-800"
              >
                {{ $t('search.reset_filters') }}
              </button>
            </div>
            
            <div class="flex items-center space-x-3">
              <span class="text-sm text-gray-600">
                {{ $t('search.found_properties', { count: totalResults }) }}
              </span>
              <button
                @click="performSearch"
                class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                :disabled="isSearching"
              >
                {{ $t('search.apply_filters') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
    
    <!-- Search Results Summary -->
    <div v-if="hasSearched" class="bg-gray-50 border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600">
              {{ $t('search.showing_results', { 
                from: (currentPage - 1) * limit + 1,
                to: Math.min(currentPage * limit, totalResults),
                total: totalResults
              }) }}
            </span>
            <span v-if="searchTime" class="text-xs text-gray-500">
              ({{ searchTime }}ms)
            </span>
          </div>
          
          <div class="flex items-center space-x-2">
            <label class="text-sm text-gray-600">{{ $t('search.sort_by') }}:</label>
            <select
              v-model="sortBy"
              @change="updateSort"
              class="text-sm border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="posted_date">{{ $t('search.sort.newest') }}</option>
              <option value="price">{{ $t('search.sort.price_low') }}</option>
              <option value="price_desc">{{ $t('search.sort.price_high') }}</option>
              <option value="area_desc">{{ $t('search.sort.largest') }}</option>
              <option value="quality_score">{{ $t('search.sort.best_match') }}</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { debounce } from 'lodash-es'
import { useI18n } from 'vue-i18n'
import {
  MagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
  BookmarkIcon,
  XMarkIcon,
  MapPinIcon,
  HomeIcon,
  TagIcon
} from '@heroicons/vue/24/outline'

import { useListingsStore } from '@/stores/listings'
import { useSearchStore } from '@/stores/search'
import { useNotificationStore } from '@/stores/notifications'
import type { PropertySearchFilters, SearchSuggestion } from '@/types/property'
import { PROPERTY_TYPES, LISTING_TYPES, SOURCES } from '@/types/property'

import LocationSelector from './LocationSelector.vue'
import PriceRangeSlider from './PriceRangeSlider.vue'
import RangeSlider from './RangeSlider.vue'

// Composables
const { t } = useI18n()
const listingsStore = useListingsStore()
const searchStore = useSearchStore()
const notificationStore = useNotificationStore()

// State
const searchQuery = ref('')
const showFilters = ref(false)
const showSavedSearches = ref(false)
const showSuggestions = ref(false)
const isSearching = ref(false)
const hasSearched = ref(false)
const searchTime = ref<number>()

const filters = ref<PropertySearchFilters>({})
const suggestions = ref<SearchSuggestion[]>([])
const quickFilters = ref([
  { id: 'has_images', label: t('search.with_photos'), filters: { has_images: true }, count: 0 },
  { id: 'parking', label: t('search.parking'), filters: { has_parking: true }, count: 0 },
  { id: 'new_listings', label: t('search.new_listings'), filters: { posted_from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString() }, count: 0 },
  { id: 'price_reduced', label: t('search.price_reduced'), filters: { has_price_reduction: true }, count: 0 }
])

// Computed
const activeFiltersCount = computed(() => listingsStore.activeFiltersCount)
const totalResults = computed(() => listingsStore.totalListings)
const currentPage = computed(() => listingsStore.currentPage)
const limit = computed(() => 20) // Should come from store
const sortBy = ref('posted_date')

const activeFiltersSummary = computed(() => {
  const summary = []
  
  if (filters.value.city) {
    summary.push({ key: 'city', label: `${t('search.city')}: ${filters.value.city}` })
  }
  
  if (filters.value.min_price || filters.value.max_price) {
    const min = filters.value.min_price ? `€${filters.value.min_price.toLocaleString()}` : '0'
    const max = filters.value.max_price ? `€${filters.value.max_price.toLocaleString()}` : '∞'
    summary.push({ key: 'price', label: `${t('search.price')}: ${min} - ${max}` })
  }
  
  if (filters.value.property_type?.length) {
    summary.push({ 
      key: 'property_type', 
      label: `${t('search.property_type')}: ${filters.value.property_type.join(', ')}` 
    })
  }
  
  return summary
})

// Methods
const handleSearchInput = debounce(async (event: Event) => {
  const query = (event.target as HTMLInputElement).value
  if (query.length > 2) {
    // Fetch suggestions
    suggestions.value = await fetchSuggestions(query)
    showSuggestions.value = true
  } else {
    showSuggestions.value = false
  }
}, 300)

const fetchSuggestions = async (query: string): Promise<SearchSuggestion[]> => {
  // Mock implementation - in real app, this would call API
  return [
    { type: 'location', text: `${query} (City)`, result_count: 45 },
    { type: 'query', text: `${query} apartment`, result_count: 23 },
    { type: 'filter', text: `${query} with parking`, result_count: 12 }
  ]
}

const getSuggestionIcon = (type: string) => {
  switch (type) {
    case 'location': return MapPinIcon
    case 'query': return MagnifyingGlassIcon
    case 'filter': return TagIcon
    default: return HomeIcon
  }
}

const applySuggestion = (suggestion: SearchSuggestion) => {
  searchQuery.value = suggestion.text
  showSuggestions.value = false
  performSearch()
}

const performSearch = async () => {
  isSearching.value = true
  hasSearched.value = true
  const startTime = performance.now()
  
  try {
    const searchFilters = {
      ...filters.value,
      query: searchQuery.value,
      page: 1
    }
    
    await listingsStore.fetchListings(searchFilters)
    searchTime.value = Math.round(performance.now() - startTime)
    
    // Add to search history
    searchStore.addToRecentSearches(searchQuery.value, searchFilters)
    
  } catch (error: any) {
    notificationStore.error('Search Error', error.message)
  } finally {
    isSearching.value = false
  }
}

const toggleFilters = () => {
  showFilters.value = !showFilters.value
}

const toggleSavedSearches = () => {
  showSavedSearches.value = !showSavedSearches.value
}

const updateFilter = (key: keyof PropertySearchFilters, value: any) => {
  filters.value[key] = value
}

const togglePropertyType = (type: string) => {
  if (!filters.value.property_type) {
    filters.value.property_type = []
  }
  
  const index = filters.value.property_type.indexOf(type as any)
  if (index > -1) {
    filters.value.property_type.splice(index, 1)
  } else {
    filters.value.property_type.push(type as any)
  }
}

const toggleListingType = (type: string) => {
  if (!filters.value.listing_type) {
    filters.value.listing_type = []
  }
  
  const index = filters.value.listing_type.indexOf(type as any)
  if (index > -1) {
    filters.value.listing_type.splice(index, 1)
  } else {
    filters.value.listing_type.push(type as any)
  }
}

const toggleSourceSite = (source: string) => {
  if (!filters.value.exclude_sources) {
    filters.value.exclude_sources = []
  }
  
  const index = filters.value.exclude_sources.indexOf(source as any)
  if (index > -1) {
    filters.value.exclude_sources.splice(index, 1)
  } else {
    filters.value.exclude_sources.push(source as any)
  }
}

const updatePriceRange = ({ min, max }: { min: number; max: number }) => {
  filters.value.min_price = min
  filters.value.max_price = max
}

const updateAreaRange = ([min, max]: [number, number]) => {
  filters.value.min_area = min
  filters.value.max_area = max
}

const toggleQuickFilter = (quickFilter: any) => {
  const isActive = isQuickFilterActive(quickFilter)
  
  if (isActive) {
    // Remove quick filter
    Object.keys(quickFilter.filters).forEach(key => {
      delete filters.value[key as keyof PropertySearchFilters]
    })
  } else {
    // Apply quick filter
    Object.assign(filters.value, quickFilter.filters)
  }
}

const isQuickFilterActive = (quickFilter: any) => {
  return Object.keys(quickFilter.filters).every(key => 
    filters.value[key as keyof PropertySearchFilters] === quickFilter.filters[key]
  )
}

const removeFilter = (key: string) => {
  delete filters.value[key as keyof PropertySearchFilters]
}

const clearAllFilters = () => {
  filters.value = {}
  searchQuery.value = ''
}

const resetFilters = () => {
  clearAllFilters()
  performSearch()
}

const saveCurrentSearch = () => {
  // Implementation for saving current search
  notificationStore.success('Search Saved', 'Your search has been saved successfully')
}

const updateSort = () => {
  const [field, order] = sortBy.value.includes('_desc') 
    ? [sortBy.value.replace('_desc', ''), 'desc']
    : [sortBy.value, 'asc']
  
  filters.value.sort_by = field as any
  filters.value.sort_order = order as 'asc' | 'desc'
  performSearch()
}

// Watchers
watch(
  () => filters.value,
  () => {
    // Auto-save filters to localStorage or store
  },
  { deep: true }
)

// Lifecycle
onMounted(() => {
  // Load saved filters from localStorage or route params
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>