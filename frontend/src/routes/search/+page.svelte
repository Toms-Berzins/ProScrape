<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import SearchBar from '$lib/components/search/SearchBar.svelte';
	import FilterPanel from '$lib/components/search/FilterPanel.svelte';
	import ListingGrid from '$lib/components/listings/ListingGrid.svelte';
	import { filters, filterActions, filterSummary, searchQuery, searchResults, filtersLoading } from '$lib/stores/filters';
	import { ListingsApi } from '$lib/api/listings';
	import type { Listing, ListingFilters, PaginatedResponse } from '$lib/types/listing';
	
	let currentPage = 1;
	let isSearching = false;
	
	// Perform search with current filters
	const performSearch = async (append = false) => {
		if (isSearching) return;
		
		try {
			isSearching = true;
			filtersLoading.set(true);
			
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
			
			const response = await ListingsApi.getListings(
				$filters.page || 1,
				$filters.limit || 20,
				apiFilters
			);
			
			if (response.error) {
				searchResults.update(state => ({
					...state,
					error: response.error!,
					listings: append ? state.listings : []
				}));
				return;
			}
			
			const data = response.data as PaginatedResponse<Listing>;
			
			searchResults.update(state => ({
				listings: append ? [...state.listings, ...data.items] : data.items,
				total: data.total,
				hasMore: data.hasNext,
				error: null
			}));
			
			currentPage = data.page;
			
			// Add to search history if there's a query
			if ($filters.query) {
				filterActions.addToHistory($filters.query, data.total);
			}
			
		} catch (error) {
			searchResults.update(state => ({
				...state,
				error: error instanceof Error ? error.message : 'Search failed',
				listings: append ? state.listings : []
			}));
		} finally {
			isSearching = false;
			filtersLoading.set(false);
		}
	};
	
	// Handle search from search bar
	const handleSearch = (event: CustomEvent<{ query: string }>) => {
		performSearch();
		updateURL();
	};
	
	// Handle filter application
	const handleApplyFilters = () => {
		filterActions.updateFilter('page', 1);
		performSearch();
		updateURL();
	};
	
	// Handle filter clearing
	const handleClearFilters = () => {
		filterActions.updateFilter('page', 1);
		performSearch();
		updateURL();
	};
	
	// Handle load more
	const handleLoadMore = () => {
		const nextPage = currentPage + 1;
		filterActions.updateFilter('page', nextPage);
		performSearch(true);
	};
	
	// Handle refresh
	const handleRefresh = () => {
		filterActions.updateFilter('page', 1);
		performSearch();
	};
	
	// Update URL with current filters
	const updateURL = () => {
		const params = filterActions.getSearchParams();
		const url = params.toString() ? `/search?${params.toString()}` : '/search';
		goto(url, { replaceState: true });
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
		
		performSearch();
		updateURL();
	};
	
	// Initialize from URL parameters
	onMount(() => {
		const urlParams = $page.url.searchParams;
		if (urlParams.toString()) {
			filterActions.setFromSearchParams(urlParams);
		}
		
		// Perform initial search if there are filters or query
		if ($filters.query || $filterSummary.hasActiveFilters) {
			performSearch();
		}
	});
	
</script>

<svelte:head>
	<title>Advanced Search - ProScrape</title>
	<meta name="description" content="Find your perfect property with advanced search filters. Search by price, area, location, and more." />
</svelte:head>

<div class="container mx-auto px-4 py-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">Advanced Property Search</h1>
		<p class="text-gray-600">Use detailed filters to find exactly what you're looking for</p>
	</div>
	
	<!-- Search Bar -->
	<div class="mb-6">
		<SearchBar
			size="lg"
			showSuggestions={true}
			on:search={handleSearch}
			on:clear={handleClearFilters}
		/>
	</div>
	
	<!-- Filter Summary -->
	{#if $filterSummary.hasActiveFilters}
		<div class="mb-6 p-4 bg-primary-50 border border-primary-200 rounded-lg">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-2">
					<span class="text-sm font-medium text-primary-900">Active Filters:</span>
					<div class="flex flex-wrap gap-2">
						{#each $filterSummary.items as filter}
							<span class="bg-primary-100 text-primary-800 text-xs font-medium px-2 py-1 rounded">
								{filter}
							</span>
						{/each}
					</div>
				</div>
				<button
					on:click={handleClearFilters}
					class="text-primary-600 hover:text-primary-700 text-sm font-medium"
				>
					Clear All
				</button>
			</div>
		</div>
	{/if}
	
	<div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
		<!-- Filters Sidebar -->
		<div class="lg:col-span-1">
			<div class="sticky top-4">
				<FilterPanel
					on:apply={handleApplyFilters}
					on:clear={handleClearFilters}
				/>
			</div>
		</div>
		
		<!-- Results -->
		<div class="lg:col-span-3">
			<!-- Results Header -->
			<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
				<div>
					{#if $searchResults.total > 0}
						<h2 class="text-xl font-semibold text-gray-900">
							{$searchResults.total.toLocaleString()} Properties Found
						</h2>
						{#if $filters.query}
							<p class="text-gray-600">Results for "{$filters.query}"</p>
						{/if}
					{:else if !$filtersLoading && ($filterSummary.hasActiveFilters || $filters.query)}
						<h2 class="text-xl font-semibold text-gray-900">No Properties Found</h2>
						<p class="text-gray-600">Try adjusting your search criteria</p>
					{:else if !$filterSummary.hasActiveFilters && !$filters.query}
						<h2 class="text-xl font-semibold text-gray-900">Start Your Search</h2>
						<p class="text-gray-600">Use the search bar or filters to find properties</p>
					{/if}
				</div>
				
				<!-- Sort Options -->
				{#if $searchResults.listings.length > 0}
					<div class="flex items-center space-x-2">
						<label class="text-sm text-gray-600">Sort by:</label>
						<select
							on:change={handleSortChange}
							value="{$filters.sortBy}_{$filters.sortOrder}"
							class="input py-2 px-3 text-sm"
						>
							<option value="posted_date_desc">Recently Posted</option>
							<option value="price_asc">Price: Low to High</option>
							<option value="price_desc">Price: High to Low</option>
							<option value="area_asc">Area: Small to Large</option>
							<option value="area_desc">Area: Large to Small</option>
							<option value="created_at_desc">Recently Added</option>
						</select>
					</div>
				{/if}
			</div>
			
			<!-- Search Results -->
			<ListingGrid
				listings={$searchResults.listings}
				loading={$filtersLoading}
				error={$searchResults.error}
				showLoadMore={true}
				hasMore={$searchResults.hasMore}
				on:loadMore={handleLoadMore}
				on:refresh={handleRefresh}
			/>
			
			<!-- No filters applied state -->
			{#if !$filterSummary.hasActiveFilters && !$filters.query && !$filtersLoading}
				<div class="text-center py-12">
					<svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
					<h3 class="text-lg font-medium text-gray-900 mb-2">Start searching for properties</h3>
					<p class="text-gray-600 mb-6">Enter keywords or use the filters to find your perfect property</p>
					<div class="flex flex-col sm:flex-row gap-4 justify-center">
						<a href="/listings" class="btn-primary">
							Browse All Listings
						</a>
						<button
							on:click={() => filterActions.toggleQuickFilter('apartments', { propertyType: 'apartment' })}
							class="btn-secondary"
						>
							Search Apartments
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>