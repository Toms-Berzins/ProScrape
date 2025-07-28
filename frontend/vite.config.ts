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
			'leaflet.heat'
		],
		exclude: []
	},
	ssr: {
		noExternal: [
			'leaflet',
			'leaflet.markercluster', 
			'leaflet.heat'
		]
	}
});
