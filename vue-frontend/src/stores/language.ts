import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { 
  type SupportedLocale, 
  DEFAULT_LOCALE, 
  SUPPORT_LOCALES, 
  LOCALE_INFO,
  getLocale,
  setLocale 
} from '@/plugins/i18n'

export const useLanguageStore = defineStore('language', () => {
  // State
  const currentLocale = ref<SupportedLocale>(getLocale())
  const isRTL = ref(false)
  
  // Getters
  const localeInfo = computed(() => LOCALE_INFO[currentLocale.value])
  const availableLocales = computed(() => SUPPORT_LOCALES)
  const isDefaultLocale = computed(() => currentLocale.value === DEFAULT_LOCALE)
  
  // Actions
  const setCurrentLocale = (locale: SupportedLocale) => {
    if (SUPPORT_LOCALES.includes(locale)) {
      currentLocale.value = locale
      setLocale(locale)
      isRTL.value = LOCALE_INFO[locale].rtl
    }
  }
  
  const toggleRTL = () => {
    isRTL.value = !isRTL.value
    document.documentElement.dir = isRTL.value ? 'rtl' : 'ltr'
  }
  
  const resetToDefault = () => {
    setCurrentLocale(DEFAULT_LOCALE)
  }
  
  // Formatting helpers (using current locale)
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat(currentLocale.value, {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }
  
  const formatArea = (area: number): string => {
    const formatter = new Intl.NumberFormat(currentLocale.value, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    })
    return `${formatter.format(area)} m²`
  }
  
  const formatDate = (date: Date | string, format: 'short' | 'long' | 'datetime' = 'short'): string => {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    
    const options: Intl.DateTimeFormatOptions = 
      format === 'short' ? { year: 'numeric', month: '2-digit', day: '2-digit' } :
      format === 'long' ? { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' } :
      { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
    
    return new Intl.DateTimeFormat(currentLocale.value, options).format(dateObj)
  }
  
  const formatNumber = (num: number, options?: Intl.NumberFormatOptions): string => {
    return new Intl.NumberFormat(currentLocale.value, options).format(num)
  }
  
  // Initialize store
  const initialize = () => {
    const savedLocale = getLocale()
    setCurrentLocale(savedLocale)
  }
  
  return {
    // State
    currentLocale,
    isRTL,
    
    // Getters
    localeInfo,
    availableLocales,
    isDefaultLocale,
    
    // Actions
    setLocale: setCurrentLocale,
    toggleRTL,
    resetToDefault,
    initialize,
    
    // Formatters
    formatCurrency,
    formatArea,
    formatDate,
    formatNumber,
  }
})

// Type exports for better TypeScript support
export type LanguageStore = ReturnType<typeof useLanguageStore>