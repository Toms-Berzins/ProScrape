import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	define: {
		global: 'globalThis',
	},
	optimizeDeps: {
		include: [
			'leaflet',
			'leaflet.markercluster',
			'leaflet.heat',
			'workbox-window',
			'idb'
		],
		exclude: []
	},
	ssr: {
		noExternal: [
			'leaflet',
			'leaflet.markercluster', 
			'leaflet.heat'
		]
	},
	build: {
		rollupOptions: {
			output: {
				manualChunks: {
					// Core chunks for better caching
					'vendor-maps': ['leaflet', 'leaflet.markercluster', 'leaflet.heat'],
					'vendor-pwa': ['workbox-window', 'idb'],
				}
			}
		},
		// Enable source maps for better debugging
		sourcemap: true,
		// Optimize for mobile performance
		target: ['es2020', 'safari13'],
		// Enable compression
		reportCompressedSize: true
	},
	// Performance optimizations
	server: {
		headers: {
			'Cache-Control': 'max-age=31536000'
		}
	}
});
