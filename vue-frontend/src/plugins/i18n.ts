import { createI18n } from 'vue-i18n'
import { nextTick } from 'vue'

// Import translation files
import en from '@/locales/en.json'
import lv from '@/locales/lv.json'
import ru from '@/locales/ru.json'

// Supported languages configuration
export const SUPPORT_LOCALES = ['en', 'lv', 'ru'] as const
export type SupportedLocale = typeof SUPPORT_LOCALES[number]

export const LOCALE_INFO = {
  en: {
    name: 'English',
    nativeName: 'English',
    flag: '🇺🇸',
    rtl: false,
    dateFormat: 'MM/dd/yyyy',
    timeFormat: 'hh:mm a',
    currency: 'EUR',
    numberFormat: {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }
  },
  lv: {
    name: 'Latvian', 
    nativeName: 'Latviešu',
    flag: '🇱🇻',
    rtl: false,
    dateFormat: 'dd.MM.yyyy',
    timeFormat: 'HH:mm',
    currency: 'EUR',
    numberFormat: {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }
  },
  ru: {
    name: 'Russian',
    nativeName: 'Русский', 
    flag: '🇷🇺',
    rtl: false,
    dateFormat: 'dd.MM.yyyy',
    timeFormat: 'HH:mm',
    currency: 'EUR',
    numberFormat: {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }
  }
} as const

// Default locale
export const DEFAULT_LOCALE: SupportedLocale = 'en'

// Storage key for locale preference
export const LOCALE_STORAGE_KEY = 'proscrape-locale'

/**
 * Get locale from various sources with priority:
 * 1. localStorage
 * 2. URL parameter
 * 3. Browser language
 * 4. Default locale
 */
export function getLocale(): SupportedLocale {
  // Check localStorage first
  const storedLocale = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (storedLocale && SUPPORT_LOCALES.includes(storedLocale as SupportedLocale)) {
    return storedLocale as SupportedLocale
  }
  
  // Check URL parameter
  const urlParams = new URLSearchParams(window.location.search)
  const urlLocale = urlParams.get('lang')
  if (urlLocale && SUPPORT_LOCALES.includes(urlLocale as SupportedLocale)) {
    return urlLocale as SupportedLocale
  }
  
  // Check browser language
  const browserLang = navigator.language.split('-')[0]
  if (SUPPORT_LOCALES.includes(browserLang as SupportedLocale)) {
    return browserLang as SupportedLocale
  }
  
  return DEFAULT_LOCALE
}

/**
 * Set and persist locale
 */
export function setLocale(locale: SupportedLocale): void {
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  
  // Update HTML lang attribute
  document.documentElement.lang = locale
  
  // Update HTML dir attribute for RTL languages
  const localeInfo = LOCALE_INFO[locale]
  document.documentElement.dir = localeInfo.rtl ? 'rtl' : 'ltr'
}

/**
 * Setup locale for the app with lazy loading support
 */
export async function setupI18n(options: { 
  locale?: SupportedLocale
  lazyLoad?: boolean 
} = {}) {
  const { locale = getLocale(), lazyLoad = true } = options
  
  const i18n = createI18n({
    legacy: false, // Use Composition API mode
    locale,
    fallbackLocale: DEFAULT_LOCALE,
    globalInjection: true,
    messages: lazyLoad ? {
      // Only load default locale initially for lazy loading
      [DEFAULT_LOCALE]: DEFAULT_LOCALE === 'en' ? en : 
                       DEFAULT_LOCALE === 'lv' ? lv : ru
    } : {
      // Load all translations upfront for non-lazy loading
      en,
      lv, 
      ru
    },
    numberFormats: {
      en: {
        currency: {
          style: 'currency',
          currency: 'EUR',
          notation: 'standard',
        },
        decimal: {
          style: 'decimal',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        },
        percent: {
          style: 'percent',
          useGrouping: false,
        }
      },
      lv: {
        currency: {
          style: 'currency',
          currency: 'EUR',
          notation: 'standard',
          currencyDisplay: 'symbol',
        },
        decimal: {
          style: 'decimal',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
          useGrouping: true,
        },
        percent: {
          style: 'percent',
          useGrouping: false,
        }
      },
      ru: {
        currency: {
          style: 'currency',
          currency: 'EUR',
          notation: 'standard',
          currencyDisplay: 'symbol',
        },
        decimal: {
          style: 'decimal',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
          useGrouping: true,
        },
        percent: {
          style: 'percent',
          useGrouping: false,
        }
      }
    },
    datetimeFormats: {
      en: {
        short: {
          year: 'numeric',
          month: 'short',
          day: 'numeric'
        },
        long: {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          weekday: 'long'
        },
        time: {
          hour: 'numeric',
          minute: 'numeric'
        },
        datetime: {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: 'numeric'
        }
      },
      lv: {
        short: {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        },
        long: {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          weekday: 'long'
        },
        time: {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        },
        datetime: {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        }
      },
      ru: {
        short: {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        },
        long: {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          weekday: 'long'
        },
        time: {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        },
        datetime: {
          year: 'numeric',
          month: '2-digit', 
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        }
      }
    }
  })
  
  // Set initial locale
  await setI18nLanguage(i18n, locale)
  
  // If using lazy loading and the selected locale isn't the default, load it
  if (lazyLoad && locale !== DEFAULT_LOCALE) {
    await loadLocaleMessages(i18n, locale)
  }
  
  // Preload other translations in the background
  if (lazyLoad) {
    // Don't await this - let it load in the background
    preloadTranslations(SUPPORT_LOCALES.filter(l => l !== locale))
  }
  
  return i18n
}

/**
 * Set i18n language with side effects
 */
export function setI18nLanguage(i18n: any, locale: SupportedLocale) {
  i18n.global.locale.value = locale
  setLocale(locale)
  return nextTick()
}

/**
 * Load locale messages dynamically (for lazy loading)
 */
export async function loadLocaleMessages(i18n: any, locale: SupportedLocale) {
  // Check if already loaded
  if (i18n.global.availableLocales.includes(locale)) {
    return setI18nLanguage(i18n, locale)
  }
  
  try {
    // Dynamic import for lazy loading
    const messages = await import(`@/locales/${locale}.json`)
    
    // Set locale messages
    i18n.global.setLocaleMessage(locale, messages.default)
    
    console.log(`✅ Loaded ${locale} translations`)
    
    return setI18nLanguage(i18n, locale)
  } catch (error) {
    console.error(`❌ Failed to load ${locale} translations:`, error)
    
    // Fallback to default locale if loading fails
    if (locale !== DEFAULT_LOCALE) {
      console.warn(`🔄 Falling back to ${DEFAULT_LOCALE} locale`)
      return setI18nLanguage(i18n, DEFAULT_LOCALE)
    }
    
    throw error
  }
}

/**
 * Preload translation files for better performance
 */
export async function preloadTranslations(locales: SupportedLocale[] = SUPPORT_LOCALES) {
  const preloadPromises = locales.map(async (locale) => {
    try {
      // Use dynamic import to preload but don't wait for all
      await import(`@/locales/${locale}.json`)
      console.log(`📦 Preloaded ${locale} translations`)
    } catch (error) {
      console.warn(`⚠️ Failed to preload ${locale} translations:`, error)
    }
  })
  
  // Don't wait for all to complete, just start the loading process
  Promise.allSettled(preloadPromises)
}

/**
 * Route helper for language-based routing
 */
export function getLocalizedPath(path: string, locale?: SupportedLocale): string {
  const currentLocale = locale || getLocale()
  
  // Don't add locale prefix for default locale
  if (currentLocale === DEFAULT_LOCALE) {
    return path
  }
  
  // Add locale prefix
  return `/${currentLocale}${path === '/' ? '' : path}`
}

/**
 * Extract locale from path
 */
export function getLocaleFromPath(path: string): { locale: SupportedLocale; path: string } {
  const segments = path.split('/').filter(Boolean)
  
  if (segments.length > 0 && SUPPORT_LOCALES.includes(segments[0] as SupportedLocale)) {
    return {
      locale: segments[0] as SupportedLocale,
      path: '/' + segments.slice(1).join('/')
    }
  }
  
  return {
    locale: DEFAULT_LOCALE,
    path
  }
}

/**
 * Format currency based on locale
 */
export function formatCurrency(amount: number, locale: SupportedLocale = getLocale()): string {
  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
  
  return formatter.format(amount)
}

/**
 * Format area with units based on locale
 */
export function formatArea(area: number, locale: SupportedLocale = getLocale()): string {
  const formatter = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  })
  
  return `${formatter.format(area)} m²`
}

/**
 * Format date based on locale
 */
export function formatDate(date: Date | string, locale: SupportedLocale = getLocale(), format: 'short' | 'long' | 'datetime' = 'short'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  
  const formatter = new Intl.DateTimeFormat(locale, 
    format === 'short' ? { year: 'numeric', month: '2-digit', day: '2-digit' } :
    format === 'long' ? { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' } :
    { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
  )
  
  return formatter.format(dateObj)
}

/**
 * Pluralization helper for different languages
 */
export function pluralize(count: number, key: string, locale: SupportedLocale = getLocale()): string {
  // This is a simplified pluralization - Vue i18n handles this better
  if (locale === 'ru') {
    // Russian pluralization rules
    const mod10 = count % 10
    const mod100 = count % 100
    
    if (mod100 >= 11 && mod100 <= 14) {
      return `${key}s` // many form
    } else if (mod10 === 1) {
      return key // one form
    } else if (mod10 >= 2 && mod10 <= 4) {
      return `${key}s` // few form  
    } else {
      return `${key}s` // many form
    }
  } else if (locale === 'lv') {
    // Latvian pluralization rules
    const mod10 = count % 10
    const mod100 = count % 100
    
    if (count === 0) {
      return `${key}s` // zero form
    } else if (mod100 === 11 || mod10 !== 1) {
      return `${key}s` // many form
    } else {
      return key // one form
    }
  } else {
    // English pluralization
    return count === 1 ? key : `${key}s`
  }
}

export default setupI18n