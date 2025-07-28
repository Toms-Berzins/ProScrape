<template>
  <div class="relative h-full w-full">
    <!-- Map Container -->
    <div ref="mapContainer" class="h-full w-full rounded-lg overflow-hidden"></div>
    
    <!-- Map Controls -->
    <div class="absolute top-4 right-4 z-[1000] space-y-2">
      <!-- Search in Area Button -->
      <button
        v-if="canSearchInArea"
        @click="searchInCurrentArea"
        class="bg-white shadow-lg rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center space-x-2"
      >
        <MagnifyingGlassIcon class="h-4 w-4" />
        <span>{{ $t('map.search_area') }}</span>
      </button>
      
      <!-- Toggle Clustering -->
      <button
        @click="toggleClustering"
        class="bg-white shadow-lg rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center space-x-2"
        :class="{ 'bg-primary-50 text-primary-700': clusteringEnabled }"
      >
        <span class="w-4 h-4 rounded-full border-2 border-current flex items-center justify-center">
          <span class="w-2 h-2 bg-current rounded-full"></span>
        </span>
        <span>{{ $t('map.toggle_clusters') }}</span>
      </button>
      
      <!-- Layer Selector -->
      <div class="bg-white shadow-lg rounded-lg overflow-hidden">
        <select
          v-model="selectedLayer"
          @change="changeMapLayer"
          class="bg-transparent border-none text-sm font-medium text-gray-700 px-3 py-2 focus:outline-none"
        >
          <option value="osm">{{ $t('map.street') }}</option>
          <option value="satellite">{{ $t('map.satellite') }}</option>
          <option value="terrain">{{ $t('map.terrain') }}</option>
        </select>
      </div>
    </div>
    
    <!-- Loading Overlay -->
    <div
      v-if="isLoading"
      class="absolute inset-0 bg-white bg-opacity-80 flex items-center justify-center z-[1000]"
    >
      <div class="text-center">
        <div class="spinner spinner-lg"></div>
        <p class="mt-2 text-sm text-gray-600">{{ $t('map.loading_properties') }}</p>
      </div>
    </div>
    
    <!-- Property Info Popup -->
    <Teleport to="body">
      <div
        v-if="selectedProperty && showPropertyPopup"
        ref="popup"
        class="fixed z-[2000] bg-white rounded-lg shadow-xl border max-w-sm"
        :style="popupStyle"
      >
        <PropertyPopup
          :property="selectedProperty"
          @close="closePopup"
          @view-details="viewPropertyDetails"
        />
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet.markercluster'
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'

import PropertyPopup from './PropertyPopup.vue'
import { useLanguageStore } from '@/stores/language'
import { useRealEstateI18n } from '@/composables/useRealEstateI18n'
import type { ListingResponse } from '@/services/api'
import { getLocalizedPath, getCurrentLocaleFromRoute } from '@/plugins/i18n'

// Fix for default markers in Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Props
interface Props {
  properties?: ListingResponse[]
  center?: [number, number]
  zoom?: number
  height?: string
  highlightProperty?: string
}

const props = withDefaults(defineProps<Props>(), {
  properties: () => [],
  center: () => [56.9496, 24.1052], // Riga, Latvia
  zoom: 10,
  height: '400px'
})

// Emits
const emit = defineEmits<{
  boundsChange: [bounds: L.LatLngBounds]
  propertyClick: [property: ListingResponse]
  mapReady: [map: L.Map]
}>()

// Composables
const { t } = useI18n()
const router = useRouter()
const languageStore = useLanguageStore()
const {
  formatPropertyPrice,
  translatePropertyType,
  translateCityName,
  translateDistrictName,
  formatPropertyArea,
  formatPropertyRooms
} = useRealEstateI18n()

// Refs
const mapContainer = ref<HTMLElement>()
const popup = ref<HTMLElement>()

// State
const map = ref<L.Map>()
const markersGroup = ref<L.MarkerClusterGroup | L.LayerGroup>()
const selectedProperty = ref<ListingResponse>()
const showPropertyPopup = ref(false)
const popupStyle = ref({})
const isLoading = ref(false)
const clusteringEnabled = ref(true)
const selectedLayer = ref('osm')
const canSearchInArea = ref(false)

// Map layers
const tileLayers = {
  osm: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }),
  satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: '© Esri'
  }),
  terrain: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenTopoMap'
  })
}

// Computed
const currentTileLayer = computed(() => tileLayers[selectedLayer.value as keyof typeof tileLayers])

// Methods
const initializeMap = async () => {
  if (!mapContainer.value) return

  // Create map
  map.value = L.map(mapContainer.value, {
    center: props.center,
    zoom: props.zoom,
    zoomControl: false
  })

  // Add zoom control to top left
  L.control.zoom({ position: 'topleft' }).addTo(map.value)

  // Add tile layer
  currentTileLayer.value.addTo(map.value)

  // Initialize markers group
  updateMarkersGroup()

  // Map event listeners
  map.value.on('moveend', handleMapMove)
  map.value.on('zoomend', handleMapMove)
  map.value.on('click', closePopup)

  // Load properties
  await loadProperties()

  emit('mapReady', map.value)
}

const updateMarkersGroup = () => {
  if (!map.value) return

  // Remove existing markers group
  if (markersGroup.value) {
    map.value.removeLayer(markersGroup.value)
  }

  // Create new markers group
  if (clusteringEnabled.value) {
    markersGroup.value = L.markerClusterGroup({
      chunkedLoading: true,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      maxClusterRadius: 80,
      iconCreateFunction: (cluster) => {
        const count = cluster.getChildCount()
        const size = count < 10 ? 'small' : count < 100 ? 'medium' : 'large'
        
        return L.divIcon({
          html: `<div class="cluster-marker cluster-${size}">${count}</div>`,
          className: 'custom-cluster-icon',
          iconSize: L.point(40, 40, true),
        })
      }
    })
  } else {
    markersGroup.value = L.layerGroup()
  }

  map.value.addLayer(markersGroup.value)
}

const loadProperties = async () => {
  if (!map.value || !markersGroup.value) return

  isLoading.value = true

  try {
    // Clear existing markers
    markersGroup.value.clearLayers()

    // Add property markers
    props.properties.forEach(property => {
      if (property.latitude && property.longitude) {
        const marker = createPropertyMarker(property)
        markersGroup.value!.addLayer(marker)
      }
    })

    // Highlight specific property if provided
    if (props.highlightProperty) {
      highlightProperty(props.highlightProperty)
    }

  } catch (error) {
    console.error('Error loading properties on map:', error)
  } finally {
    isLoading.value = false
  }
}

const createPropertyMarker = (property: ListingResponse): L.Marker => {
  const marker = L.marker([property.latitude!, property.longitude!], {
    icon: createPropertyIcon(property)
  })

  // Add click handler
  marker.on('click', (e) => {
    L.DomEvent.stopPropagation(e)
    showPropertyDetails(property, e.target as L.Marker)
  })

  // Add tooltip with basic info
  const price = formatPropertyPrice(property.price, { 
    context: property.listing_type === 'rent' ? 'rent' : undefined,
    showCurrency: true 
  })
  const propertyType = translatePropertyType(property.property_type)
  const area = property.area_sqm ? formatPropertyArea(property.area_sqm) : ''
  const rooms = property.rooms ? formatPropertyRooms(property.rooms) : ''
  
  const tooltipContent = `
    <div class="text-sm max-w-xs">
      <div class="font-semibold mb-1 line-clamp-2">${property.title}</div>
      <div class="text-primary-600 font-medium mb-1">${price}</div>
      <div class="text-gray-600 mb-1">${propertyType}</div>
      ${area ? `<div class="text-gray-500 text-xs">${area}</div>` : ''}
      ${rooms ? `<div class="text-gray-500 text-xs">${rooms}</div>` : ''}
    </div>
  `
  
  marker.bindTooltip(tooltipContent, {
    direction: 'top',
    offset: [0, -10],
    className: 'custom-tooltip'
  })

  return marker
}

const createPropertyIcon = (property: ListingResponse): L.DivIcon => {
  const price = formatPropertyPrice(property.price, { 
    context: property.listing_type === 'rent' ? 'rent' : undefined,
    compact: true 
  })
  const propertyType = translatePropertyType(property.property_type)
  const isHighlighted = property.id === props.highlightProperty
  
  // Determine marker color based on listing type
  let markerClass = 'property-marker'
  if (isHighlighted) {
    markerClass += ' highlighted'
  } else {
    switch (property.listing_type) {
      case 'sell':
        markerClass += ' for-sale'
        break
      case 'rent':
        markerClass += ' for-rent'
        break
      case 'buy':
        markerClass += ' wanted-buy'
        break
      case 'rent_wanted':
        markerClass += ' wanted-rent'
        break
      default:
        markerClass += ' default'
    }
  }
  
  // Create marker with better layout
  const iconSize = price.length > 8 ? [140, 45] : [120, 40]
  
  return L.divIcon({
    html: `
      <div class="property-marker-content">
        <div class="property-price">${price}</div>
        <div class="property-type">${propertyType}</div>
        ${property.rooms ? `<div class="property-rooms">${formatPropertyRooms(property.rooms, { showLabel: false })}r</div>` : ''}
      </div>
    `,
    className: markerClass,
    iconSize,
    iconAnchor: [iconSize[0] / 2, iconSize[1]],
    popupAnchor: [0, -iconSize[1]]
  })
}

const showPropertyDetails = (property: ListingResponse, marker: L.Marker) => {
  selectedProperty.value = property
  
  // Calculate popup position
  const point = map.value!.latLngToContainerPoint(marker.getLatLng())
  const mapRect = mapContainer.value!.getBoundingClientRect()
  
  popupStyle.value = {
    left: `${mapRect.left + point.x - 150}px`, // Center popup on marker
    top: `${mapRect.top + point.y - 10}px`, // Position above marker
    transform: 'translateY(-100%)'
  }
  
  showPropertyPopup.value = true
  emit('propertyClick', property)
}

const closePopup = () => {
  showPropertyPopup.value = false
  selectedProperty.value = undefined
}

const viewPropertyDetails = (property: ListingResponse) => {
  const currentRoute = router.currentRoute.value
  const currentLocale = getCurrentLocaleFromRoute(currentRoute)
  const detailPath = getLocalizedPath(`/property/${property.id}`, currentLocale)
  
  router.push(detailPath)
  closePopup()
}

const highlightProperty = (propertyId: string) => {
  const property = props.properties.find(p => p.id === propertyId)
  if (property && property.latitude && property.longitude) {
    map.value?.setView([property.latitude, property.longitude], 15)
    
    // Show property details after a short delay
    setTimeout(() => {
      const marker = findMarkerByProperty(propertyId)
      if (marker) {
        showPropertyDetails(property, marker)
      }
    }, 500)
  }
}

const findMarkerByProperty = (propertyId: string): L.Marker | null => {
  if (!markersGroup.value) return null
  
  let foundMarker: L.Marker | null = null
  
  markersGroup.value.eachLayer((layer) => {
    if (layer instanceof L.Marker) {
      // You'd need to store property ID on marker for this to work
      // This is a simplified implementation
      foundMarker = layer
    }
  })
  
  return foundMarker
}

const toggleClustering = () => {
  clusteringEnabled.value = !clusteringEnabled.value
  updateMarkersGroup()
  loadProperties()
}

const changeMapLayer = () => {
  if (!map.value) return
  
  // Remove current layer
  map.value.eachLayer((layer) => {
    if (layer instanceof L.TileLayer) {
      map.value!.removeLayer(layer)
    }
  })
  
  // Add new layer
  currentTileLayer.value.addTo(map.value)
}

const handleMapMove = () => {
  if (!map.value) return
  
  const bounds = map.value.getBounds()
  canSearchInArea.value = true
  emit('boundsChange', bounds)
}

const searchInCurrentArea = () => {
  if (!map.value) return
  
  const bounds = map.value.getBounds()
  const ne = bounds.getNorthEast()
  const sw = bounds.getSouthWest()
  
  // Emit bounds for parent component to handle search
  emit('boundsChange', bounds)
}

// Watchers
watch(() => props.properties, loadProperties, { deep: true })

watch(() => props.highlightProperty, (newPropertyId) => {
  if (newPropertyId) {
    highlightProperty(newPropertyId)
  }
})

watch(() => props.center, (newCenter) => {
  if (map.value && newCenter) {
    map.value.setView(newCenter, map.value.getZoom())
  }
})

// Lifecycle
onMounted(() => {
  nextTick(initializeMap)
})

onUnmounted(() => {
  if (map.value) {
    map.value.remove()
  }
})
</script>

<style>
/* Cluster marker styles */
.custom-cluster-icon {
  background: transparent;
  border: none;
}

.cluster-marker {
  background: #3b82f6;
  border: 3px solid #ffffff;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.cluster-small {
  width: 30px;
  height: 30px;
}

.cluster-medium {
  width: 35px;
  height: 35px;
}

.cluster-large {
  width: 40px;
  height: 40px;
}

/* Property marker styles */
.property-marker {
  background: transparent;
  border: none;
}

.property-marker-content {
  background: white;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  padding: 4px 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  text-align: center;
  min-width: 80px;
  position: relative;
}

/* Listing type specific colors */
.property-marker.for-sale .property-marker-content {
  border-color: #10b981;
  background: #f0fdf4;
}

.property-marker.for-sale .property-price {
  color: #10b981;
}

.property-marker.for-rent .property-marker-content {
  border-color: #3b82f6;
  background: #eff6ff;
}

.property-marker.for-rent .property-price {
  color: #3b82f6;
}

.property-marker.wanted-buy .property-marker-content {
  border-color: #8b5cf6;
  background: #faf5ff;
}

.property-marker.wanted-buy .property-price {
  color: #8b5cf6;
}

.property-marker.wanted-rent .property-marker-content {
  border-color: #f59e0b;
  background: #fffbeb;
}

.property-marker.wanted-rent .property-price {
  color: #f59e0b;
}

.property-marker.highlighted .property-marker-content {
  border-color: #ef4444 !important;
  background: #fef2f2 !important;
  animation: pulse 2s infinite;
}

.property-marker.highlighted .property-price {
  color: #ef4444 !important;
}

.property-price {
  font-weight: 600;
  font-size: 12px;
  line-height: 1.2;
  margin-bottom: 1px;
}

.property-type {
  font-size: 10px;
  color: #6b7280;
  line-height: 1.2;
  margin-bottom: 1px;
}

.property-rooms {
  font-size: 9px;
  color: #9ca3af;
  line-height: 1;
  position: absolute;
  top: 2px;
  right: 4px;
  background: rgba(255, 255, 255, 0.8);
  padding: 1px 3px;
  border-radius: 3px;
}

/* Animation for highlighted markers */
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

/* Custom tooltip styles */
.custom-tooltip {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.custom-tooltip::before {
  border-top-color: white;
}

/* Popup positioning */
.leaflet-popup-content-wrapper {
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.leaflet-popup-content {
  margin: 12px;
}

.leaflet-popup-tip {
  background: white;
}
</style>