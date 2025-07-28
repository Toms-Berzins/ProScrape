<template>
  <div class="property-popup w-80 max-w-sm">
    <!-- Header with close button -->
    <div class="flex justify-between items-start p-4 border-b border-gray-200">
      <h3 class="text-lg font-semibold text-gray-900 line-clamp-2 flex-1 mr-2">
        {{ property.title }}
      </h3>
      <button
        @click="$emit('close')"
        class="p-1 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
      >
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>

    <!-- Property Image -->
    <div v-if="property.image_urls && property.image_urls.length > 0" class="relative h-32">
      <img
        :src="property.image_urls[0]"
        :alt="property.title"
        class="w-full h-full object-cover"
        @error="onImageError"
      />
      
      <!-- Image count badge -->
      <div
        v-if="property.image_urls.length > 1"
        class="absolute top-2 right-2 bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded-full flex items-center"
      >
        <PhotoIcon class="h-3 w-3 mr-1" />
        {{ property.image_urls.length }}
      </div>
      
      <!-- Listing type badge -->
      <div 
        class="absolute top-2 left-2 px-2 py-1 rounded-full text-xs font-medium"
        :class="listingTypeBadgeClass"
      >
        {{ property.listing_type_localized || property.listing_type }}
      </div>
    </div>

    <!-- Property Details -->
    <div class="p-4 space-y-3">
      <!-- Price -->
      <div class="flex items-center justify-between">
        <div class="text-xl font-bold text-primary-600">
          {{ formatPrice(property.price) }}
          <span v-if="property.listing_type === 'rent'" class="text-sm text-gray-500 font-normal">
            / {{ $t('units.per_month') }}
          </span>
        </div>
        <div v-if="property.price_currency" class="text-sm text-gray-500">
          {{ property.price_currency }}
        </div>
      </div>

      <!-- Property info grid -->
      <div class="grid grid-cols-2 gap-2 text-sm">
        <div v-if="property.property_type_localized" class="flex items-center text-gray-600">
          <HomeIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.property_type_localized }}
        </div>
        
        <div v-if="property.area_formatted" class="flex items-center text-gray-600">
          <ScaleIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.area_formatted }}
        </div>
        
        <div v-if="property.rooms" class="flex items-center text-gray-600">
          <BuildingOfficeIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.rooms }} {{ $t('units.rooms') }}
        </div>
        
        <div v-if="property.floor && property.total_floors" class="flex items-center text-gray-600">
          <BuildingStorefrontIcon class="h-4 w-4 mr-1 text-gray-400" />
          {{ property.floor }}/{{ property.total_floors }} {{ $t('units.floor') }}
        </div>
      </div>

      <!-- Location -->
      <div v-if="property.address || property.city_localized" class="flex items-start">
        <MapPinIcon class="h-4 w-4 mr-1 text-gray-400 mt-0.5 flex-shrink-0" />
        <div class="text-sm text-gray-600">
          <div v-if="property.address" class="line-clamp-1">{{ property.address }}</div>
          <div v-if="property.city_localized">
            {{ property.city_localized }}
            <span v-if="property.district_localized">, {{ property.district_localized }}</span>
          </div>
        </div>
      </div>

      <!-- Features -->
      <div v-if="displayFeatures.length > 0">
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

      <!-- Posted date and source -->
      <div class="flex justify-between items-center text-xs text-gray-500 pt-2 border-t border-gray-100">
        <div v-if="property.posted_date_formatted">
          {{ $t('property.posted') }}: {{ property.posted_date_formatted }}
        </div>
        <div v-if="property.source_site">
          {{ property.source_site }}
        </div>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="px-4 pb-4 flex space-x-2">
      <button
        @click="$emit('view-details', property)"
        class="flex-1 btn btn-primary btn-sm"
      >
        {{ $t('property.details') }}
      </button>
      
      <button
        @click="toggleSaved"
        class="btn btn-outline btn-sm"
        :class="{ '!bg-red-50 !border-red-200 !text-red-600': isSaved }"
        :title="isSaved ? $t('property.unsave') : $t('property.save')"
      >
        <HeartIcon 
          class="h-4 w-4" 
          :class="{ 'fill-current': isSaved }"
        />
      </button>
      
      <button
        @click="shareProperty"
        class="btn btn-outline btn-sm"
        :title="$t('property.share')"
      >
        <ShareIcon class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  XMarkIcon,
  PhotoIcon,
  HomeIcon,
  ScaleIcon,
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  MapPinIcon,
  HeartIcon,
  ShareIcon
} from '@heroicons/vue/24/outline'

import { useLanguageStore } from '@/stores/language'
import { useSavedListingsStore } from '@/stores/savedListings'
import { useAppStore } from '@/stores/app'
import type { ListingResponse } from '@/services/api'
import { getLocalizedPath, getCurrentLocaleFromRoute } from '@/plugins/i18n'

// Props & Emits
interface Props {
  property: ListingResponse
}

defineProps<Props>()

const emit = defineEmits<{
  close: []
  'view-details': [property: ListingResponse]
}>()

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
  return features.slice(0, 4) // Show only first 4 features in popup
})

const remainingFeaturesCount = computed(() => {
  const features = props.property.features_localized || props.property.features || []
  return Math.max(0, features.length - 4)
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

const shareProperty = async () => {
  const currentRoute = router.currentRoute.value
  const currentLocale = getCurrentLocaleFromRoute(currentRoute)
  const detailPath = getLocalizedPath(`/property/${props.property.id}`, currentLocale)
  const url = `${window.location.origin}${detailPath}`
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
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.property-popup {
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  border-radius: 12px;
  overflow: hidden;
  background: white;
  border: 1px solid #e5e7eb;
}
</style>