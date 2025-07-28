import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createHead } from '@vueuse/head'

// Main App component
import App from './App.vue'

// Router
import router from './router'

// i18n setup
import setupI18n from './plugins/i18n'

// Styles
import './assets/css/main.css'

// Create Vue app
const app = createApp(App)

// Initialize plugins
const pinia = createPinia()
const head = createHead()

async function setupApp() {
  try {
    // Setup i18n
    const i18n = await setupI18n()
    
    // Install plugins
    app.use(pinia)
    app.use(router)
    app.use(i18n)
    app.use(head)
    
    // Global error handler
    app.config.errorHandler = (error, instance, info) => {
      console.error('Global error:', error)
      console.error('Component instance:', instance)
      console.error('Error info:', info)
      
      // You can integrate with error reporting service here
      // e.g., Sentry, LogRocket, etc.
    }
    
    // Global warning handler
    app.config.warnHandler = (msg, instance, trace) => {
      console.warn('Global warning:', msg)
      console.warn('Component instance:', instance)
      console.warn('Trace:', trace)
    }
    
    // Global properties (if needed)
    app.config.globalProperties.$api = {
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000'
    }
    
    // Mount the app
    app.mount('#app')
    
    console.log('🚀 ProScrape Vue.js app started successfully')
    
  } catch (error) {
    console.error('❌ Failed to start app:', error)
    
    // Show error message to user
    document.body.innerHTML = `
      <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        font-family: system-ui, sans-serif;
        background: #f7fafc;
        color: #2d3748;
      ">
        <div style="text-align: center; max-width: 500px; padding: 2rem;">
          <h1 style="color: #e53e3e; margin-bottom: 1rem;">
            ⚠️ Application Error
          </h1>
          <p style="margin-bottom: 1rem;">
            Failed to start the application. Please check the console for details.
          </p>
          <button 
            onclick="window.location.reload()" 
            style="
              background: #3182ce;
              color: white;
              border: none;
              padding: 0.75rem 1.5rem;
              border-radius: 0.375rem;
              cursor: pointer;
              font-size: 1rem;
            "
          >
            🔄 Reload Page
          </button>
        </div>
      </div>
    `
  }
}

// Initialize app
setupApp()

// Hot Module Replacement (HMR) support
if (import.meta.hot) {
  import.meta.hot.accept()
}