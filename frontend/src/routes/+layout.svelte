<script>
  import { browser } from "$app/environment";
  import PerformanceDashboard from "$lib/components/common/PerformanceDashboard.svelte";
  import PWAInstallBanner from "$lib/components/common/PWAInstallBanner.svelte";
  import Footer from "$lib/components/layout/Footer.svelte";
  import Header from "$lib/components/layout/Header.svelte";
  import ConnectionStatus from "$lib/components/notifications/ConnectionStatus.svelte";
  import ToastContainer from "$lib/components/notifications/ToastContainer.svelte";
  import { onMount } from "svelte";
  import "../app.css";
  // PWA and Performance utilities
  import { networkAwareManager } from "$lib/utils/networkAware";
  import { CoreWebVitalsMonitor } from "$lib/utils/performanceMonitor";
  import { pushNotificationManager } from "$lib/utils/pushNotifications";
  import { serviceWorkerManager } from "$lib/utils/serviceWorker";

  // State
  let showPerformanceDashboard = false;
  let isStandalone = false;
  let isDevelopment = false;

  onMount(() => {
    if (!browser) return;

    // Check if running in standalone PWA mode
    isStandalone = serviceWorkerManager.isStandalone();

    // Check if in development mode
    isDevelopment = import.meta.env.DEV;

    // Initialize PWA features
    initializePWAFeatures();

    // Set up service worker update notifications
    setupServiceWorkerUpdateNotifications();

    // Initialize performance monitoring
    initializePerformanceMonitoring();

    // Show performance dashboard in development or debug mode
    const urlParams = new URLSearchParams(window.location.search);
    showPerformanceDashboard =
      isDevelopment || urlParams.has("debug-performance");
  });

  async function initializePWAFeatures() {
    try {
      // Service worker should already be registered from app.html
      // Just ensure it's working properly
      const registration = serviceWorkerManager.getRegistration();
      if (registration) {
        console.log("Service worker active and ready");
      }

      // Initialize network awareness
      networkAwareManager.subscribe((conditions) => {
        console.log("Network conditions updated:", conditions);
      });

      // Set up push notifications if user has previously enabled them
      const savedSettings = localStorage.getItem("notification-settings");
      if (savedSettings) {
        const settings = JSON.parse(savedSettings);
        if (settings.enabled) {
          // Restore push notification subscription
          await pushNotificationManager.requestPermission();
        }
      }
    } catch (error) {
      console.error("Failed to initialize PWA features:", error);
    }
  }

  function setupServiceWorkerUpdateNotifications() {
    // Listen for service worker updates
    window.addEventListener("sw-update-available", () => {
      // Show update notification using toast system
      const event = new CustomEvent("show-toast", {
        detail: {
          type: "info",
          title: "Update Available",
          message:
            "A new version of ProScrape is available. Refresh to update.",
          actions: [
            {
              label: "Update Now",
              action: () => {
                serviceWorkerManager.applyUpdate();
              },
            },
            {
              label: "Later",
              action: () => {},
            },
          ],
          persistent: true,
        },
      });
      window.dispatchEvent(event);
    });

    // Listen for PWA installation events
    window.addEventListener("pwa-installable", () => {
      console.log("PWA installation available");
    });
  }

  function initializePerformanceMonitoring() {
    try {
      // Initialize Core Web Vitals monitoring
      const vitalsMonitor = CoreWebVitalsMonitor.getInstance();

      vitalsMonitor.subscribe((metrics) => {
        // Log performance metrics in development
        if (isDevelopment) {
          console.log("Core Web Vitals:", metrics);
        }

        // Send to analytics in production
        if (!isDevelopment && typeof gtag !== "undefined") {
          if (metrics.lcp) {
            gtag("event", "performance_metric", {
              event_category: "Web Vitals",
              event_label: "LCP",
              value: Math.round(metrics.lcp),
            });
          }

          if (metrics.fid) {
            gtag("event", "performance_metric", {
              event_category: "Web Vitals",
              event_label: "FID",
              value: Math.round(metrics.fid),
            });
          }

          if (metrics.cls !== undefined) {
            gtag("event", "performance_metric", {
              event_category: "Web Vitals",
              event_label: "CLS",
              value: Math.round(metrics.cls * 1000),
            });
          }
        }
      });
    } catch (error) {
      console.error("Failed to initialize performance monitoring:", error);
    }
  }

  // Handle keyboard shortcuts
  function handleKeydown(event) {
    // Toggle performance dashboard with Ctrl/Cmd + Shift + P
    if (
      (event.ctrlKey || event.metaKey) &&
      event.shiftKey &&
      event.key === "P"
    ) {
      event.preventDefault();
      showPerformanceDashboard = !showPerformanceDashboard;
    }

    // Force service worker update with Ctrl/Cmd + Shift + U
    if (
      (event.ctrlKey || event.metaKey) &&
      event.shiftKey &&
      event.key === "U"
    ) {
      event.preventDefault();
      serviceWorkerManager.applyUpdate();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="min-h-screen flex flex-col" class:standalone={isStandalone}>
  <Header />
  <main class="flex-1">
    <slot />
  </main>
  <Footer />
</div>

<!-- Global Toast Notifications -->
<ToastContainer />

<!-- Global Connection Status -->
<ConnectionStatus />

<!-- PWA Install Banner (only show if not in standalone mode) -->
{#if !isStandalone}
  <PWAInstallBanner variant="banner" position="bottom" />
{/if}

<!-- Performance Dashboard (development and debug mode) -->
{#if showPerformanceDashboard}
  <PerformanceDashboard variant="compact" showDetailedMetrics={isDevelopment} />
{/if}

<style>
  /* PWA-specific styles */
  .standalone {
    /* Add padding for safe areas on devices with notches */
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
  }

  /* Standalone mode adjustments */
  :global(.standalone) {
    /* Hide browser UI elements that don't make sense in standalone mode */
    user-select: none;
    -webkit-touch-callout: none;
  }

  /* Performance optimizations */
  :global(body) {
    /* Enable GPU acceleration for smooth scrolling */
    transform: translateZ(0);
    -webkit-transform: translateZ(0);

    /* Optimize font rendering */
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
  }

  /* Touch-friendly interactions */
  :global(*) {
    /* Prevent selection on touch devices */
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;

    /* Allow selection for text content */
    -webkit-touch-callout: none;
  }

  :global(input, textarea, [contenteditable]) {
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
    user-select: text;
  }

  /* Loading optimization */
  :global(.loading-skeleton) {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
  }

  @keyframes loading {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    :global(.loading-skeleton) {
      background: linear-gradient(90deg, #374151 25%, #4b5563 50%, #374151 75%);
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    :global(.loading-skeleton) {
      animation: none;
    }

    :global(*) {
      transition: none !important;
      animation: none !important;
    }
  }

  /* High contrast mode support */
  @media (prefers-contrast: high) {
    :global(*) {
      border-width: 2px;
    }
  }
</style>
