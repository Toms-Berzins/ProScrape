<template>
  <div class="min-h-screen">
    <!-- Hero Section -->
    <section class="bg-gradient-to-r from-primary-600 to-primary-800 text-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div class="text-center">
          <h1 class="text-4xl md:text-6xl font-bold mb-6">
            {{ $t('messages.welcome') }}
          </h1>
          <p class="text-xl md:text-2xl mb-8 text-primary-100 max-w-3xl mx-auto">
            {{ $t('home.hero.subtitle', 'Find your perfect property in Latvia with our comprehensive real estate search platform') }}
          </p>
          
          <!-- Quick Search -->
          <div class="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-2">
            <div class="flex flex-col sm:flex-row gap-2">
              <input
                v-model="quickSearchQuery"
                type="text"
                :placeholder="$t('search.placeholder')"
                class="flex-1 px-4 py-3 text-gray-900 placeholder-gray-500 rounded-md border-0 focus:ring-2 focus:ring-primary-500 focus:outline-none"
                @keyup.enter="performQuickSearch"
              />
              <button
                @click="performQuickSearch"
                class="bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-md font-medium transition-colors flex items-center justify-center"
              >
                <MagnifyingGlassIcon class="h-5 w-5 mr-2" />
                {{ $t('common.search') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Statistics Section -->
    <section class="py-16 bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-3xl font-bold text-gray-900 mb-4">
            {{ $t('home.stats.title', 'Real Estate Market Overview') }}
          </h2>
          <p class="text-lg text-gray-600 max-w-2xl mx-auto">
            {{ $t('home.stats.subtitle', 'Current market statistics and trends') }}
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div
            v-for="stat in statistics"
            :key="stat.key"
            class="bg-white rounded-lg shadow-sm p-6 text-center hover:shadow-md transition-shadow"
          >
            <div class="text-3xl font-bold text-primary-600 mb-2">
              {{ stat.value }}
            </div>
            <div class="text-gray-600">
              {{ stat.label }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Featured Properties -->
    <section class="py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center mb-12">
          <div>
            <h2 class="text-3xl font-bold text-gray-900 mb-4">
              {{ $t('home.featured.title', 'Featured Properties') }}
            </h2>
            <p class="text-lg text-gray-600">
              {{ $t('home.featured.subtitle', 'Discover the latest and most popular properties') }}
            </p>
          </div>
          <RouterLink
            :to="localizedPath('/search')"
            class="btn btn-outline hidden sm:flex"
          >
            {{ $t('home.featured.view_all', 'View All Properties') }}
          </RouterLink>
        </div>

        <!-- Loading State -->
        <div v-if="isLoadingProperties" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="n in 6"
            :key="n"
            class="bg-white rounded-lg shadow-sm overflow-hidden"
          >
            <div class="h-48 bg-gray-200 skeleton"></div>
            <div class="p-4 space-y-3">
              <div class="h-4 bg-gray-200 skeleton rounded"></div>
              <div class="h-4 bg-gray-200 skeleton rounded w-3/4"></div>
              <div class="h-4 bg-gray-200 skeleton rounded w-1/2"></div>
            </div>
          </div>
        </div>

        <!-- Properties Grid -->
        <div v-else-if="featuredProperties.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <PropertyCard
            v-for="property in featuredProperties"
            :key="property.id"
            :property="property"
          />
        </div>

        <!-- Empty State -->
        <div v-else class="text-center py-12">
          <HomeIcon class="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">
            {{ $t('home.featured.no_properties', 'No featured properties available') }}
          </h3>
          <p class="text-gray-600 mb-6">
            {{ $t('home.featured.no_properties_desc', 'Check back later for new listings') }}
          </p>
          <RouterLink
            :to="localizedPath('/search')"
            class="btn btn-primary"
          >
            {{ $t('common.search') }}
          </RouterLink>
        </div>

        <!-- Mobile View All Button -->
        <div class="text-center mt-8 sm:hidden">
          <RouterLink
            :to="localizedPath('/search')"
            class="btn btn-outline"
          >
            {{ $t('home.featured.view_all', 'View All Properties') }}
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- Search Categories -->
    <section class="py-16 bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-3xl font-bold text-gray-900 mb-4">
            {{ $t('home.categories.title', 'Search by Category') }}
          </h2>
          <p class="text-lg text-gray-600">
            {{ $t('home.categories.subtitle', 'Find properties by type and location') }}
          </p>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <RouterLink
            v-for="category in searchCategories"
            :key="category.type"
            :to="getCategorySearchPath(category.type)"
            class="group bg-white rounded-lg shadow-sm p-6 text-center hover:shadow-md hover:bg-primary-50 transition-all duration-200"
          >
            <component 
              :is="category.icon" 
              class="h-12 w-12 text-gray-400 group-hover:text-primary-600 mx-auto mb-3 transition-colors" 
            />
            <h3 class="font-medium text-gray-900 group-hover:text-primary-900 mb-1">
              {{ $t(`types.${category.type}`) }}
            </h3>
            <p class="text-sm text-gray-500 group-hover:text-primary-700">
              {{ category.count }} {{ $t('home.categories.properties', 'properties') }}
            </p>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-16 bg-primary-600">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="text-3xl font-bold text-white mb-4">
          {{ $t('home.cta.title', 'Ready to Find Your Dream Property?') }}
        </h2>
        <p class="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
          {{ $t('home.cta.subtitle', 'Start your search today and discover thousands of properties across Latvia') }}
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <RouterLink
            :to="localizedPath('/search')"
            class="btn bg-white text-primary-600 hover:bg-gray-100 px-8 py-3 text-lg font-medium"
          >
            {{ $t('navigation.search') }}
          </RouterLink>
          <RouterLink
            :to="localizedPath('/map')"
            class="btn btn-outline border-white text-white hover:bg-white hover:text-primary-600 px-8 py-3 text-lg font-medium"
          >
            {{ $t('navigation.map') }}
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useHead } from '@vueuse/head'
import {
  MagnifyingGlassIcon,
  HomeIcon,
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  MapIcon,
  GlobeEuropeAfricaIcon
} from '@heroicons/vue/24/outline'

import PropertyCard from '@/components/property/PropertyCard.vue'
import { listingsApi, statisticsApi } from '@/services/api'
import { useLanguageStore } from '@/stores/language'
import { useAppStore } from '@/stores/app'
import { getLocalizedPath, getCurrentLocaleFromRoute } from '@/plugins/i18n'
import type { ListingResponse } from '@/services/api'

// Composables
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const languageStore = useLanguageStore()
const appStore = useAppStore()

// State
const quickSearchQuery = ref('')
const featuredProperties = ref<ListingResponse[]>([])
const isLoadingProperties = ref(false)
const statistics = ref([
  { key: 'total', label: t('home.stats.total_properties', 'Total Properties'), value: '0' },
  { key: 'apartments', label: t('types.apartment'), value: '0' },
  { key: 'houses', label: t('types.house'), value: '0' },
  { key: 'cities', label: t('home.stats.cities', 'Cities'), value: '0' }
])

const searchCategories = ref([
  { type: 'apartment', icon: BuildingOfficeIcon, count: 0 },
  { type: 'house', icon: HomeIcon, count: 0 },
  { type: 'commercial', icon: BuildingStorefrontIcon, count: 0 },
  { type: 'land', icon: MapIcon, count: 0 }
])

// Computed
const localizedPath = computed(() => {
  return (path: string) => {
    const currentLocale = getCurrentLocaleFromRoute(route)
    return getLocalizedPath(path, currentLocale)
  }
})

// Methods
const performQuickSearch = () => {
  if (quickSearchQuery.value.trim()) {
    const searchPath = localizedPath.value('/search')
    router.push({
      path: searchPath,
      query: { q: quickSearchQuery.value }
    })
  }
}

const getCategorySearchPath = (propertyType: string) => {
  const searchPath = localizedPath.value('/search')
  return {
    path: searchPath,
    query: { property_type: propertyType }
  }
}

const loadFeaturedProperties = async () => {
  isLoadingProperties.value = true
  
  try {
    const response = await listingsApi.getAll({
      limit: 6,
      sort_by: 'scraped_at',
      sort_order: 'desc'
    })
    
    featuredProperties.value = response.items
  } catch (error) {
    console.error('Error loading featured properties:', error)
    appStore.showError(
      t('messages.error_loading'),
      t('home.featured.load_error', 'Failed to load featured properties')
    )
  } finally {
    isLoadingProperties.value = false
  }
}

const loadStatistics = async () => {
  try {
    const response = await statisticsApi.get()
    
    statistics.value = [
      { 
        key: 'total', 
        label: t('home.stats.total_properties', 'Total Properties'), 
        value: response.total_listings?.toLocaleString() || '0' 
      },
      { 
        key: 'apartments', 
        label: t('types.apartment'), 
        value: response.by_property_type?.apartment?.toLocaleString() || '0' 
      },
      { 
        key: 'houses', 
        label: t('types.house'), 
        value: response.by_property_type?.house?.toLocaleString() || '0' 
      },
      { 
        key: 'cities', 
        label: t('home.stats.cities', 'Cities'), 
        value: Object.keys(response.top_cities || {}).length.toString() 
      }
    ]
    
    // Update search categories with counts
    searchCategories.value = searchCategories.value.map(category => ({
      ...category,
      count: response.by_property_type?.[category.type] || 0
    }))
    
  } catch (error) {
    console.error('Error loading statistics:', error)
  }
}

// SEO Meta
useHead({
  title: computed(() => `${t('messages.welcome')} | ProScrape`),
  meta: [
    {
      name: 'description',
      content: computed(() => t('home.hero.subtitle', 'Find your perfect property in Latvia with our comprehensive real estate search platform'))
    },
    {
      property: 'og:title',
      content: computed(() => `${t('messages.welcome')} | ProScrape`)
    },
    {
      property: 'og:description', 
      content: computed(() => t('home.hero.subtitle', 'Find your perfect property in Latvia with our comprehensive real estate search platform'))
    }
  ]
})

// Lifecycle
onMounted(() => {
  loadFeaturedProperties()
  loadStatistics()
})
</script>

<style scoped>
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, transparent 37%, #f0f0f0 63%);
  background-size: 400% 100%;
  animation: skeleton 1.4s ease-in-out infinite;
}

@keyframes skeleton {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}
</style>