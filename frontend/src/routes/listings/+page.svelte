<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import ListingGrid from '$lib/components/listings/ListingGrid.svelte';
	import FilterPanel from '$lib/components/search/FilterPanel.svelte';
	import { ListingsApi } from '$lib/api/listings';
	import { filters, filterActions, filterSummary } from '$lib/stores/filters';
	import { realtimeActions, hasNewContent, pendingUpdatesCount } from '$lib/stores/realtime';
	import { websocketManager } from '$lib/api/websocket';
	import type { Listing, PaginatedResponse, ListingFilters } from '$lib/types/listing';
	
	// State
	let listings: Listing[] = [];
	let loading = true;
	let error: string | null = null;
	let totalListings = 0;
	let currentPage = 1;
	let hasMore = false;
	let viewMode: 'grid' | 'list' = 'grid';
	let realtimeEnabled = true;
	let showRealtimeUpdates = false;
	
	// Load listings with current filters
	const loadListings = async (page = 1, append = false) => {
		try {
			loading = true;
			error = null;
			
			// Convert store filters to API format
			const apiFilters: ListingFilters = {
				search: $filters.query || undefined,
				minPrice: $filters.minPrice,
				maxPrice: $filters.maxPrice,
				minArea: $filters.minArea,
				maxArea: $filters.maxArea,
				propertyType: $filters.propertyType || undefined,
				location: $filters.location || undefined,
				source: $filters.source || undefined,
				hasImages: $filters.hasImages,
				parking: $filters.parking,
				balcony: $filters.balcony,
				elevator: $filters.elevator
			};
			
			const response = await ListingsApi.getListings(page, 20, apiFilters);
			
			if (response.error) {
				error = response.error;
				return;
			}
			
			const data = response.data as PaginatedResponse<Listing>;
			
			// Ensure we have valid data structure
			if (!data || !data.items || !Array.isArray(data.items)) {
				error = 'Invalid data structure received from API';
				return;
			}
			
			if (append) {
				listings = [...listings, ...data.items];
			} else {
				listings = data.items;
			}
			
			totalListings = data.total;
			currentPage = data.page;
			hasMore = data.has_next;
			
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load listings';
		} finally {
			loading = false;
		}
	};
	
	// Load more listings
	const handleLoadMore = () => {
		if (!loading && hasMore) {
			loadListings(currentPage + 1, true);
		}
	};
	
	// Refresh listings
	const handleRefresh = () => {
		listings = [];
		loadListings(1, false);
	};
	
	// Handle filter application
	const handleApplyFilters = () => {
		filterActions.updateFilter('page', 1);
		loadListings();
		updateURL();
	};
	
	// Handle filter clearing
	const handleClearFilters = () => {
		filterActions.clearFilters();
		loadListings();
		updateURL();
	};
	
	// Handle sort change
	const handleSortChange = (event: Event) => {
		const target = event.target as HTMLSelectElement;
		const [sortBy, sortOrder] = target.value.split('_');
		
		filterActions.updateFilters({
			sortBy: sortBy as any,
			sortOrder: (sortOrder || 'desc') as 'asc' | 'desc',
			page: 1
		});
		
		loadListings();
		updateURL();
	};
	
	// Toggle view mode
	const toggleViewMode = () => {
		viewMode = viewMode === 'grid' ? 'list' : 'grid';
	};
	
	// Toggle real-time updates
	const toggleRealtime = () => {
		realtimeEnabled = !realtimeEnabled;
		if (realtimeEnabled) {
			realtimeActions.startRealtime();
		} else {
			realtimeActions.stopRealtime();
		}
	};
	
	// Apply pending real-time updates
	const applyRealtimeUpdates = () => {
		realtimeActions.applyPendingUpdates();
	};
	
	// Start WebSocket connection and real-time updates
	const startRealtime = () => {
		// Connect WebSocket
		websocketManager.connect();
		
		// Start real-time monitoring
		if (realtimeEnabled) {
			realtimeActions.startRealtime();
		}
	};
	
	// Stop WebSocket connection
	const stopRealtime = () => {
		websocketManager.disconnect();
		realtimeActions.stopRealtime();
	};
	
	// Update URL with current filters
	const updateURL = () => {
		const params = filterActions.getSearchParams();
		const url = params.toString() ? `/listings?${params.toString()}` : '/listings';
		goto(url, { replaceState: true });
	};
	
	// Load initial data
	onMount(() => {
		// Initialize from URL parameters
		const urlParams = $page.url.searchParams;
		if (urlParams.toString()) {
			filterActions.setFromSearchParams(urlParams);
		}
		
		loadListings();
		
		// Start real-time updates after initial load
		setTimeout(() => {
			startRealtime();
		}, 1000);
	});
	
	// Cleanup on component destroy
	onDestroy(() => {
		stopRealtime();
	});
</script>

<svelte:head>
	<title>All Listings - ProScrape</title>
	<meta name="description" content="Browse all available real estate listings from Latvia's top property websites." />
</svelte:head>

<div class="container mx-auto px-4 py-8">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
		<div>
			<h1 class="text-3xl font-bold text-gray-900 mb-2">All Listings</h1>
			{#if !loading && totalListings > 0}
				<p class="text-gray-600">
					Showing {listings.length} of {totalListings.toLocaleString()} properties
				</p>
			{/if}
		</div>
		
		<!-- View Controls -->
		<div class="flex items-center space-x-4">
			<!-- Map View Button -->
			<a 
				href="/map"
				class="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
			>
				<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
				</svg>
				Map View
			</a>
			
			<!-- Real-time Toggle -->
			<div class="flex items-center space-x-2">
				<label class="relative inline-flex items-center cursor-pointer">
					<input
						type="checkbox"
						class="sr-only peer"
						checked={realtimeEnabled}
						on:change={toggleRealtime}
					/>
					<div class="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
				</label>
				<span class="text-sm text-gray-600">Live updates</span>
			</div>
			
			<!-- View Mode Toggle -->
			<div class="flex items-center bg-gray-100 rounded-lg p-1">
				<button
					on:click={toggleViewMode}
					class="p-2 rounded {viewMode === 'grid' ? 'bg-white shadow-sm' : 'text-gray-600'}"
					aria-label="Grid view"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
					</svg>
				</button>
				<button
					on:click={toggleViewMode}
					class="p-2 rounded {viewMode === 'list' ? 'bg-white shadow-sm' : 'text-gray-600'}"
					aria-label="List view"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
					</svg>
				</button>
			</div>
			
			<!-- Sort Dropdown -->
			<select 
				class="input py-2 px-3 text-sm"
				value="{$filters.sortBy}_{$filters.sortOrder}"
				on:change={handleSortChange}
			>
				<option value="posted_date_desc">Recently Posted</option>
				<option value="price_asc">Price: Low to High</option>
				<option value="price_desc">Price: High to Low</option>
				<option value="area_asc">Area: Small to Large</option>
				<option value="area_desc">Area: Large to Small</option>
				<option value="created_at_desc">Recently Added</option>
			</select>
		</div>
	</div>
	
	<!-- Filters Bar -->
	<div class="mb-8">
		<FilterPanel 
			compact={true}
			on:apply={handleApplyFilters}
			on:clear={handleClearFilters}
		/>
	</div>
	
	<!-- Real-time Updates Banner -->
	{#if $hasNewContent && realtimeEnabled}
		<div class="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-3">
					<div class="flex-shrink-0">
						<svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
					</div>
					<div>
						<h3 class="text-sm font-medium text-blue-900">
							New updates available
						</h3>
						<p class="text-sm text-blue-700">
							{$pendingUpdatesCount} new changes found. Click to refresh the listings.
						</p>
					</div>
				</div>
				<div class="flex items-center space-x-2">
					<button
						type="button"
						class="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
						on:click={applyRealtimeUpdates}
					>
						Apply Updates
					</button>
					<button
						type="button"
						class="p-2 text-blue-400 hover:text-blue-600"
						on:click={() => realtimeActions.clearUpdates()}
						aria-label="Dismiss updates"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>
		</div>
	{/if}
	
	<!-- Results -->
	<ListingGrid 
		{listings}
		{loading}
		{error}
		compact={viewMode === 'list'}
		showLoadMore={true}
		{hasMore}
		on:loadMore={handleLoadMore}
		on:refresh={handleRefresh}
	/>
</div>