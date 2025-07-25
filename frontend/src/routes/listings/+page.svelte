<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import ListingGrid from '$lib/components/listings/ListingGrid.svelte';
	import FilterPanel from '$lib/components/search/FilterPanel.svelte';
	import { ListingsApi } from '$lib/api/listings';
	import { filters, filterActions, filterSummary } from '$lib/stores/filters';
	import type { Listing, PaginatedResponse, ListingFilters } from '$lib/types/listing';
	
	// State
	let listings: Listing[] = [];
	let loading = true;
	let error: string | null = null;
	let totalListings = 0;
	let currentPage = 1;
	let hasMore = false;
	let viewMode: 'grid' | 'list' = 'grid';
	
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
			
			if (append) {
				listings = [...listings, ...data.items];
			} else {
				listings = data.items;
			}
			
			totalListings = data.total;
			currentPage = data.page;
			hasMore = data.hasNext;
			
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