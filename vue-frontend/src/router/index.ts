import { createRouter, createWebHistory } from 'vue-router'
import { nextTick } from 'vue'
import { 
  SUPPORT_LOCALES, 
  DEFAULT_LOCALE, 
  getLocaleFromPath, 
  setI18nLanguage,
  type SupportedLocale 
} from '@/plugins/i18n'

// Route components
const Home = () => import('@/views/Home.vue')
const Search = () => import('@/views/Search.vue')
const PropertyDetail = () => import('@/views/PropertyDetail.vue')
const Map = () => import('@/views/Map.vue')
const Saved = () => import('@/views/Saved.vue')
const About = () => import('@/views/About.vue')
const Contact = () => import('@/views/Contact.vue')
const NotFound = () => import('@/views/NotFound.vue')

// Base routes (without locale prefix)
const baseRoutes = [
  {
    path: '/',
    name: 'home',
    component: Home,
    meta: {
      title: 'navigation.home',
      description: 'Find your perfect property in Latvia'
    }
  },
  {
    path: '/search',
    name: 'search',
    component: Search,
    meta: {
      title: 'navigation.search',
      description: 'Search properties with advanced filters'
    }
  },
  {
    path: '/property/:id',
    name: 'property-detail',
    component: PropertyDetail,
    props: true,
    meta: {
      title: 'property.details',
      description: 'View detailed property information'
    }
  },
  {
    path: '/map',
    name: 'map',
    component: Map,
    meta: {
      title: 'navigation.map',
      description: 'Explore properties on interactive map'
    }
  },
  {
    path: '/saved',
    name: 'saved',
    component: Saved,
    meta: {
      title: 'navigation.saved',
      description: 'Your saved properties'
    }
  },
  {
    path: '/about',
    name: 'about',
    component: About,
    meta: {
      title: 'navigation.about',
      description: 'About ProScrape real estate platform'
    }
  },
  {
    path: '/contact',
    name: 'contact',
    component: Contact,
    meta: {
      title: 'navigation.contact',
      description: 'Contact us for support'
    }
  }
]

// Generate routes with locale prefixes
const routes = [
  // Redirect root to default locale
  {
    path: '/',
    redirect: `/${DEFAULT_LOCALE}`
  },
  
  // Routes for each supported locale
  ...SUPPORT_LOCALES.flatMap(locale => {
    const prefix = locale === DEFAULT_LOCALE ? '' : `/${locale}`
    
    return baseRoutes.map(route => ({
      ...route,
      path: `${prefix}${route.path === '/' ? '' : route.path}`,
      name: locale === DEFAULT_LOCALE ? route.name : `${locale}-${route.name}`,
      meta: {
        ...route.meta,
        locale
      }
    }))
  }),
  
  // Catch-all 404 route
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: NotFound,
    meta: {
      title: 'Page Not Found',
      description: 'The page you are looking for does not exist'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // Scroll to saved position if available (browser back/forward)
    if (savedPosition) {
      return savedPosition
    }
    
    // Scroll to anchor if present
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    
    // Scroll to top for new pages
    return { top: 0, behavior: 'smooth' }
  }
})

// Global navigation guards
router.beforeEach(async (to, from) => {
  // Extract locale from path
  const { locale, path } = getLocaleFromPath(to.path)
  
  // Validate locale
  if (!SUPPORT_LOCALES.includes(locale)) {
    // Redirect to default locale if invalid
    return `/${DEFAULT_LOCALE}${path}`
  }
  
  // Set document language and direction
  await nextTick()
  document.documentElement.lang = locale
  
  // Update i18n locale if needed
  const i18n = (router.app?.config?.globalProperties?.$i18n)
  if (i18n && i18n.global.locale.value !== locale) {
    await setI18nLanguage(i18n, locale)
  }
  
  return true
})

router.afterEach((to) => {
  // Update document title with localized text
  nextTick(() => {
    const i18n = router.app?.config?.globalProperties?.$i18n
    if (i18n && to.meta?.title) {
      const translatedTitle = i18n.global.t(to.meta.title as string)
      document.title = `${translatedTitle} | ProScrape`
    } else {
      document.title = 'ProScrape - Real Estate Portal'
    }
    
    // Update meta description
    if (to.meta?.description) {
      const descriptionElement = document.querySelector('meta[name="description"]')
      if (descriptionElement) {
        const translatedDescription = i18n?.global.t(to.meta.description as string) || to.meta.description
        descriptionElement.setAttribute('content', translatedDescription as string)
      }
    }
  })
})

// Helper functions for route generation
export function generateLocalizedRoute(name: string, locale?: SupportedLocale, params?: any) {
  const currentLocale = locale || DEFAULT_LOCALE
  const routeName = currentLocale === DEFAULT_LOCALE ? name : `${currentLocale}-${name}`
  
  return {
    name: routeName,
    params: params || {}
  }
}

export function getCurrentLocaleFromRoute(route: any): SupportedLocale {
  return route.meta?.locale || getLocaleFromPath(route.path).locale
}

export function getLocalizedPath(path: string, locale: SupportedLocale): string {
  if (locale === DEFAULT_LOCALE) {
    return path
  }
  return `/${locale}${path === '/' ? '' : path}`
}

export function switchRouteLocale(currentRoute: any, newLocale: SupportedLocale) {
  const { path } = getLocaleFromPath(currentRoute.path)
  return getLocalizedPath(path, newLocale)
}

export default router