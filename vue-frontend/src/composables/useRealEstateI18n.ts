import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLanguageStore } from '@/stores/language'  
import { useSEOi18n } from './useSEOi18n'
import type { SupportedLocale } from '@/plugins/i18n'
import type { ListingResponse } from '@/services/api'

/**
 * Real Estate specific internationalization composable
 * Provides specialized formatting and translations for property data
 */
export function useRealEstateI18n() {
  const { t, locale } = useI18n()
  const languageStore = useLanguageStore()
  
  const currentLocale = computed(() => locale.value as SupportedLocale)

  /**
   * Format property price with currency and optional context
   */
  const formatPropertyPrice = (
    amount: number | null | undefined,
    options: {
      context?: 'sale' | 'rent' | 'per_sqm' | 'per_hectare'
      showCurrency?: boolean
      compact?: boolean
    } = {}
  ): string => {
    if (!amount || amount <= 0) {
      return t('common.price_on_request', 'Price on request')
    }

    const { context, showCurrency = true, compact = false } = options
    
    // Format the base amount
    let formattedAmount: string
    if (compact && amount >= 1000000) {
      formattedAmount = `${(amount / 1000000).toFixed(1)}M`
    } else if (compact && amount >= 1000) {
      formattedAmount = `${(amount / 1000).toFixed(0)}k`
    } else {
      formattedAmount = new Intl.NumberFormat(currentLocale.value, {
        style: showCurrency ? 'currency' : 'decimal',
        currency: 'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(amount)
    }

    // Add context suffix
    switch (context) {
      case 'rent':
        return `${formattedAmount} ${t('units.per_month')}`
      case 'per_sqm':
        return `${formattedAmount} ${t('formats.price_per_sqm')}`
      case 'per_hectare':
        return `${formattedAmount} ${t('formats.price_per_hectare')}`
      default:
        return formattedAmount
    }
  }

  /**
   * Format property area with appropriate units
   */
  const formatPropertyArea = (
    area: number | null | undefined,
    options: {
      unit?: 'sqm' | 'hectare' | 'sqft'
      precision?: number
      showUnit?: boolean
    } = {}
  ): string => {
    if (!area || area <= 0) {
      return t('common.not_specified', 'Not specified')
    }

    const { unit = 'sqm', precision = 1, showUnit = true } = options
    
    let convertedArea = area
    let unitSymbol = 'm²'

    switch (unit) {
      case 'hectare':
        convertedArea = area / 10000
        unitSymbol = t('units.hectare', 'ha')
        break
      case 'sqft':
        convertedArea = area * 10.764
        unitSymbol = 'sq ft'
        break
      default:
        unitSymbol = 'm²'
    }

    const formatter = new Intl.NumberFormat(currentLocale.value, {
      minimumFractionDigits: 0,
      maximumFractionDigits: precision,
    })

    const formattedArea = formatter.format(convertedArea)
    return showUnit ? `${formattedArea} ${unitSymbol}` : formattedArea
  }

  /**
   * Format property rooms with proper pluralization
   */
  const formatPropertyRooms = (
    rooms: number | null | undefined,
    options: { showLabel?: boolean } = {}
  ): string => {
    if (!rooms || rooms <= 0) {
      return t('common.not_specified', 'Not specified')
    }

    const { showLabel = true } = options
    
    if (!showLabel) {
      return rooms.toString()
    }

    // Handle pluralization based on locale
    if (currentLocale.value === 'ru') {
      // Russian pluralization rules
      const mod10 = rooms % 10
      const mod100 = rooms % 100
      
      let key: string
      if (mod100 >= 11 && mod100 <= 14) {
        key = 'units.rooms_many' // комнат
      } else if (mod10 === 1) {
        key = 'units.room_one' // комната
      } else if (mod10 >= 2 && mod10 <= 4) {
        key = 'units.rooms_few' // комнаты
      } else {
        key = 'units.rooms_many' // комнат
      }
      
      return `${rooms} ${t(key, t('units.rooms'))}`
    } else if (currentLocale.value === 'lv') {
      // Latvian pluralization rules
      const key = rooms === 1 ? 'units.room' : 'units.rooms'
      return `${rooms} ${t(key)}`
    } else {
      // English pluralization
      const key = rooms === 1 ? 'units.room' : 'units.rooms'
      return `${rooms} ${t(key)}`
    }
  }

  /**
   * Format property floor information
   */
  const formatPropertyFloor = (
    floor: number | null | undefined,
    totalFloors?: number | null | undefined,
    options: { showTotal?: boolean } = {}
  ): string => {
    if (!floor) {
      return t('common.not_specified', 'Not specified')
    }

    const { showTotal = true } = options
    
    let floorText = floor.toString()
    
    // Handle ground floor and basement
    if (floor === 0) {
      floorText = t('property.ground_floor', 'Ground floor')
    } else if (floor < 0) {
      floorText = t('property.basement', 'Basement')
    }

    if (showTotal && totalFloors && totalFloors > 0) {
      return `${floorText}/${totalFloors} ${t('units.floor')}`
    }

    return `${floorText} ${t('units.floor')}`
  }

  /**
   * Format property date with locale-specific formatting
   */
  const formatPropertyDate = (
    date: Date | string | null | undefined,
    options: {
      format?: 'short' | 'long' | 'relative'
      showTime?: boolean
    } = {}
  ): string => {
    if (!date) {
      return t('common.not_specified', 'Not specified')
    }

    const { format = 'short', showTime = false } = options
    const dateObj = typeof date === 'string' ? new Date(date) : date

    if (format === 'relative') {
      const now = new Date()
      const diffInDays = Math.floor((now.getTime() - dateObj.getTime()) / (1000 * 60 * 60 * 24))
      
      if (diffInDays === 0) {
        return t('dates.today', 'Today')
      } else if (diffInDays === 1) {
        return t('dates.yesterday', 'Yesterday')
      } else if (diffInDays < 7) {
        return t('dates.days_ago', '{count} days ago', { count: diffInDays })
      } else if (diffInDays < 30) {
        const weeks = Math.floor(diffInDays / 7)
        return t('dates.weeks_ago', '{count} weeks ago', { count: weeks })
      } else if (diffInDays < 365) {
        const months = Math.floor(diffInDays / 30)
        return t('dates.months_ago', '{count} months ago', { count: months })
      } else {
        const years = Math.floor(diffInDays / 365)
        return t('dates.years_ago', '{count} years ago', { count: years })
      }
    }

    return languageStore.formatDate(dateObj, format)
  }

  /**
   * Translate property type with proper localization
   */
  const translatePropertyType = (
    propertyType: string | null | undefined
  ): string => {
    if (!propertyType) {
      return t('common.not_specified', 'Not specified')
    }

    const key = `types.${propertyType.toLowerCase().replace(/\s+/g, '_')}`
    return t(key, propertyType)
  }

  /**
   * Translate listing type with proper localization
   */
  const translateListingType = (
    listingType: string | null | undefined
  ): string => {
    if (!listingType) {
      return t('common.not_specified', 'Not specified')
    }

    const key = `listing_types.${listingType.toLowerCase()}`
    return t(key, listingType)
  }

  /**
   * Translate property features array
   */
  const translatePropertyFeatures = (
    features: string[] | null | undefined,
    options: { limit?: number } = {}
  ): string[] => {
    if (!features || features.length === 0) {
      return []
    }

    const { limit } = options
    const featuresToTranslate = limit ? features.slice(0, limit) : features

    return featuresToTranslate.map(feature => {
      const key = `features.${feature.toLowerCase().replace(/\s+/g, '_')}`
      return t(key, feature)
    })
  }

  /**
   * Translate city name with proper localization
   */
  const translateCityName = (
    cityName: string | null | undefined
  ): string => {
    if (!cityName) {
      return t('common.not_specified', 'Not specified')
    }

    const key = `cities.${cityName.toLowerCase().replace(/\s+/g, '_')}`
    return t(key, cityName)
  }

  /**
   * Translate district name with proper localization
   */
  const translateDistrictName = (
    districtName: string | null | undefined
  ): string => {
    if (!districtName) {
      return t('common.not_specified', 'Not specified')
    }

    const key = `districts.${districtName.toLowerCase().replace(/\s+/g, '_')}`
    return t(key, districtName)
  }

  /**
   * Format complete property address
   */
  const formatPropertyAddress = (
    address: {
      street?: string | null
      city?: string | null
      district?: string | null
      country?: string | null
    }
  ): string => {
    const parts: string[] = []

    if (address.street) {
      parts.push(address.street)
    }

    if (address.district) {
      parts.push(translateDistrictName(address.district))
    }

    if (address.city) {
      parts.push(translateCityName(address.city))
    }

    if (address.country && address.country.toLowerCase() !== 'latvia') {
      parts.push(address.country)
    }

    return parts.join(', ') || t('common.address_not_available', 'Address not available')
  }

  /**
   * Format property energy efficiency rating
   */
  const formatEnergyRating = (
    rating: string | number | null | undefined
  ): string => {
    if (!rating) {
      return t('property.energy_rating_not_available', 'Not available')
    }

    if (typeof rating === 'number') {
      // Convert numeric rating to letter grade
      if (rating >= 90) return 'A+'
      if (rating >= 80) return 'A'
      if (rating >= 70) return 'B'
      if (rating >= 60) return 'C'
      if (rating >= 50) return 'D'
      if (rating >= 40) return 'E'
      if (rating >= 30) return 'F'
      return 'G'
    }

    return rating.toString().toUpperCase()
  }

  /**
   * Format price range for filters
   */
  const formatPriceRange = (
    minPrice?: number | null,
    maxPrice?: number | null
  ): string => {
    if (!minPrice && !maxPrice) {
      return t('search.filters.any_price', 'Any price')
    }

    if (minPrice && !maxPrice) {
      return `${t('search.filters.from')} ${formatPropertyPrice(minPrice)}`
    }

    if (!minPrice && maxPrice) {
      return `${t('search.filters.up_to')} ${formatPropertyPrice(maxPrice)}`
    }

    return `${formatPropertyPrice(minPrice!)} - ${formatPropertyPrice(maxPrice!)}`
  }

  /**
   * Format area range for filters
   */
  const formatAreaRange = (
    minArea?: number | null,
    maxArea?: number | null
  ): string => {
    if (!minArea && !maxArea) {
      return t('search.filters.any_area', 'Any area')
    }

    if (minArea && !maxArea) {
      return `${t('search.filters.from')} ${formatPropertyArea(minArea)}`
    }

    if (!minArea && maxArea) {
      return `${t('search.filters.up_to')} ${formatPropertyArea(maxArea)}`
    }

    return `${formatPropertyArea(minArea!)} - ${formatPropertyArea(maxArea!)}`
  }

  /**
   * Localize a complete property object with all fields
   */
  const localizeProperty = (property: ListingResponse): ListingResponse => {
    return {
      ...property,
      // Localized strings
      property_type_localized: translatePropertyType(property.property_type),
      listing_type_localized: translateListingType(property.listing_type),
      city_localized: property.city ? translateCityName(property.city) : null,
      district_localized: property.district ? translateDistrictName(property.district) : null,
      features_localized: property.features ? translatePropertyFeatures(property.features) : null,
      
      // Formatted values
      price_formatted: formatPropertyPrice(property.price, {
        context: property.listing_type === 'rent' ? 'rent' : undefined
      }),
      area_formatted: property.area_sqm ? formatPropertyArea(property.area_sqm) : null,
      rooms_formatted: property.rooms ? formatPropertyRooms(property.rooms) : null,
      floor_formatted: formatPropertyFloor(property.floor, property.total_floors),
      posted_date_formatted: property.posted_date ? formatPropertyDate(property.posted_date, { format: 'relative' }) : null,
      updated_date_formatted: property.updated_date ? formatPropertyDate(property.updated_date, { format: 'relative' }) : null,
      
      // Address
      address_formatted: formatPropertyAddress({
        street: property.address,
        city: property.city,
        district: property.district,
        country: 'Latvia'
      })
    }
  }

  /**
   * Localize multiple properties efficiently
   */
  const localizeProperties = (properties: ListingResponse[]): ListingResponse[] => {
    return properties.map(localizeProperty)
  }

  /**
   * Get localized search suggestions
   */
  const getSearchSuggestions = (query: string): { 
    cities: Array<{ key: string; label: string; type: 'city' }>
    propertyTypes: Array<{ key: string; label: string; type: 'property_type' }>
    features: Array<{ key: string; label: string; type: 'feature' }>
  } => {
    const queryLower = query.toLowerCase()
    
    // City suggestions
    const cityKeys = [
      'riga', 'jurmala', 'liepaja', 'daugavpils', 'jelgava', 'ventspils',
      'rezekne', 'valmiera', 'jekabpils', 'ogre', 'tukums', 'salaspils',
      'cesis', 'kuldiga', 'saldus', 'talsi', 'dobele', 'bauska', 'sigulda'
    ]
    
    const cities = cityKeys
      .map(key => ({ key, label: translateCityName(key), type: 'city' as const }))
      .filter(city => city.label.toLowerCase().includes(queryLower))
      .slice(0, 5)

    // Property type suggestions
    const propertyTypeKeys = [
      'apartment', 'house', 'land', 'commercial', 'office', 'warehouse',
      'garage', 'room', 'new_development', 'villa', 'townhouse', 'studio'
    ]
    
    const propertyTypes = propertyTypeKeys
      .map(key => ({ key, label: translatePropertyType(key), type: 'property_type' as const }))
      .filter(type => type.label.toLowerCase().includes(queryLower))
      .slice(0, 5)

    // Feature suggestions
    const featureKeys = [
      'balcony', 'terrace', 'garden', 'parking', 'garage', 'elevator',
      'sauna', 'swimming_pool', 'fireplace', 'air_conditioning', 'furnished'
    ]
    
    const features = featureKeys
      .map(key => ({ key, label: t(`features.${key}`), type: 'feature' as const }))
      .filter(feature => feature.label.toLowerCase().includes(queryLower))
      .slice(0, 5)

    return { cities, propertyTypes, features }
  }

  /**
   * Generate breadcrumb navigation with localization
   */
  const getBreadcrumbs = (params: {
    city?: string
    propertyType?: string
    listingType?: string
    propertyId?: string
  }) => {
    const breadcrumbs = [
      { label: t('navigation.home'), path: '/' }
    ]

    if (params.city || params.propertyType || params.listingType) {
      breadcrumbs.push({ 
        label: t('navigation.search'), 
        path: '/search' 
      })
    }

    if (params.city) {
      breadcrumbs.push({
        label: translateCityName(params.city),
        path: `/search?city=${params.city}`
      })
    }

    if (params.propertyType) {
      breadcrumbs.push({
        label: translatePropertyType(params.propertyType),
        path: `/search?property_type=${params.propertyType}${params.city ? `&city=${params.city}` : ''}`
      })
    }

    if (params.propertyId) {
      breadcrumbs.push({
        label: t('property.details'),
        path: `/property/${params.propertyId}`
      })
    }

    return breadcrumbs
  }

  /**
   * Get SEO utilities integrated with real estate i18n
   */
  const getSEOUtils = () => {
    try {
      return useSEOi18n()
    } catch (error) {
      console.warn('SEO i18n not available:', error)
      return null
    }
  }

  /**
   * Format property for sharing (social media, etc.)
   */
  const formatPropertyForSharing = (property: ListingResponse) => {
    const price = formatPropertyPrice(property.price, {
      context: property.listing_type === 'rent' ? 'rent' : undefined
    })
    const propertyType = translatePropertyType(property.property_type)
    const city = property.city ? translateCityName(property.city) : ''

    return {
      title: `${property.title} - ${price}`,
      description: [
        propertyType,
        property.rooms ? formatPropertyRooms(property.rooms) : null,
        property.area_sqm ? formatPropertyArea(property.area_sqm) : null,
        city ? `${t('property.location')}: ${city}` : null
      ].filter(Boolean).join(' • '),
      url: `${window.location.origin}/property/${property.id}`,
      image: property.image_urls?.[0] || null
    }
  }

  /**
   * Get validation messages for forms with localization
   */
  const getValidationMessages = () => {
    return {
      required: (field: string) => t('validation.required', '{field} is required', { field }),
      min: (field: string, min: number) => t('validation.min', '{field} must be at least {min}', { field, min }),
      max: (field: string, max: number) => t('validation.max', '{field} must be no more than {max}', { field, max }),
      email: (field: string) => t('validation.email', '{field} must be a valid email', { field }),
      phone: (field: string) => t('validation.phone', '{field} must be a valid phone number', { field }),
      price: (field: string) => t('validation.price', '{field} must be a valid price', { field }),
      area: (field: string) => t('validation.area', '{field} must be a valid area', { field })
    }
  }

  return {
    // Price formatting
    formatPropertyPrice,
    formatPriceRange,
    
    // Area formatting
    formatPropertyArea,
    formatAreaRange,
    
    // Property details
    formatPropertyRooms,
    formatPropertyFloor,
    formatPropertyDate,
    formatEnergyRating,
    
    // Translations
    translatePropertyType,
    translateListingType,
    translatePropertyFeatures,
    translateCityName,
    translateDistrictName,
    
    // Address formatting
    formatPropertyAddress,
    
    // Complete localization
    localizeProperty,
    localizeProperties,
    
    // Search and navigation
    getSearchSuggestions,
    getBreadcrumbs,
    
    // Sharing and SEO
    formatPropertyForSharing,
    getSEOUtils,
    
    // Form validation
    getValidationMessages,
    
    // Utility
    currentLocale
  }
}