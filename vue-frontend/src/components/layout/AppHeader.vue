<template>
  <header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo -->
        <div class="flex items-center">
          <RouterLink 
            :to="localizedPath('/')" 
            class="flex items-center space-x-2 text-xl font-bold text-primary-600 hover:text-primary-700 transition-colors"
          >
            <div class="w-8 h-8 bg-primary-600 rounded text-white flex items-center justify-center">
              <span class="text-sm font-bold">PS</span>
            </div>
            <span>ProScrape</span>
          </RouterLink>
        </div>

        <!-- Desktop Navigation -->
        <nav class="hidden md:flex items-center space-x-8">
          <RouterLink
            v-for="item in navigationItems"
            :key="item.name"
            :to="localizedPath(item.path)"
            class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
            :class="{ 'text-primary-600 bg-primary-50': isActiveRoute(item.path) }"
          >
            {{ $t(item.label) }}
          </RouterLink>
        </nav>

        <!-- Right Side Actions -->
        <div class="flex items-center space-x-4">
          <!-- Search Bar (Desktop) -->
          <div class="hidden lg:block">
            <QuickSearch />
          </div>

          <!-- Language Switcher -->
          <LanguageSwitcher />

          <!-- Saved Properties -->
          <RouterLink
            :to="localizedPath('/saved')"
            class="relative p-2 text-gray-600 hover:text-gray-900 transition-colors"
            :title="$t('navigation.saved')"
          >
            <HeartIcon class="h-6 w-6" />
            <span 
              v-if="savedCount > 0"
              class="absolute -top-1 -right-1 bg-primary-600 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center"
            >
              {{ savedCount }}
            </span>
          </RouterLink>

          <!-- Mobile Menu Button -->
          <button
            @click="toggleMobileMenu"
            class="md:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            :aria-expanded="isMobileMenuOpen"
            aria-label="Open menu"
          >
            <Bars3Icon v-if="!isMobileMenuOpen" class="h-6 w-6" />
            <XMarkIcon v-else class="h-6 w-6" />
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile Menu -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <div v-show="isMobileMenuOpen" class="md:hidden bg-white border-t border-gray-200">
        <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3">
          <!-- Mobile Search -->
          <div class="px-3 py-2">
            <QuickSearch />
          </div>

          <!-- Mobile Navigation Links -->
          <RouterLink
            v-for="item in navigationItems"
            :key="item.name"
            :to="localizedPath(item.path)"
            @click="closeMobileMenu"
            class="block px-3 py-2 rounded-md text-base font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors"
            :class="{ 'text-primary-600 bg-primary-50': isActiveRoute(item.path) }"
          >
            {{ $t(item.label) }}
          </RouterLink>
        </div>
      </div>
    </Transition>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { 
  Bars3Icon, 
  XMarkIcon, 
  HeartIcon 
} from '@heroicons/vue/24/outline'

import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import QuickSearch from '@/components/search/QuickSearch.vue'
import { useLanguageStore } from '@/stores/language'
import { useSavedListingsStore } from '@/stores/savedListings'
import { getLocalizedPath, getCurrentLocaleFromRoute } from '@/plugins/i18n'

// Composables
const route = useRoute()
const { t } = useI18n()
const languageStore = useLanguageStore()
const savedListingsStore = useSavedListingsStore()

// State
const isMobileMenuOpen = ref(false)

// Computed
const savedCount = computed(() => savedListingsStore.count)

const navigationItems = [
  { name: 'home', label: 'navigation.home', path: '/' },
  { name: 'search', label: 'navigation.search', path: '/search' },
  { name: 'map', label: 'navigation.map', path: '/map' },
  { name: 'about', label: 'navigation.about', path: '/about' },
  { name: 'contact', label: 'navigation.contact', path: '/contact' },
]

// Methods
const localizedPath = (path: string) => {
  const currentLocale = getCurrentLocaleFromRoute(route)
  return getLocalizedPath(path, currentLocale)
}

const isActiveRoute = (path: string) => {
  const currentPath = route.path
  const { path: routePath } = getLocaleFromPath(currentPath)
  
  if (path === '/') {
    return routePath === '/' || routePath === ''
  }
  
  return routePath.startsWith(path)
}

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false
}

// Close mobile menu when clicking outside
const handleClickOutside = (event: Event) => {
  const target = event.target as Element
  if (!target.closest('header') && isMobileMenuOpen.value) {
    closeMobileMenu()
  }
}

// Close mobile menu on escape key
const handleEscapeKey = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && isMobileMenuOpen.value) {
    closeMobileMenu()
  }
}

// Close mobile menu on route change
const handleRouteChange = () => {
  if (isMobileMenuOpen.value) {
    closeMobileMenu()
  }
}

// Lifecycle
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleEscapeKey)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscapeKey)
})

// Watch route changes
watch(() => route.path, handleRouteChange)
</script>

<style scoped>
/* Additional header-specific styles if needed */
.router-link-exact-active {
  @apply text-primary-600 bg-primary-50;
}
</style>