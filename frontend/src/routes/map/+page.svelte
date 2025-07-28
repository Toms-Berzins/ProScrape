<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { 
		mapView, 
		mapBounds, 
		propertyMarkers, 
		visibleListings,
		searchArea,
		mapStatistics,
		selectedMarker,
		mapLoading,
		mapActions,
		debouncedMapActions
	} from '$lib/stores/map';
	import { filters, filterActions } from '$lib/stores/filters';
	import { savedListings } from '$lib/stores/savedListings';
	import type { Listing } from '$lib/types/listing';
	import type { MapBounds, SearchArea, PropertyMarker } from '$lib/types/map';
	import { MapApi } from '$lib/api/map';
	import { debounce } from '$lib/utils/debounce';

	// Components
	import MapContainer from '$lib/components/map/MapContainer.svelte';
	import PropertySidebar from '$lib/components/map/PropertySidebar.svelte';
	import MapControls from '$lib/components/map/MapControls.svelte';
	import FilterPanel from '$lib/components/search/FilterPanel.svelte';
	import SearchBar from '$lib/components/search/SearchBar.svelte';
	import ToastContainer from '$lib/components/notifications/ToastContainer.svelte';

	// Component state
	let mapComponent: MapContainer;
	let isLoading = false;
	let error: string | null = null;
	let isSidebarCollapsed = false;
	let showFilters = false;
	let showMobileControls = false;

	// Reactive loading search
	const debouncedLoadListings = debounce(loadListingsForBounds, 300);

	onMount(() => {
		// Load initial data
		loadInitialData();
		
		// Set up URL state management
		setupUrlStateManagement();
		
		// Handle initial URL parameters
		handleUrlParameters();
	});

	async function loadInitialData() {
		if (!browser) return;

		// If we have map bounds, load listings
		if ($mapBounds) {
			await loadListingsForBounds($mapBounds);
		}
	}

	async function loadListingsForBounds(bounds: MapBounds) {
		if (isLoading) return;

		isLoading = true;
		mapActions.setLoading(true);
		error = null;

		try {
			// Convert filters to ListingFilters format
			const listingFilters = {
				search: $filters.query,
				minPrice: $filters.minPrice,
				maxPrice: $filters.maxPrice,
				minArea: $filters.minArea,
				maxArea: $filters.maxArea,
				propertyType: $filters.propertyType,
				location: $filters.location,
				source: $filters.source,
				hasImages: $filters.hasImages,
				hasCoordinates: true // Always require coordinates for map view
			};

			const response = await MapApi.getListingsInBounds(bounds, listingFilters);

			if (response.error) {
				error = response.error;
				console.error('Failed to load listings:', response.error);
			} else if (response.data) {
				// Update map markers
				mapActions.setPropertyMarkers(response.data);
				
				// Update visible listings for sidebar
				mapActions.setVisibleListings(response.data);
			}

		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load listings';
			console.error('Error loading listings:', err);
		} finally {
			isLoading = false;
			mapActions.setLoading(false);
		}
	}

	async function loadListingsForArea(area: SearchArea) {
		if (isLoading) return;

		isLoading = true;
		mapActions.setLoading(true);
		error = null;

		try {
			const listingFilters = {
				search: $filters.query,
				minPrice: $filters.minPrice,
				maxPrice: $filters.maxPrice,
				minArea: $filters.minArea,
				maxArea: $filters.maxArea,
				propertyType: $filters.propertyType,
				location: $filters.location,
				source: $filters.source,
				hasImages: $filters.hasImages,
				hasCoordinates: true
			};

			const response = await MapApi.getListingsInArea(area, listingFilters);

			if (response.error) {
				error = response.error;
			} else if (response.data) {
				mapActions.setPropertyMarkers(response.data);
				mapActions.setVisibleListings(response.data);
			}

		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load listings';
		} finally {
			isLoading = false;
			mapActions.setLoading(false);
		}
	}

	function setupUrlStateManagement() {
		// Update URL when map state changes
		let updateUrlTimeout: NodeJS.Timeout;

		const updateUrl = () => {
			clearTimeout(updateUrlTimeout);
			updateUrlTimeout = setTimeout(() => {
				const params = new URLSearchParams();
				
				// Add map view parameters
				params.set('lat', $mapView.center[0].toString());
				params.set('lng', $mapView.center[1].toString());
				params.set('zoom', $mapView.zoom.toString());
				
				// Add search area if exists
				if ($searchArea) {
					params.set('area', btoa(JSON.stringify($searchArea)));
				}
				
				// Add filters
				if ($filters.query) params.set('q', $filters.query);
				if ($filters.minPrice) params.set('min_price', $filters.minPrice.toString());
				if ($filters.maxPrice) params.set('max_price', $filters.maxPrice.toString());
				if ($filters.propertyType) params.set('type', $filters.propertyType);
				
				// Update URL without page reload
				const newUrl = `${window.location.pathname}?${params.toString()}`;
				window.history.replaceState({}, '', newUrl);
			}, 1000);
		};

		// Watch for changes
		const unsubscribers = [
			mapView.subscribe(updateUrl),
			searchArea.subscribe(updateUrl),
			filters.subscribe(updateUrl)
		];

		// Cleanup
		return () => {
			unsubscribers.forEach(unsub => unsub());
			clearTimeout(updateUrlTimeout);
		};
	}

	function handleUrlParameters() {
		const params = new URLSearchParams($page.url.search);
		
		// Restore map view
		const lat = params.get('lat');
		const lng = params.get('lng');
		const zoom = params.get('zoom');
		
		if (lat && lng && zoom) {
			mapActions.updateView({
				center: [parseFloat(lat), parseFloat(lng)],
				zoom: parseInt(zoom)
			});
		}
		
		// Restore search area
		const areaParam = params.get('area');
		if (areaParam) {
			try {
				const area = JSON.parse(atob(areaParam));
				mapActions.setSearchArea(area);
			} catch (e) {
				console.warn('Failed to parse search area from URL');
			}
		}
		
		// Restore filters
		const filterUpdates: any = {};
		if (params.get('q')) filterUpdates.query = params.get('q');
		if (params.get('min_price')) filterUpdates.minPrice = parseInt(params.get('min_price')!);
		if (params.get('max_price')) filterUpdates.maxPrice = parseInt(params.get('max_price')!);
		if (params.get('type')) filterUpdates.propertyType = params.get('type');
		
		if (Object.keys(filterUpdates).length > 0) {
			filterActions.updateFilters(filterUpdates);
		}
	}

	// Event handlers
	function handleMapReady(event: CustomEvent<L.Map>) {
		console.log('Map ready');
	}

	function handleBoundsChanged(event: CustomEvent<MapBounds>) {
		const bounds = event.detail;
		
		// Only load if we have a significant bounds change
		if (!$searchArea) {
			debouncedLoadListings(bounds);
		}
	}

	function handleAreaDrawn(event: CustomEvent<SearchArea>) {
		const area = event.detail;
		loadListingsForArea(area);
	}

	function handleMarkerClicked(event: CustomEvent<PropertyMarker>) {
		const marker = event.detail;
		// Marker selection is handled by the map store
	}

	function handleListingSelected(event: CustomEvent<Listing>) {
		const listing = event.detail;
		
		// Find and select the corresponding marker
		const marker = $propertyMarkers.find(m => m.listing.listing_id === listing.listing_id);
		if (marker) {
			mapActions.selectMarker(marker);
			
			// Pan to marker if needed
			if (mapComponent) {
				mapComponent.panTo(marker.position);
			}
		}
	}

	function handleViewDetails(event: CustomEvent<string>) {
		const listingId = event.detail;
		goto(`/listings/${listingId}`);
	}

	function handleSaveListing(event: CustomEvent<string>) {
		const listingId = event.detail;
		savedListings.toggle(listingId);
	}

	function handleFilterChange() {
		// Reload listings when filters change
		if ($mapBounds) {
			debouncedLoadListings($mapBounds);
		} else if ($searchArea) {
			loadListingsForArea($searchArea);
		}
	}

	function toggleSidebar() {
		isSidebarCollapsed = !isSidebarCollapsed;
	}

	function toggleFilters() {
		showFilters = !showFilters;
	}

	function toggleMobileControls() {
		showMobileControls = !showMobileControls;
	}

	// Reactive statements
	$: if ($filters && browser) {
		handleFilterChange();
	}

	$: if ($mapBounds && browser) {
		debouncedLoadListings($mapBounds);
	}
</script>

<svelte:head>
	<title>Property Map Search - ProScrape</title>
	<meta name="description" content="Interactive map search for Latvian real estate properties. Find apartments, houses, and land with advanced filtering options." />
</svelte:head>

<div class="map-page">
	<!-- Mobile header -->
	<div class="mobile-header">
		<div class="mobile-header-content">
			<h1 class="mobile-title">Property Map</h1>
			<div class="mobile-actions">
				<button 
					class="mobile-action-button"
					class:active={showFilters}
					on:click={toggleFilters}
					aria-label="Toggle filters"
				>
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46"></polygon>
					</svg>
				</button>
				
				<button 
					class="mobile-action-button"
					class:active={showMobileControls}
					on:click={toggleMobileControls}
					aria-label="Toggle map controls"
				>
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="3"></circle>
						<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
					</svg>
				</button>
				
				<button 
					class="mobile-action-button"
					class:active={!isSidebarCollapsed}
					on:click={toggleSidebar}
					aria-label="Toggle property list"
				>
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"></path>
					</svg>
				</button>
			</div>
		</div>
		
		<!-- Mobile search bar -->
		<div class="mobile-search">
			<SearchBar 
				placeholder="Search properties..."
				on:search={(e) => filterActions.updateFilter('query', e.detail)}
			/>
		</div>
	</div>

	<!-- Mobile filters panel -->
	{#if showFilters}
		<div class="mobile-filters">
			<FilterPanel 
				compact={true}
				on:filter-changed={handleFilterChange}
				on:close={() => showFilters = false}
			/>
		</div>
	{/if}

	<!-- Main content -->
	<div class="map-content">
		<!-- Desktop sidebar -->
		<div class="desktop-sidebar" class:collapsed={isSidebarCollapsed}>
			<PropertySidebar 
				{isSidebarCollapsed}
				on:listing-selected={handleListingSelected}
				on:view-details={handleViewDetails}
				on:toggle-collapsed={() => isSidebarCollapsed = !isSidebarCollapsed}
			/>
		</div>

		<!-- Map container -->
		<div class="map-wrapper">
			<MapContainer
				bind:this={mapComponent}
				width="100%"
				height="100%"
				on:map-ready={handleMapReady}
				on:bounds-changed={handleBoundsChanged}
				on:marker-clicked={handleMarkerClicked}
			/>

			<!-- Map controls overlay -->
			<MapControls 
				map={mapComponent?.getMap()}
				on:area-drawn={handleAreaDrawn}
			/>

			<!-- Loading overlay -->
			{#if $mapLoading || isLoading}
				<div class="loading-overlay">
					<div class="loading-spinner">
						<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
						</svg>
					</div>
					<div class="loading-text">Loading properties...</div>
				</div>
			{/if}

			<!-- Error overlay -->
			{#if error}
				<div class="error-overlay">
					<div class="error-content">
						<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<circle cx="12" cy="12" r="10"></circle>
							<line x1="15" y1="9" x2="9" y2="15"></line>
							<line x1="9" y1="9" x2="15" y2="15"></line>
						</svg>
						<p>{error}</p>
						<button 
							class="retry-button"
							on:click={() => {
								error = null;
								if ($mapBounds) loadListingsForBounds($mapBounds);
							}}
						>
							Retry
						</button>
					</div>
				</div>
			{/if}

			<!-- Statistics overlay -->
			{#if $mapStatistics && $mapStatistics.visibleCount > 0}
				<div class="stats-overlay">
					<div class="stats-content">
						<span class="stats-count">{$mapStatistics.visibleCount} properties</span>
						{#if $mapStatistics.priceStats}
							<span class="stats-price">
								€{Math.round($mapStatistics.priceStats.min / 1000)}k - €{Math.round($mapStatistics.priceStats.max / 1000)}k
							</span>
						{/if}
					</div>
				</div>
			{/if}
		</div>

		<!-- Mobile property list -->
		<div class="mobile-sidebar" class:collapsed={isSidebarCollapsed}>
			<PropertySidebar 
				{isSidebarCollapsed}
				maxHeight="50vh"
				on:listing-selected={handleListingSelected}
				on:view-details={handleViewDetails}
				on:toggle-collapsed={() => isSidebarCollapsed = !isSidebarCollapsed}
			/>
		</div>
	</div>
</div>

<ToastContainer />

<style>
	.map-page {
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}

	.mobile-header {
		display: none;
		background: white;
		border-bottom: 1px solid #E5E7EB;
		z-index: 50;
	}

	.mobile-header-content {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
	}

	.mobile-title {
		font-size: 18px;
		font-weight: 600;
		margin: 0;
		color: #111827;
	}

	.mobile-actions {
		display: flex;
		gap: 8px;
	}

	.mobile-action-button {
		background: #F9FAFB;
		border: 1px solid #D1D5DB;
		padding: 8px;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
		color: #374151;
	}

	.mobile-action-button:hover,
	.mobile-action-button.active {
		background: #3B82F6;
		border-color: #3B82F6;
		color: white;
	}

	.mobile-search {
		padding: 0 16px 12px;
	}

	.mobile-filters {
		background: white;
		border-bottom: 1px solid #E5E7EB;
		max-height: 50vh;
		overflow-y: auto;
	}

	.map-content {
		flex: 1;
		display: flex;
		overflow: hidden;
	}

	.desktop-sidebar {
		flex-shrink: 0;
		transition: all 0.3s ease;
	}

	.desktop-sidebar.collapsed {
		margin-left: -352px;
	}

	.map-wrapper {
		flex: 1;
		position: relative;
		overflow: hidden;
	}

	.mobile-sidebar {
		display: none;
	}

	.loading-overlay {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(255, 255, 255, 0.8);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.loading-spinner {
		color: #3B82F6;
		animation: spin 1s linear infinite;
	}

	.loading-text {
		margin-top: 12px;
		font-size: 14px;
		color: #6B7280;
	}

	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	.error-overlay {
		position: absolute;
		top: 20px;
		left: 50%;
		transform: translateX(-50%);
		z-index: 1000;
	}

	.error-content {
		background: #FEE2E2;
		border: 1px solid #FECACA;
		color: #DC2626;
		padding: 12px 16px;
		border-radius: 8px;
		display: flex;
		align-items: center;
		gap: 8px;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
		max-width: 400px;
	}

	.retry-button {
		background: #DC2626;
		color: white;
		border: none;
		padding: 4px 8px;
		border-radius: 4px;
		font-size: 12px;
		cursor: pointer;
		margin-left: 8px;
	}

	.stats-overlay {
		position: absolute;
		top: 20px;
		right: 20px;
		z-index: 1000;
	}

	.stats-content {
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(8px);
		padding: 8px 12px;
		border-radius: 8px;
		border: 1px solid #E5E7EB;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		display: flex;
		flex-direction: column;
		gap: 2px;
		font-size: 12px;
	}

	.stats-count {
		font-weight: 600;
		color: #111827;
	}

	.stats-price {
		color: #6B7280;
	}

	/* Mobile responsiveness */
	@media (max-width: 768px) {
		.mobile-header {
			display: block;
		}

		.desktop-sidebar {
			display: none;
		}

		.mobile-sidebar {
			display: block;
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			z-index: 40;
			transition: all 0.3s ease;
		}

		.mobile-sidebar.collapsed {
			transform: translateY(calc(100% - 56px));
		}

		.map-content {
			flex-direction: column;
		}

		.map-wrapper {
			height: calc(100vh - 120px);
		}

		.stats-overlay {
			top: 10px;
			right: 10px;
		}

		.stats-content {
			font-size: 11px;
			padding: 6px 8px;
		}
	}

	@media (max-width: 480px) {
		.mobile-header-content {
			padding: 8px 12px;
		}

		.mobile-title {
			font-size: 16px;
		}

		.mobile-action-button {
			padding: 6px;
		}

		.mobile-search {
			padding: 0 12px 8px;
		}

		.map-wrapper {
			height: calc(100vh - 100px);
		}
	}
</style>