<template>
  <div class="bg-white rounded-lg shadow-lg p-6">
    <!-- Search Title -->
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-gray-900 mb-2">
        {{ $t('search.title') }}
      </h2>
      <p class="text-gray-600">
        {{ $t('search.found', { count: totalResults }) }}
      </p>
    </div>

    <!-- Search Form -->
    <form @submit.prevent="handleSearch" class="space-y-4">
      <!-- Main Search Input -->
      <div class="relative">
        <MagnifyingGlassIcon class="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="$t('search.placeholder')"
          class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
          @input="debouncedSearch"
        />
      </div>

      <!-- Filter Row -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Location Filter -->
        <div>
          <label class="form-label">{{ $t('search.filters.location') }}</label>
          <select
            v-model="filters.city"
            class="form-input"
            @change="handleFilterChange"
          >
            <option value="">{{ $t('search.filters.any') }}</option>
            <option
              v-for="city in cities"
              :key="city.value"
              :value="city.value"
            >
              {{ city.label }}
            </option>
          </select>
        </div>

        <!-- Property Type Filter -->
        <div>
          <label class="form-label">{{ $t('search.filters.property_type') }}</label>
          <select
            v-model="filters.property_type"
            class="form-input"
            @change="handleFilterChange"
          >
            <option value="">{{ $t('search.filters.any') }}</option>
            <option
              v-for="type in propertyTypes"
              :key="type.value"
              :value="type.value"
            >
              {{ type.label }}
            </option>
          </select>
        </div>

        <!-- Listing Type Filter -->
        <div>
          <label class="form-label">{{ $t('search.filters.listing_type') }}</label>
          <select
            v-model="filters.listing_type"
            class="form-input"
            @change="handleFilterChange"
          >
            <option value="">{{ $t('search.filters.any') }}</option>
            <option
              v-for="type in listingTypes"
              :key="type.value"
              :value="type.value"
            >
              {{ type.label }}
            </option>
          </select>
        </div>

        <!-- Sort Filter -->
        <div>
          <label class="form-label">{{ $t('search.sort.title', 'Sort by') }}</label>
          <select
            v-model="sortBy"
            class="form-input"
            @change="handleSortChange"
          >
            <option value="scraped_at:desc">{{ $t('search.sort.newest') }}</option>
            <option value="scraped_at:asc">{{ $t('search.sort.oldest') }}</option>
            <option value="price:asc">{{ $t('search.sort.price_low') }}</option>
            <option value="price:desc">{{ $t('search.sort.price_high') }}</option>
            <option value="area_sqm:asc">{{ $t('search.sort.area_small') }}</option>
            <option value="area_sqm:desc">{{ $t('search.sort.area_large') }}</option>
          </select>
        </div>
      </div>

      <!-- Advanced Filters Toggle -->
      <div class="flex justify-between items-center">
        <button
          type="button"
          @click="showAdvancedFilters = !showAdvancedFilters"
          class="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center"
        >
          <AdjustmentsHorizontalIcon class="h-4 w-4 mr-1" />
          {{ $t('search.advanced') }}
          <ChevronDownIcon 
            class="h-4 w-4 ml-1 transition-transform"
            :class="{ 'rotate-180': showAdvancedFilters }"
          />
        </button>

        <div class="flex space-x-2">
          <button
            type="button"
            @click="clearFilters"
            class="btn btn-outline btn-sm"
          >
            {{ $t('search.filters.clear_all') }}
          </button>
          <button
            type="submit"
            class="btn btn-primary btn-sm"
            :disabled="isLoading"
          >
            <span v-if="isLoading" class="spinner spinner-sm mr-2"></span>
            {{ $t('search.filters.apply_filters') }}
          </button>
        </div>
      </div>

      <!-- Advanced Filters -->
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="transform scale-95 opacity-0 max-h-0"
        enter-to-class="transform scale-100 opacity-100 max-h-screen"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="transform scale-100 opacity-100 max-h-screen"
        leave-to-class="transform scale-95 opacity-0 max-h-0"
      >
        <div v-show="showAdvancedFilters" class="overflow-hidden">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4 border-t border-gray-200">
            <!-- Price Range -->
            <div class="col-span-1 md:col-span-2 lg:col-span-1">
              <label class="form-label">{{ $t('search.filters.price_range') }}</label>
              <div class="grid grid-cols-2 gap-2">
                <input
                  v-model.number="filters.min_price"
                  type="number"
                  :placeholder="$t('search.filters.min_price')"
                  class="form-input"
                  min="0"
                  @input="handleFilterChange"
                />
                <input
                  v-model.number="filters.max_price"
                  type="number"
                  :placeholder="$t('search.filters.max_price')"
                  class="form-input"
                  min="0"
                  @input="handleFilterChange"
                />
              </div>
            </div>

            <!-- Area Range -->
            <div class="col-span-1 md:col-span-2 lg:col-span-1">
              <label class="form-label">{{ $t('search.filters.area_range') }}</label>
              <div class="grid grid-cols-2 gap-2">
                <input
                  v-model.number="filters.min_area"
                  type="number"
                  :placeholder="$t('search.filters.min_area')"
                  class="form-input"
                  min="0"
                  step="0.1"
                  @input="handleFilterChange"
                />
                <input
                  v-model.number="filters.max_area"
                  type="number"
                  :placeholder="$t('search.filters.max_area')"
                  class="form-input"
                  min="0"
                  step="0.1"
                  @input="handleFilterChange"
                />
              </div>
            </div>

            <!-- Rooms -->
            <div>
              <label class="form-label">{{ $t('search.filters.rooms') }}</label>
              <select
                v-model="filters.rooms"
                class="form-input"
                @change="handleFilterChange"
              >
                <option value="">{{ $t('search.filters.any') }}</option>
                <option v-for="num in [1,2,3,4,5,6]" :key="num" :value="num">
                  {{ num }} {{ $t('units.rooms') }}
                </option>
                <option value="7+">7+ {{ $t('units.rooms') }}</option>
              </select>
            </div>
          </div>
        </div>
      </Transition>
    </form>

    <!-- Active Filters -->
    <div v-if="activeFilters.length > 0" class="mt-4">
      <div class="flex flex-wrap gap-2">
        <span class="text-sm text-gray-600 mr-2">{{ $t('search.filters.title') }}:</span>
        <span
          v-for="filter in activeFilters"
          :key="filter.key"
          class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800"
        >
          {{ filter.label }}
          <button
            @click="removeFilter(filter.key)"
            class="ml-1 hover:bg-primary-200 rounded-full p-0.5"
          >
            <XMarkIcon class="h-3 w-3" />
          </button>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
  MagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
  ChevronDownIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'

import { useLanguageStore } from '@/stores/language'
import { useSearchStore } from '@/stores/search'
import type { SearchFilters } from '@/services/api'

// Composables
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const languageStore = useLanguageStore()
const searchStore = useSearchStore()

// Props & Emits
interface Props {
  initialFilters?: Partial<SearchFilters>
  totalResults?: number
}

const props = withDefaults(defineProps<Props>(), {
  totalResults: 0
})

const emit = defineEmits<{
  search: [filters: SearchFilters]
  filtersChange: [filters: SearchFilters]
}>()

// State
const searchQuery = ref('')
const showAdvancedFilters = ref(false)
const isLoading = ref(false)
const sortBy = ref('scraped_at:desc')

const filters = ref<SearchFilters>({
  city: '',
  property_type: '',
  listing_type: '',
  min_price: undefined,
  max_price: undefined,
  min_area: undefined,
  max_area: undefined,
  rooms: undefined,
  page: 1,
  limit: 20,
  sort_by: 'scraped_at',
  sort_order: 'desc'
})

// Computed properties for dropdown options
const cities = computed(() => [
  { value: 'riga', label: t('cities.riga') },
  { value: 'jurmala', label: t('cities.jurmala') },
  { value: 'liepaja', label: t('cities.liepaja') },
  { value: 'daugavpils', label: t('cities.daugavpils') },
  { value: 'jelgava', label: t('cities.jelgava') },
  // Add more cities as needed
])

const propertyTypes = computed(() => [
  { value: 'apartment', label: t('types.apartment') },
  { value: 'house', label: t('types.house') },
  { value: 'land', label: t('types.land') },
  { value: 'commercial', label: t('types.commercial') },
  { value: 'office', label: t('types.office') },
])

const listingTypes = computed(() => [
  { value: 'sell', label: t('listing_types.sell') },
  { value: 'rent', label: t('listing_types.rent') },
])

const activeFilters = computed(() => {
  const active = []
  
  if (filters.value.city) {
    const city = cities.value.find(c => c.value === filters.value.city)
    if (city) active.push({ key: 'city', label: city.label })
  }
  
  if (filters.value.property_type) {
    const type = propertyTypes.value.find(t => t.value === filters.value.property_type)
    if (type) active.push({ key: 'property_type', label: type.label })
  }
  
  if (filters.value.listing_type) {
    const type = listingTypes.value.find(t => t.value === filters.value.listing_type)
    if (type) active.push({ key: 'listing_type', label: type.label })
  }
  
  if (filters.value.min_price) {
    active.push({ 
      key: 'min_price', 
      label: `${t('search.filters.min_price')}: ${languageStore.formatCurrency(filters.value.min_price)}` 
    })
  }
  
  if (filters.value.max_price) {
    active.push({ 
      key: 'max_price', 
      label: `${t('search.filters.max_price')}: ${languageStore.formatCurrency(filters.value.max_price)}` 
    })
  }
  
  if (filters.value.min_area) {
    active.push({ 
      key: 'min_area', 
      label: `${t('search.filters.min_area')}: ${languageStore.formatArea(filters.value.min_area)}` 
    })
  }
  
  if (filters.value.max_area) {
    active.push({ 
      key: 'max_area', 
      label: `${t('search.filters.max_area')}: ${languageStore.formatArea(filters.value.max_area)}` 
    })
  }
  
  return active
})

// Methods
const handleSearch = () => {
  isLoading.value = true
  
  const searchFilters = {
    ...filters.value,
    q: searchQuery.value || undefined
  }
  
  emit('search', searchFilters)
  
  // Update URL with search params
  const query = Object.fromEntries(
    Object.entries(searchFilters).filter(([_, value]) => value !== '' && value !== undefined)
  )
  
  router.push({ query })
  
  setTimeout(() => {
    isLoading.value = false
  }, 1000)
}

const handleFilterChange = () => {
  emit('filtersChange', filters.value)
}

const handleSortChange = () => {
  const [field, order] = sortBy.value.split(':')
  filters.value.sort_by = field
  filters.value.sort_order = order as 'asc' | 'desc'
  handleFilterChange()
}

const clearFilters = () => {
  searchQuery.value = ''
  filters.value = {
    city: '',
    property_type: '',
    listing_type: '',
    min_price: undefined,
    max_price: undefined,
    min_area: undefined,
    max_area: undefined,
    rooms: undefined,
    page: 1,
    limit: 20,
    sort_by: 'scraped_at',
    sort_order: 'desc'
  }
  sortBy.value = 'scraped_at:desc'
  handleSearch()
}

const removeFilter = (filterKey: string) => {
  switch (filterKey) {
    case 'city':
      filters.value.city = ''
      break
    case 'property_type':
      filters.value.property_type = ''
      break
    case 'listing_type':
      filters.value.listing_type = ''
      break
    case 'min_price':
      filters.value.min_price = undefined
      break
    case 'max_price':
      filters.value.max_price = undefined
      break
    case 'min_area':
      filters.value.min_area = undefined
      break
    case 'max_area':
      filters.value.max_area = undefined
      break
  }
  handleFilterChange()
}

// Debounced search for real-time searching
const debouncedSearch = useDebounceFn(() => {
  handleFilterChange()
}, 500)

// Initialize from route query
onMounted(() => {
  const query = route.query
  
  if (query.q) searchQuery.value = query.q as string
  if (query.city) filters.value.city = query.city as string
  if (query.property_type) filters.value.property_type = query.property_type as string
  if (query.listing_type) filters.value.listing_type = query.listing_type as string
  if (query.min_price) filters.value.min_price = Number(query.min_price)
  if (query.max_price) filters.value.max_price = Number(query.max_price)
  if (query.min_area) filters.value.min_area = Number(query.min_area)
  if (query.max_area) filters.value.max_area = Number(query.max_area)
  
  // Apply initial filters if provided
  if (props.initialFilters) {
    Object.assign(filters.value, props.initialFilters)
  }
})
</script>

<style scoped>
.rotate-180 {
  transform: rotate(180deg);
}
</style>