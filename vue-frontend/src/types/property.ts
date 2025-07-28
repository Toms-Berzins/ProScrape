// Enhanced TypeScript interfaces for ProScrape property data
import type { ListingResponse as APIListingResponse } from '@/services/api'

// Core property interfaces with strict typing
export interface PropertyLocation {
  address?: string
  city?: string
  city_localized?: string
  district?: string
  district_localized?: string
  postal_code?: string
  latitude?: number
  longitude?: number
  region?: string
  country: string
}

export interface PropertyPricing {
  price?: number
  price_formatted?: string
  price_currency: string
  price_per_sqm?: number
  price_per_sqm_formatted?: string
  original_price?: number
  price_change?: PriceChange
  market_value_estimate?: MarketValueEstimate
}

export interface PriceChange {
  old_price: number
  new_price: number
  change_amount: number
  change_percentage: number
  change_type: 'increase' | 'decrease'
  changed_at: string
}

export interface MarketValueEstimate {
  estimated_value: number
  confidence_score: number
  comparable_properties: number
  last_updated: string
}

export interface PropertyFeatures {
  area_sqm?: number
  area_formatted?: string
  rooms?: number
  bedrooms?: number
  bathrooms?: number
  floor?: number
  total_floors?: number
  building_year?: number
  renovation_year?: number
  energy_rating?: EnergyRating
  parking_spaces?: number
  balcony_area?: number
  garden_area?: number
}

export interface EnergyRating {
  rating: 'A+' | 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G'
  consumption_kwh?: number
  emissions_kg?: number
  certificate_date?: string
}

export interface PropertyAmenities {
  features: string[]
  features_localized?: string[]
  amenities: string[]
  amenities_localized?: string[]
  accessibility_features?: string[]
  smart_home_features?: string[]
  security_features?: string[]
  outdoor_features?: string[]
}

export interface PropertyMedia {
  image_urls: string[]
  video_urls: string[]
  virtual_tour_url?: string
  floor_plan_urls?: string[]
  thumbnail_url?: string
  hero_image_url?: string
  image_metadata?: ImageMetadata[]
}

export interface ImageMetadata {
  url: string
  width?: number
  height?: number
  alt_text?: string
  caption?: string
  room_type?: string
  is_hero?: boolean
  sort_order?: number
}

export interface PropertySource {
  source_site: 'ss.com' | 'city24.lv' | 'pp.lv'
  source_url: string
  listing_id: string
  external_id?: string
  posted_date?: string
  posted_date_formatted?: string
  updated_date?: string
  updated_date_formatted?: string
  scraped_at: string
  scraped_at_formatted?: string
  data_quality_score?: number
}

export interface PropertyAnalytics {
  view_count?: number
  favorite_count?: number
  inquiry_count?: number
  last_viewed?: string
  trending_score?: number
  days_on_market?: number
  price_reduction_count?: number
}

// Enhanced main property interface
export interface Property extends APIListingResponse {
  // Enhanced location data
  location: PropertyLocation
  
  // Enhanced pricing data
  pricing: PropertyPricing
  
  // Enhanced features data
  features: PropertyFeatures
  
  // Enhanced amenities data
  amenities: PropertyAmenities
  
  // Enhanced media data
  media: PropertyMedia
  
  // Source and metadata
  source: PropertySource
  
  // Analytics data
  analytics?: PropertyAnalytics
  
  // Computed properties for UI
  display_title: string
  display_price: string
  display_location: string
  display_features: string[]
  is_featured: boolean
  is_new: boolean
  is_price_reduced: boolean
  quality_score: number
}

// Search and filtering interfaces
export interface PropertySearchFilters {
  // Text search
  query?: string
  
  // Location filters
  city?: string
  district?: string
  region?: string
  latitude?: number
  longitude?: number
  radius?: number // in km
  
  // Property type filters
  property_type?: PropertyType[]
  listing_type?: ListingType[]
  
  // Price filters
  min_price?: number
  max_price?: number
  price_currency?: string
  
  // Size filters
  min_area?: number
  max_area?: number
  min_rooms?: number
  max_rooms?: number
  min_bedrooms?: number
  max_bedrooms?: number
  
  // Building filters
  min_floor?: number
  max_floor?: number
  min_building_year?: number
  max_building_year?: number
  energy_rating?: EnergyRating['rating'][]
  
  // Feature filters
  has_parking?: boolean
  has_balcony?: boolean
  has_garden?: boolean
  has_elevator?: boolean
  has_basement?: boolean
  has_garage?: boolean
  furnished?: boolean
  pets_allowed?: boolean
  
  // Media filters
  has_images?: boolean
  has_video?: boolean
  has_virtual_tour?: boolean
  has_floor_plan?: boolean
  
  // Source filters
  source_sites?: ('ss.com' | 'city24.lv' | 'pp.lv')[]
  exclude_sources?: ('ss.com' | 'city24.lv' | 'pp.lv')[]
  
  // Date filters
  posted_from?: string
  posted_to?: string
  updated_from?: string
  updated_to?: string
  
  // Quality filters
  min_quality_score?: number
  exclude_duplicates?: boolean
  
  // Sorting
  sort_by?: PropertySortField
  sort_order?: 'asc' | 'desc'
  
  // Pagination
  page?: number
  limit?: number
  offset?: number
}

export type PropertyType = 
  | 'apartment' 
  | 'house' 
  | 'villa' 
  | 'townhouse' 
  | 'condo' 
  | 'studio' 
  | 'loft' 
  | 'penthouse' 
  | 'land' 
  | 'commercial' 
  | 'office' 
  | 'retail' 
  | 'warehouse' 
  | 'industrial' 
  | 'mixed_use' 
  | 'other'

export type ListingType = 'sell' | 'rent' | 'buy' | 'rent_wanted' | 'auction'

export type PropertySortField = 
  | 'posted_date' 
  | 'updated_date' 
  | 'price' 
  | 'price_per_sqm' 
  | 'area' 
  | 'rooms' 
  | 'quality_score' 
  | 'days_on_market' 
  | 'trending_score'

// Faceted search interfaces
export interface PropertyFacet {
  field: keyof PropertySearchFilters
  label: string
  type: 'range' | 'checkbox' | 'select' | 'multiselect' | 'toggle'
  options?: FacetOption[]
  min_value?: number
  max_value?: number
  current_min?: number
  current_max?: number
  step?: number
}

export interface FacetOption {
  value: string | number | boolean
  label: string
  count: number
  selected?: boolean
}

export interface PropertySearchResponse {
  properties: Property[]
  total: number
  page: number
  limit: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
  facets: PropertyFacet[]
  search_meta: SearchMetadata
}

export interface SearchMetadata {
  query?: string
  total_results: number
  search_time_ms: number
  applied_filters: Partial<PropertySearchFilters>
  suggestions?: SearchSuggestion[]
  location_suggestions?: LocationSuggestion[]
}

export interface SearchSuggestion {
  type: 'query' | 'filter' | 'location'
  text: string
  category?: string
  result_count: number
}

export interface LocationSuggestion {
  name: string
  type: 'city' | 'district' | 'region' | 'address'
  coordinates?: [number, number] // [lat, lng]
  bounds?: [[number, number], [number, number]] // [[sw_lat, sw_lng], [ne_lat, ne_lng]]
  result_count: number
}

// Saved searches and alerts
export interface PropertySavedSearch {
  id: string
  name: string
  filters: PropertySearchFilters
  created_at: string
  updated_at: string
  last_run: string
  result_count: number
  alert_enabled: boolean
  alert_frequency: 'immediate' | 'daily' | 'weekly'
  alert_email?: string
  alert_push?: boolean
}

export interface PropertyAlert {
  id: string
  saved_search_id: string
  property_id: string
  alert_type: 'new_listing' | 'price_change' | 'status_change'
  created_at: string
  read: boolean
  property: Property
}

// Comparison interface
export interface PropertyComparison {
  id: string
  name?: string
  properties: Property[]
  created_at: string
  updated_at: string
  comparison_fields: ComparisonField[]
}

export interface ComparisonField {
  field: keyof Property
  label: string
  type: 'text' | 'number' | 'currency' | 'area' | 'list' | 'boolean'
  highlight_differences: boolean
}

// Market analysis interfaces
export interface MarketAnalysis {
  location: PropertyLocation
  property_type: PropertyType
  time_period: 'month' | 'quarter' | 'year'
  analysis_date: string
  
  metrics: {
    average_price: number
    median_price: number
    price_per_sqm: number
    total_listings: number
    new_listings: number
    sold_listings: number
    price_trend: 'up' | 'down' | 'stable'
    price_change_percentage: number
    days_on_market_avg: number
    supply_demand_ratio: number
  }
  
  price_distribution: PriceDistribution[]
  size_distribution: SizeDistribution[]
  comparable_areas: ComparableArea[]
}

export interface PriceDistribution {
  range: string
  count: number
  percentage: number
}

export interface SizeDistribution {
  range: string
  count: number
  percentage: number
  avg_price: number
}

export interface ComparableArea {
  name: string
  average_price: number
  price_difference_percentage: number
  distance_km: number
}

// Export utility types
export type PropertyUpdatePayload = Partial<Omit<Property, 'id' | 'source' | 'analytics'>>
export type PropertyCreatePayload = Omit<Property, 'id' | 'analytics' | 'display_title' | 'display_price' | 'display_location' | 'display_features' | 'is_featured' | 'is_new' | 'is_price_reduced' | 'quality_score'>

// Constants for property types and features
export const PROPERTY_TYPES: { value: PropertyType; label: string; icon: string }[] = [
  { value: 'apartment', label: 'Apartment', icon: 'building-office-2' },
  { value: 'house', label: 'House', icon: 'home' },
  { value: 'villa', label: 'Villa', icon: 'home-modern' },
  { value: 'townhouse', label: 'Townhouse', icon: 'building-office' },
  { value: 'studio', label: 'Studio', icon: 'squares-2x2' },
  { value: 'land', label: 'Land', icon: 'map' },
  { value: 'commercial', label: 'Commercial', icon: 'building-storefront' }
]

export const LISTING_TYPES: { value: ListingType; label: string; color: string }[] = [
  { value: 'sell', label: 'For Sale', color: 'green' },
  { value: 'rent', label: 'For Rent', color: 'blue' },
  { value: 'auction', label: 'Auction', color: 'purple' }
]

export const ENERGY_RATINGS: EnergyRating['rating'][] = ['A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']

export const PRICE_RANGES = [
  { min: 0, max: 50000, label: 'Under €50k' },
  { min: 50000, max: 100000, label: '€50k - €100k' },
  { min: 100000, max: 200000, label: '€100k - €200k' },
  { min: 200000, max: 300000, label: '€200k - €300k' },
  { min: 300000, max: 500000, label: '€300k - €500k' },
  { min: 500000, max: undefined, label: 'Over €500k' }
]

export const AREA_RANGES = [
  { min: 0, max: 50, label: 'Under 50m²' },
  { min: 50, max: 100, label: '50m² - 100m²' },
  { min: 100, max: 150, label: '100m² - 150m²' },
  { min: 150, max: 200, label: '150m² - 200m²' },
  { min: 200, max: undefined, label: 'Over 200m²' }
]