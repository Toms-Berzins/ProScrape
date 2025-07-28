import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useHead } from '@vueuse/head'
import { useRoute } from 'vue-router'
import { useRealEstateI18n } from './useRealEstateI18n'
import type { SupportedLocale } from '@/plugins/i18n'
import type { ListingResponse } from '@/services/api'

interface SEOMetaOptions {
  title?: string
  description?: string
  keywords?: string[]
  ogTitle?: string
  ogDescription?: string
  ogImage?: string
  ogType?: string
  canonicalUrl?: string
  alternateUrls?: { [key: string]: string }
  structuredData?: any
}

/**
 * SEO internationalization composable
 * Provides localized meta tags, Open Graph data, and structured data
 */
export function useSEOi18n() {
  const { t, locale } = useI18n()
  const route = useRoute()
  const { 
    formatPropertyPrice, 
    translatePropertyType, 
    translateCityName,
    translateDistrictName,
    formatPropertyArea,
    formatPropertyRooms
  } = useRealEstateI18n()

  const currentLocale = computed(() => locale.value as SupportedLocale)

  /**
   * Generate localized meta tags for property listings page
   */
  const setPropertyListingsMeta = (options: {
    city?: string
    propertyType?: string
    listingType?: string
    totalCount?: number
  } = {}) => {
    const { city, propertyType, listingType, totalCount } = options
    
    // Build localized title
    let titleParts: string[] = []
    
    if (listingType) {
      titleParts.push(t(`listing_types.${listingType}`))
    }
    
    if (propertyType) {
      titleParts.push(t(`types.${propertyType}`))
    }
    
    if (city) {
      titleParts.push(translateCityName(city))
    }
    
    titleParts.push(t('navigation.search'))
    
    const title = titleParts.join(' - ') + ' | ProScrape'
    
    // Build localized description
    let description = t('seo.property_listings_description', 
      'Find your perfect property in Latvia. Browse apartments, houses, and commercial properties with detailed information and photos.'
    )
    
    if (city && propertyType) {
      description = t('seo.specific_property_search', 
        'Find {propertyType} in {city}. Browse available properties with detailed information, photos, and pricing.',
        { 
          propertyType: t(`types.${propertyType}`).toLowerCase(), 
          city: translateCityName(city) 
        }
      )
    }
    
    if (totalCount !== undefined) {
      description += ` ${t('seo.found_properties', 'Found {count} properties.', { count: totalCount })}`
    }

    // Generate keywords
    const keywords = [
      t('seo.keywords.real_estate', 'real estate'),
      t('seo.keywords.property', 'property'),
      t('seo.keywords.latvia', 'Latvia'),
      'ProScrape'
    ]
    
    if (city) {
      keywords.push(translateCityName(city))
    }
    
    if (propertyType) {
      keywords.push(t(`types.${propertyType}`).toLowerCase())
    }
    
    if (listingType) {
      keywords.push(t(`listing_types.${listingType}`).toLowerCase())
    }

    return setMeta({
      title,
      description,
      keywords,
      ogTitle: title,
      ogDescription: description,
      ogType: 'website'
    })
  }

  /**
   * Generate localized meta tags for individual property page
   */
  const setPropertyDetailMeta = (property: ListingResponse) => {
    // Build localized title
    const price = formatPropertyPrice(property.price)
    const propertyType = translatePropertyType(property.property_type)
    const city = property.city ? translateCityName(property.city) : ''
    
    const title = `${property.title} - ${price} | ${propertyType} ${city ? `in ${city}` : ''} | ProScrape`
    
    // Build localized description
    let descriptionParts: string[] = []
    
    descriptionParts.push(property.title)
    descriptionParts.push(t('seo.property_detail_price', 'Price: {price}', { price }))
    
    if (property.area_sqm) {
      descriptionParts.push(t('seo.property_detail_area', 'Area: {area}', { 
        area: formatPropertyArea(property.area_sqm) 
      }))
    }
    
    if (property.rooms) {
      descriptionParts.push(formatPropertyRooms(property.rooms))
    }
    
    if (city) {
      descriptionParts.push(t('seo.property_detail_location', 'Located in {city}', { city }))
    }
    
    const description = descriptionParts.join('. ') + '.'

    // Generate keywords
    const keywords = [
      t('seo.keywords.real_estate', 'real estate'),
      propertyType.toLowerCase(),
      city.toLowerCase(),
      t('seo.keywords.property', 'property'),
      t('seo.keywords.latvia', 'Latvia'),
      'ProScrape'
    ]
    
    if (property.district) {
      keywords.push(translateDistrictName(property.district).toLowerCase())
    }

    // Structured data for property
    const structuredData = {
      '@context': 'https://schema.org',
      '@type': 'RealEstateListing',
      name: property.title,
      description: property.description || description,
      url: `${window.location.origin}/property/${property.id}`,
      identifier: property.id,
      datePosted: property.posted_date,
      offers: {
        '@type': 'Offer',
        price: property.price,
        priceCurrency: 'EUR',
        availability: 'InStock',
        priceSpecification: {
          '@type': 'PriceSpecification',
          price: property.price,
          priceCurrency: 'EUR'
        }
      },
      containedInPlace: {
        '@type': 'City',
        name: city,
        containedInPlace: {
          '@type': 'Country',
          name: t('seo.keywords.latvia', 'Latvia')
        }
      }
    }

    // Add property specific data
    if (property.area_sqm) {
      structuredData['floorSize'] = {
        '@type': 'QuantitativeValue',
        value: property.area_sqm,
        unitCode: 'MTK' // Square meter
      }
    }

    if (property.rooms) {
      structuredData['numberOfRooms'] = property.rooms
    }

    if (property.latitude && property.longitude) {
      structuredData['geo'] = {
        '@type': 'GeoCoordinates',
        latitude: property.latitude,
        longitude: property.longitude
      }
    }

    return setMeta({
      title,
      description,
      keywords,
      ogTitle: title,
      ogDescription: description,
      ogImage: property.image_urls?.[0],
      ogType: 'article',
      structuredData
    })
  }

  /**
   * Generate localized meta tags for map page
   */
  const setMapMeta = (options: {
    bounds?: { north: number; south: number; east: number; west: number }
    city?: string
    propertyCount?: number
  } = {}) => {
    const { city, propertyCount } = options
    
    let title = t('seo.map_title', 'Property Map - Interactive Real Estate Search')
    let description = t('seo.map_description', 
      'Explore properties on an interactive map. View locations, prices, and details of available real estate in Latvia.'
    )
    
    if (city) {
      title = t('seo.map_city_title', 'Property Map - {city} Real Estate', { city: translateCityName(city) })
      description = t('seo.map_city_description', 
        'Explore properties in {city} on an interactive map. View locations, prices, and details of available real estate.',
        { city: translateCityName(city) }
      )
    }
    
    if (propertyCount !== undefined) {
      description += ` ${t('seo.found_properties', 'Found {count} properties.', { count: propertyCount })}`
    }

    title += ' | ProScrape'

    const keywords = [
      t('seo.keywords.property_map', 'property map'),
      t('seo.keywords.real_estate', 'real estate'),
      t('seo.keywords.interactive_search', 'interactive search'),
      t('seo.keywords.latvia', 'Latvia'),
      'ProScrape'
    ]
    
    if (city) {
      keywords.push(translateCityName(city))
    }

    return setMeta({
      title,
      description,
      keywords,
      ogTitle: title,
      ogDescription: description,
      ogType: 'website'
    })
  }

  /**
   * Set general meta tags with localization
   */
  const setMeta = (options: SEOMetaOptions) => {
    const {
      title,
      description,
      keywords = [],
      ogTitle,
      ogDescription,
      ogImage,
      ogType = 'website',
      canonicalUrl,
      alternateUrls,
      structuredData
    } = options

    // Build canonical URL
    const baseUrl = window.location.origin
    const canonical = canonicalUrl || `${baseUrl}${route.path}`
    
    // Build alternate URLs for different languages if not provided
    const alternates = alternateUrls || {
      en: `${baseUrl}${route.path.replace(/^\/(lv|ru)/, '')}`,
      lv: `${baseUrl}/lv${route.path.replace(/^\/(lv|ru)/, '')}`,
      ru: `${baseUrl}/ru${route.path.replace(/^\/(lv|ru)/, '')}`
    }

    // Use vueuse/head to set meta tags
    useHead({
      title,
      meta: [
        // Basic meta tags
        { name: 'description', content: description },
        { name: 'keywords', content: keywords.join(', ') },
        { name: 'robots', content: 'index, follow' },
        { name: 'language', content: currentLocale.value },
        
        // Open Graph tags
        { property: 'og:title', content: ogTitle || title },
        { property: 'og:description', content: ogDescription || description },
        { property: 'og:type', content: ogType },
        { property: 'og:url', content: canonical },
        { property: 'og:site_name', content: 'ProScrape' },
        { property: 'og:locale', content: currentLocale.value === 'en' ? 'en_US' : currentLocale.value === 'lv' ? 'lv_LV' : 'ru_RU' },
        
        // Twitter Card tags
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: ogTitle || title },
        { name: 'twitter:description', content: ogDescription || description },
        
        // Additional meta tags
        { name: 'author', content: 'ProScrape' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1.0' },
        { 'http-equiv': 'Content-Language', content: currentLocale.value }
      ].concat(
        // Add og:image if provided
        ogImage ? [{ property: 'og:image', content: ogImage }] : [],
        // Add twitter:image if provided
        ogImage ? [{ name: 'twitter:image', content: ogImage }] : []
      ),
      
      link: [
        // Canonical URL
        { rel: 'canonical', href: canonical },
        
        // Alternate language versions
        ...Object.entries(alternates).map(([lang, url]) => ({
          rel: 'alternate',
          hreflang: lang,
          href: url
        }))
      ],
      
      // Structured data
      script: structuredData ? [{
        type: 'application/ld+json',
        innerHTML: JSON.stringify(structuredData)
      }] : []
    })

    return {
      title,
      description,
      keywords,
      canonical,
      alternates,
      structuredData
    }
  }

  return {
    setMeta,
    setPropertyListingsMeta,
    setPropertyDetailMeta,
    setMapMeta,
    currentLocale
  }
}