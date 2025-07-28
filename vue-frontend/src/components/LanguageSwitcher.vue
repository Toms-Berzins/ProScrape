<template>
  <div class="relative" ref="dropdown">
    <!-- Language Selector Button -->
    <button
      @click="toggleDropdown"
      class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors duration-200"
      :aria-expanded="isOpen"
      aria-haspopup="true"
    >
      <span class="mr-2 text-lg">{{ currentLocaleInfo.flag }}</span>
      <span class="hidden sm:block">{{ currentLocaleInfo.nativeName }}</span>
      <span class="sm:hidden">{{ currentLocaleInfo.flag }}</span>
      <ChevronDownIcon 
        class="ml-2 h-4 w-4 transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
      />
    </button>

    <!-- Dropdown Menu -->
    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-show="isOpen"
        class="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50"
        role="menu"
        aria-orientation="vertical"
      >
        <div class="py-1" role="none">
          <button
            v-for="locale in availableLocales"
            :key="locale"
            @click="changeLanguage(locale)"
            class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors duration-150"
            :class="{
              'bg-gray-100 text-gray-900': locale === currentLocale,
              'font-medium': locale === currentLocale
            }"
            role="menuitem"
          >
            <span class="mr-3 text-lg">{{ LOCALE_INFO[locale].flag }}</span>
            <div class="flex flex-col items-start">
              <span class="font-medium">{{ LOCALE_INFO[locale].nativeName }}</span>
              <span class="text-xs text-gray-500">{{ LOCALE_INFO[locale].name }}</span>
            </div>
            <CheckIcon 
              v-if="locale === currentLocale"
              class="ml-auto h-4 w-4 text-primary-600"
            />
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter, useRoute } from 'vue-router'
import { ChevronDownIcon, CheckIcon } from '@heroicons/vue/24/outline'
import { 
  SUPPORT_LOCALES, 
  LOCALE_INFO, 
  setI18nLanguage,
  loadLocaleMessages,
  type SupportedLocale 
} from '@/plugins/i18n'
import { useLanguageStore } from '@/stores/language'

// Composables
const { locale } = useI18n()
const router = useRouter()
const route = useRoute()
const languageStore = useLanguageStore()

// Reactive state
const isOpen = ref(false)
const dropdown = ref<HTMLElement>()

// Computed properties
const currentLocale = computed(() => locale.value as SupportedLocale)
const currentLocaleInfo = computed(() => LOCALE_INFO[currentLocale.value])
const availableLocales = computed(() => SUPPORT_LOCALES)

// Methods
const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const closeDropdown = () => {
  isOpen.value = false
}

const changeLanguage = async (newLocale: SupportedLocale) => {
  if (newLocale === currentLocale.value) {
    closeDropdown()
    return
  }

  try {
    // Show loading state if needed
    const i18nInstance = { global: { locale } }
    
    // Load locale messages if not already loaded (lazy loading)
    await loadLocaleMessages(i18nInstance, newLocale)
    
    // Update store
    languageStore.setLocale(newLocale)
    
    // Update route with new locale
    const currentPath = route.path
    const pathWithoutLocale = currentPath.replace(/^\/(?:en|lv|ru)/, '') || '/'
    
    // Navigate to the same route with new locale
    if (newLocale === 'en') {
      // Default locale doesn't need prefix
      await router.push(pathWithoutLocale)
    } else {
      await router.push(`/${newLocale}${pathWithoutLocale}`)
    }
    
    // Emit language change event for analytics
    window.dispatchEvent(new CustomEvent('language-changed', {
      detail: { from: currentLocale.value, to: newLocale }
    }))
    
    closeDropdown()
  } catch (error) {
    console.error('Error changing language:', error)
    closeDropdown()
  }
}

// Click outside handler
const handleClickOutside = (event: Event) => {
  if (dropdown.value && !dropdown.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

// Escape key handler
const handleEscapeKey = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && isOpen.value) {
    closeDropdown()
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
</script>

<style scoped>
/* Custom animations for the dropdown */
.rotate-180 {
  transform: rotate(180deg);
}
</style>