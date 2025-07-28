import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { useLanguageStore } from '@/stores/language'
import { getLocale, type SupportedLocale } from '@/plugins/i18n'

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const I18N_BASE_URL = `${API_BASE_URL}/i18n`

// Response types based on FastAPI backend
export interface ApiResponse<T = any> {
  data?: T
  message?: string
  error?: string
  language?: string
}

export interface ListingResponse {
  id: string
  listing_id: string
  source_site: string
  title: string
  description?: string
  price?: number
  price_formatted?: string
  price_currency: string
  property_type?: string
  property_type_localized?: string
  listing_type?: string
  listing_type_localized?: string
  area_sqm?: number
  area_formatted?: string
  rooms?: number
  floor?: number
  total_floors?: number
  address?: string
  city?: string
  city_localized?: string
  district?: string
  district_localized?: string
  postal_code?: string
  latitude?: number
  longitude?: number
  features: string[]
  features_localized: string[]
  amenities: string[]
  amenities_localized: string[]
  image_urls: string[]
  video_urls: string[]
  posted_date?: string
  posted_date_formatted?: string
  updated_date?: string
  updated_date_formatted?: string
  scraped_at: string
  scraped_at_formatted?: string
  source_url: string
  language: string
  available_languages: string[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
  language: string
}

export interface SearchFilters {
  page?: number
  limit?: number
  city?: string
  property_type?: string
  listing_type?: string
  min_price?: number
  max_price?: number
  min_area?: number
  max_area?: number
  source_site?: string
  date_from?: string
  date_to?: string
  north?: number
  south?: number
  east?: number
  west?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface SupportedLanguagesResponse {
  supported_languages: Record<string, { name: string; native: string }>
  current_language: string
  default_language: string
  message: string
}

// Create axios instance
class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor - add language headers
    this.client.interceptors.request.use(
      (config) => {
        const currentLocale = getLocale()
        
        // Add Accept-Language header
        config.headers['Accept-Language'] = this.getAcceptLanguageHeader(currentLocale)
        
        // Add custom language parameter
        if (config.params) {
          config.params.lang = currentLocale
        } else {
          config.params = { lang: currentLocale }
        }

        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor - handle errors and language
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        // Log language used in response for debugging
        if (response.data?.language) {
          console.debug(`API response in language: ${response.data.language}`)
        }
        
        return response
      },
      (error) => {
        // Handle common HTTP errors with localized messages
        if (error.response) {
          const status = error.response.status
          const data = error.response.data
          
          // Use localized error message from backend if available
          if (data?.detail && typeof data.detail === 'string') {
            error.message = data.detail
          } else if (data?.message) {
            error.message = data.message
          } else {
            // Fallback error messages
            switch (status) {
              case 400:
                error.message = 'Bad request'
                break
              case 401:
                error.message = 'Unauthorized'
                break
              case 403:
                error.message = 'Forbidden'
                break
              case 404:
                error.message = 'Not found'
                break
              case 500:
                error.message = 'Internal server error'
                break
              default:
                error.message = 'An error occurred'
            }
          }
        } else if (error.request) {
          error.message = 'Network error'
        }

        return Promise.reject(error)
      }
    )
  }

  private getAcceptLanguageHeader(locale: SupportedLocale): string {
    // Create proper Accept-Language header with quality values
    const languages = {
      en: 'en-US,en;q=0.9',
      lv: 'lv,lv-LV;q=0.9,en;q=0.8',
      ru: 'ru,ru-RU;q=0.9,en;q=0.8'
    }
    
    return languages[locale] || languages.en
  }

  // Generic request method
  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    const response = await this.client.request<T>(config)
    return response.data
  }

  // Listings API
  async getListings(filters: SearchFilters = {}): Promise<PaginatedResponse<ListingResponse>> {
    return this.request<PaginatedResponse<ListingResponse>>({
      method: 'GET',
      url: '/i18n/listings',
      params: filters,
    })
  }

  async getListing(id: string): Promise<ListingResponse> {
    return this.request<ListingResponse>({
      method: 'GET',
      url: `/i18n/listings/${id}`,
    })
  }

  async searchListings(query: string, limit = 50, offset = 0): Promise<ApiResponse<ListingResponse[]>> {
    return this.request<ApiResponse<ListingResponse[]>>({
      method: 'GET',
      url: '/i18n/search',
      params: { q: query, limit, offset },
    })
  }

  // Statistics API
  async getStatistics(): Promise<ApiResponse> {
    return this.request<ApiResponse>({
      method: 'GET',
      url: '/i18n/stats',
    })
  }

  // Language API
  async getSupportedLanguages(): Promise<SupportedLanguagesResponse> {
    return this.request<SupportedLanguagesResponse>({
      method: 'GET',
      url: '/i18n/languages',
    })
  }

  async reloadTranslations(): Promise<ApiResponse> {
    return this.request<ApiResponse>({
      method: 'POST',
      url: '/i18n/reload-translations',
    })
  }

  // Export API
  async exportListings(format: 'csv' | 'json', filters: SearchFilters = {}): Promise<Blob> {
    const response = await this.client.request({
      method: 'GET',
      url: `/export/${format}`,
      params: filters,
      responseType: 'blob',
    })
    
    return response.data
  }

  // Health check
  async healthCheck(): Promise<ApiResponse> {
    return this.request<ApiResponse>({
      method: 'GET',
      url: '/health',
    })
  }

  // Demo endpoint for i18n testing
  async getI18nDemo(): Promise<ApiResponse> {
    return this.request<ApiResponse>({
      method: 'GET',
      url: '/i18n/demo',
    })
  }
}

// Create singleton instance
export const apiClient = new ApiClient()

// Convenience functions
export const listingsApi = {
  getAll: (filters?: SearchFilters) => apiClient.getListings(filters),
  getById: (id: string) => apiClient.getListing(id),
  search: (query: string, limit?: number, offset?: number) => 
    apiClient.searchListings(query, limit, offset),
}

export const statisticsApi = {
  get: () => apiClient.getStatistics(),
}

export const languageApi = {
  getSupportedLanguages: () => apiClient.getSupportedLanguages(),
  reloadTranslations: () => apiClient.reloadTranslations(),
  demo: () => apiClient.getI18nDemo(),
}

export const exportApi = {
  csv: (filters?: SearchFilters) => apiClient.exportListings('csv', filters),
  json: (filters?: SearchFilters) => apiClient.exportListings('json', filters),
}

// Type exports
export type { ApiResponse, ListingResponse, PaginatedResponse, SearchFilters }

export default apiClient