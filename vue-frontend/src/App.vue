<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <!-- SEO Head Management -->
    <Head>
      <title>{{ pageTitle }}</title>
      <meta name="description" :content="pageDescription" />
      <meta property="og:title" :content="pageTitle" />
      <meta property="og:description" :content="pageDescription" />
      <meta property="og:type" content="website" />
      <meta property="og:url" :content="currentUrl" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" :content="pageTitle" />
      <meta name="twitter:description" :content="pageDescription" />
      <link rel="canonical" :href="currentUrl" />
      
      <!-- Language alternates -->
      <link 
        v-for="locale in availableLocales" 
        :key="locale"
        rel="alternate" 
        :hreflang="locale" 
        :href="getLocalizedUrl(locale)" 
      />
      <link rel="alternate" hreflang="x-default" :href="getLocalizedUrl('en')" />
    </Head>

    <!-- Header -->
    <AppHeader />

    <!-- Main Content -->
    <main class="flex-1">
      <RouterView v-slot="{ Component }">
        <Transition 
          name="page" 
          mode="out-in"
          @before-enter="onBeforeEnter"
          @after-enter="onAfterEnter"
        >
          <Suspense>
            <component :is="Component" />
            
            <template #fallback>
              <div class="flex items-center justify-center min-h-96">
                <LoadingSpinner size="lg" />
              </div>
            </template>
          </Suspense>
        </Transition>
      </RouterView>
    </main>

    <!-- Footer -->
    <AppFooter />

    <!-- Global Components -->
    <NotificationContainer />
    <ConnectionStatus />
    
    <!-- Global Loading Overlay -->
    <LoadingOverlay v-if="isGlobalLoading" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useHead } from '@vueuse/head'
import { storeToRefs } from 'pinia'

// Components
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import NotificationContainer from '@/components/notifications/NotificationContainer.vue'
import ConnectionStatus from '@/components/common/ConnectionStatus.vue'

// Stores
import { useLanguageStore } from '@/stores/language'
import { useAppStore } from '@/stores/app'

// Utils
import { SUPPORT_LOCALES, getLocalizedPath, getCurrentLocaleFromRoute } from '@/plugins/i18n'

// Composables
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const languageStore = useLanguageStore()
const appStore = useAppStore()

// Reactive store data
const { currentLocale } = storeToRefs(languageStore)
const { isGlobalLoading } = storeToRefs(appStore)

// Computed properties
const availableLocales = computed(() => SUPPORT_LOCALES)

const currentUrl = computed(() => {
  if (typeof window !== 'undefined') {
    return window.location.href
  }
  return ''
})

const pageTitle = computed(() => {
  const routeTitle = route.meta?.title as string
  if (routeTitle) {
    const translatedTitle = t(routeTitle)
    return `${translatedTitle} | ProScrape`
  }
  return 'ProScrape - Real Estate Portal'
})

const pageDescription = computed(() => {
  const routeDescription = route.meta?.description as string
  if (routeDescription) {
    // Try to translate, fallback to original if no translation
    try {
      return t(routeDescription)
    } catch {
      return routeDescription
    }
  }
  return t('messages.welcome')
})

// Methods
const getLocalizedUrl = (targetLocale: string) => {
  if (typeof window === 'undefined') return ''
  
  const { origin } = window.location
  const localizedPath = getLocalizedPath(route.path, targetLocale as any)
  return `${origin}${localizedPath}`
}

const onBeforeEnter = () => {
  // Optional: Set loading state for page transitions
  appStore.setGlobalLoading(true)
}

const onAfterEnter = () => {
  // Clear loading state
  appStore.setGlobalLoading(false)
  
  // Analytics: Track page view
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('config', 'GA_MEASUREMENT_ID', {
      page_title: pageTitle.value,
      page_location: currentUrl.value,
      language: currentLocale.value
    })
  }
}

// Watchers
watch(
  () => route.path,
  (newPath) => {
    // Update locale based on route
    const routeLocale = getCurrentLocaleFromRoute(route)
    if (routeLocale !== currentLocale.value) {
      languageStore.setLocale(routeLocale)
    }
  },
  { immediate: true }
)

watch(
  currentLocale,
  (newLocale) => {
    // Update i18n locale
    locale.value = newLocale
  }
)

// Lifecycle
onMounted(() => {
  // Initialize language store
  languageStore.initialize()
  
  // Setup global event listeners
  window.addEventListener('language-changed', handleLanguageChange)
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  
  // Check initial connection status
  appStore.setConnectionStatus(navigator.onLine)
})

const handleLanguageChange = (event: CustomEvent) => {
  console.log('Language changed:', event.detail)
  
  // Analytics: Track language change
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', 'language_change', {
      from_language: event.detail.from,
      to_language: event.detail.to
    })
  }
}

const handleOnline = () => {
  appStore.setConnectionStatus(true)
}

const handleOffline = () => {
  appStore.setConnectionStatus(false)
}

// Use head for meta management
useHead({
  htmlAttrs: {
    lang: currentLocale,
    dir: computed(() => languageStore.localeInfo.rtl ? 'rtl' : 'ltr')
  }
})
</script>

<style>
/* Page transition animations */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Global styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  line-height: 1.6;
  color: #2d3748;
  background-color: #f7fafc;
}

/* Smooth scrolling */
html {
  scroll-behavior: smooth;
}

/* Focus styles for accessibility */
:focus {
  outline: 2px solid #3182ce;
  outline-offset: 2px;
}

/* Print styles */
@media print {
  .no-print {
    display: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  * {
    border-color: currentColor !important;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>