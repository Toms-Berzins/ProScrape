<template>
  <article 
    class="property-card bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-lg transition-all duration-200"
    :class="{
      'property-card--compact': compact,
      'property-card--list': viewMode === 'list',
      'property-card--new': isNew,
      'property-card--price-changed': showPriceChangeIndicator
    }"
    @click="handleCardClick"
  >
    <!-- Property Image with Advanced Optimization -->
    <div 
      class="relative bg-gray-200"
      :class="imageContainerClasses"
    >
      <!-- Optimized Image with Lazy Loading -->
      <OptimizedImage
        v-if="property.image_urls && property.image_urls.length > 0"
        :src="property.image_urls[0]"
        :alt="property.title"
        :loading="critical ? 'eager' : 'lazy'"
        :priority="priority"
        :critical="critical"
        :aspect-ratio="viewMode === 'list' ? '4:3' : '16:9'"
        :quality="critical ? 90 : 80"
        :blur-up="!critical"
        :progressive="true"
        :width="imageWidth"
        :height="imageHeight"
        :sizes="imageSizes"
        class="w-full h-full object-cover"
        @load="handleImageLoad"
        @error="handleImageError"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-gray-400">
        <PhotoIcon class="h-12 w-12" />
      </div>
      
      <!-- Image Count Badge -->
      <div 
        v-if="property.image_urls && property.image_urls.length > 1"
        class="absolute top-2 right-2 bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded-full flex items-center"
      >
        <PhotoIcon class="h-3 w-3 mr-1" />
        {{ property.image_urls.length }}
      </div>
      
      <!-- Listing Type Badge -->
      <div 
        class="absolute top-2 left-2 px-2 py-1 rounded-full text-xs font-medium"
        :class="listingTypeBadgeClass"
      >
        {{ property.listing_type_localized || property.listing_type }}
      </div>
      
      <!-- Save Button -->
      <button
        @click.stop="toggleSaved"
        class="absolute bottom-2 right-2 p-2 bg-white bg-opacity-90 hover:bg-opacity-100 rounded-full shadow-sm transition-all duration-200"
        :class="{ 'text-red-500': isSaved, 'text-gray-400 hover:text-red-500': !isSaved }"
      >
        <HeartIcon 
          class="h-5 w-5" 
          :class="{ 'fill-current': isSaved }"
        />
      </button>
    </div>
    
    <!-- Property Content -->
    <div class="p-4">
      <!-- Price -->
      <div class="flex items-center justify-between mb-2">
        <div class="text-2xl font-bold text-primary-600">
          {{ formatPrice(property.price) }}
          <span v-if="property.listing_type === 'rent'" class="text-sm text-gray-500 font-normal">
            / {{ $t('units.per_month') }}
          </span>
        </div>
        <div v-if="property.price_currency" class="text-sm text-gray-500">
          {{ property.price_currency }}
        </div>
      </div>
      
      <!-- Title -->
      <h3 class="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
        {{ property.title }}
      </h3>
      
      <!-- Property Details -->
      <div class="grid grid-cols-2 gap-2 mb-3 text-sm text-gray-600">
        <div v-if="property.property_type_localized" class="flex items-center">
          <HomeIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.property_type_localized }}
        </div>
        
        <div v-if="property.area_formatted" class="flex items-center">
          <ScaleIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.area_formatted }}
        </div>
        
        <div v-if="property.rooms" class="flex items-center">
          <BuildingOfficeIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.rooms }} {{ $t('units.rooms') }}
        </div>
        
        <div v-if="property.floor && property.total_floors" class="flex items-center">
          <BuildingStorefrontIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.floor }}/{{ property.total_floors }} {{ $t('units.floor') }}
        </div>
      </div>
      
      <!-- Location -->
      <div v-if="property.address || property.city_localized" class="flex items-start mb-3">
        <MapPinIcon class="h-4 w-4 mr-1 text-gray-400 mt-0.5 flex-shrink-0" />
        <div class="text-sm text-gray-600 line-clamp-2">
          <div v-if="property.address">{{ property.address }}</div>
          <div v-if="property.city_localized">
            {{ property.city_localized }}
            <span v-if="property.district_localized">, {{ property.district_localized }}</span>
          </div>
        </div>
      </div>
      
      <!-- Features -->
      <div v-if="displayFeatures.length > 0" class="mb-3">
        <div class="flex flex-wrap gap-1">
          <span
            v-for="feature in displayFeatures"
            :key="feature"
            class="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
          >
            {{ feature }}
          </span>
          <span
            v-if="remainingFeaturesCount > 0"
            class="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
          >
            +{{ remainingFeaturesCount }}
          </span>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="flex items-center justify-between pt-3 border-t border-gray-100">
        <!-- Posted Date -->
        <div v-if="property.posted_date_formatted" class="text-xs text-gray-500">
          {{ $t('property.posted') }}: {{ property.posted_date_formatted }}
        </div>
        
        <!-- Source -->
        <div v-if="property.source_site" class="text-xs text-gray-500">
          {{ property.source_site }}
        </div>
      </div>
      
      <!-- Action Buttons -->
      <div class="mt-4 flex space-x-2">
        <RouterLink
          :to="propertyDetailPath"
          class="flex-1 btn btn-primary btn-sm text-center"
        >
          {{ $t('property.details') }}
        </RouterLink>
        
        <button
          v-if="property.latitude && property.longitude"
          @click.stop="viewOnMap"
          class="btn btn-outline btn-sm"
          :title="$t('property.view_on_map')"
        >
          <MapIcon class="h-4 w-4" />
        </button>
        
        <button
          @click.stop="shareProperty"
          class="btn btn-outline btn-sm"
          :title="$t('property.share')"
        >
          <ShareIcon class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  PhotoIcon,
  HeartIcon,
  HomeIcon,
  ScaleIcon,
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  MapPinIcon,
  MapIcon,
  ShareIcon
} from '@heroicons/vue/24/outline'

import { useLanguageStore } from '@/stores/language'
import { useSavedListingsStore } from '@/stores/savedListings'
import { useAppStore } from '@/stores/app'
import type { ListingResponse } from '@/services/api'
import { getLocalizedPath, getCurrentLocaleFromRoute } from '@/plugins/i18n'

// Props
interface Props {
  property: ListingResponse
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false
})

// Composables
const router = useRouter()
const { t } = useI18n()
const languageStore = useLanguageStore()
const savedListingsStore = useSavedListingsStore()
const appStore = useAppStore()

// Computed properties
const isSaved = computed(() => savedListingsStore.isListingSaved(props.property.id))

const listingTypeBadgeClass = computed(() => {
  switch (props.property.listing_type) {
    case 'sell':
      return 'bg-green-100 text-green-800'
    case 'rent':
      return 'bg-blue-100 text-blue-800'
    case 'buy':
      return 'bg-purple-100 text-purple-800'
    case 'rent_wanted':
      return 'bg-orange-100 text-orange-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
})

const displayFeatures = computed(() => {
  const features = props.property.features_localized || props.property.features || []
  return features.slice(0, 3) // Show only first 3 features
})

const remainingFeaturesCount = computed(() => {
  const features = props.property.features_localized || props.property.features || []
  return Math.max(0, features.length - 3)
})

const propertyDetailPath = computed(() => {
  const currentRoute = router.currentRoute.value
  const currentLocale = getCurrentLocaleFromRoute(currentRoute)
  return getLocalizedPath(`/property/${props.property.id}`, currentLocale)
})

// Methods
const formatPrice = (price?: number) => {
  if (!price) return t('common.price_on_request', 'Price on request')
  return languageStore.formatCurrency(price)
}

const toggleSaved = () => {
  if (isSaved.value) {
    savedListingsStore.removeFromSaved(props.property.id)
    appStore.showSuccess(t('messages.property_removed'))
  } else {
    savedListingsStore.addToSaved(props.property)
    appStore.showSuccess(t('messages.property_saved'))
  }
}

const viewOnMap = () => {
  if (props.property.latitude && props.property.longitude) {
    const currentRoute = router.currentRoute.value
    const currentLocale = getCurrentLocaleFromRoute(currentRoute)
    const mapPath = getLocalizedPath('/map', currentLocale)
    
    router.push({
      path: mapPath,
      query: {
        lat: props.property.latitude.toString(),
        lng: props.property.longitude.toString(),
        zoom: '15',
        property: props.property.id
      }
    })
  }
}

const shareProperty = async () => {
  const url = `${window.location.origin}${propertyDetailPath.value}`
  const title = props.property.title
  const text = `${title} - ${formatPrice(props.property.price)}`
  
  if (navigator.share) {
    try {
      await navigator.share({
        title,
        text,
        url
      })
    } catch (error) {
      console.log('Error sharing:', error)
      copyToClipboard(url)
    }
  } else {
    copyToClipboard(url)
  }
}

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    appStore.showSuccess(t('messages.link_copied', 'Link copied to clipboard'))
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    appStore.showError(t('messages.copy_failed', 'Failed to copy link'))
  }
}

const onImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.property-card:hover {
  transform: translateY(-2px);
}
</style>