<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	
	// Store imports
	import { 
		savedListings, 
		savedListingsActions, 
		priceAlerts, 
		activePriceAlerts 
	} from '$lib/stores/savedListings';
	import { 
		savedSearches, 
		searchCollections, 
		searchHistoryActions,
		savedSearchesWithAlerts 
	} from '$lib/stores/searchHistory';
	import { contactInquiries, recentInquiries } from '$lib/stores/contactLeads';
	import { userPreferences, displayPreferences } from '$lib/stores/userPreferences';
	import { analyticsActions } from '$lib/stores/analytics';
	import { notificationActions } from '$lib/stores/notifications';
	
	// Component imports
	import ListingCard from '$lib/components/listings/ListingCard.svelte';
	import Toast from '$lib/components/notifications/Toast.svelte';
	
	// Types
	import type { SavedListing } from '$lib/stores/savedListings';
	import type { SavedSearch } from '$lib/stores/searchHistory';
	
	// State
	let activeTab: 'properties' | 'searches' | 'collections' | 'inquiries' | 'alerts' = 'properties';
	let selectedListings: Set<string> = new Set();
	let showBulkActions = false;
	let sortBy: 'saved_date' | 'price' | 'posted_date' | 'title' = 'saved_date';
	let sortOrder: 'asc' | 'desc' = 'desc';
	let searchFilter = '';
	let showExportModal = false;
	let showImportModal = false;
	let importData = '';
	
	// Reactive statements
	$: filteredSavedListings = $savedListings
		.filter(saved => {
			if (!searchFilter) return true;
			const query = searchFilter.toLowerCase();
			return (
				saved.listing.title.toLowerCase().includes(query) ||
				saved.listing.location?.toLowerCase().includes(query) ||
				saved.notes?.toLowerCase().includes(query)
			);
		})
		.sort((a, b) => {
			let comparison = 0;
			
			switch (sortBy) {
				case 'saved_date':
					comparison = new Date(a.saved_at).getTime() - new Date(b.saved_at).getTime();
					break;
				case 'price':
					const priceA = parseFloat(a.listing.price.replace(/[^\d.]/g, ''));
					const priceB = parseFloat(b.listing.price.replace(/[^\d.]/g, ''));
					comparison = priceA - priceB;
					break;
				case 'posted_date':
					comparison = new Date(a.listing.posted_date || 0).getTime() - new Date(b.listing.posted_date || 0).getTime();
					break;
				case 'title':
					comparison = a.listing.title.localeCompare(b.listing.title);
					break;
			}
			
			return sortOrder === 'desc' ? -comparison : comparison;
		});
	
	$: viewMode = $displayPreferences.viewMode;
	
	// Functions
	function handleTabChange(tab: typeof activeTab) {
		activeTab = tab;
		analyticsActions.trackInteraction('click', `saved-tab-${tab}`, '/saved');
	}
	
	function handleListingSelect(listingId: string) {
		if (selectedListings.has(listingId)) {
			selectedListings.delete(listingId);
		} else {
			selectedListings.add(listingId);
		}
		selectedListings = selectedListings;
		showBulkActions = selectedListings.size > 0;
	}
	
	function selectAllListings() {
		if (selectedListings.size === filteredSavedListings.length) {
			selectedListings.clear();
		} else {
			selectedListings = new Set(filteredSavedListings.map(s => s.listing_id));
		}
		selectedListings = selectedListings;
		showBulkActions = selectedListings.size > 0;
	}
	
	function handleBulkRemove() {
		if (confirm(`Remove ${selectedListings.size} saved listings?`)) {
			selectedListings.forEach(listingId => {
				savedListingsActions.removeListing(listingId);
			});
			selectedListings.clear();
			selectedListings = selectedListings;
			showBulkActions = false;
			
			notificationActions.addToast({
				type: 'success',
				title: 'Listings Removed',
				message: `${selectedListings.size} listings have been removed from your saved collection.`,
				duration: 3000
			});
		}
	}
	
	function handleBulkExport() {
		const selectedSavedListings = $savedListings.filter(s => selectedListings.has(s.listing_id));
		const exportData = JSON.stringify(selectedSavedListings, null, 2);
		
		const blob = new Blob([exportData], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `saved-listings-${new Date().toISOString().split('T')[0]}.json`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
		
		analyticsActions.trackGoal('export_saved_listings', { count: selectedListings.size });
		selectedListings.clear();
		selectedListings = selectedListings;
		showBulkActions = false;
	}
	
	function handleExportAll() {
		const exportData = savedListingsActions.exportSavedListings();
		const blob = new Blob([exportData], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `proscrape-saved-listings-${new Date().toISOString().split('T')[0]}.json`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
		
		showExportModal = false;
		analyticsActions.trackGoal('export_all_saved_listings');
	}
	
	function handleImport() {
		try {
			if (savedListingsActions.importSavedListings(importData)) {
				showImportModal = false;
				importData = '';
			}
		} catch (error) {
			console.error('Import failed:', error);
		}
	}
	
	function executeSavedSearch(searchId: string) {
		const filters = searchHistoryActions.executeSavedSearch(searchId);
		if (filters) {
			goto(`/search?${new URLSearchParams(filters as any).toString()}`);
		}
	}
	
	function viewListing(listingId: string) {
		analyticsActions.trackPropertyView(listingId, 'saved_listings');
		goto(`/listings/${listingId}`);
	}
	
	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}
	
	function formatPrice(price: string): string {
		const prefs = $userPreferences;
		const numPrice = parseFloat(price.replace(/[^\d.]/g, ''));
		
		if (prefs.display.priceFormat === 'K_EUR' && numPrice >= 1000) {
			return `€${(numPrice / 1000).toFixed(0)}K`;
		}
		
		return `€${numPrice.toLocaleString()}`;
	}
	
	onMount(() => {
		analyticsActions.trackPageView('/saved');
		
		// Check URL parameters for initial tab
		const urlTab = $page.url.searchParams.get('tab');
		if (urlTab && ['properties', 'searches', 'collections', 'inquiries', 'alerts'].includes(urlTab)) {
			activeTab = urlTab as typeof activeTab;
		}
	});
</script>

<svelte:head>
	<title>Saved Items - ProScrape Real Estate</title>
	<meta name="description" content="Manage your saved properties, searches, and inquiries" />
</svelte:head>

<div class="container mx-auto px-4 py-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
			Saved Items
		</h1>
		<p class="text-gray-600 dark:text-gray-400">
			Manage your saved properties, searches, and inquiries
		</p>
	</div>

	<!-- Tabs -->
	<div class="mb-6">
		<div class="border-b border-gray-200 dark:border-gray-700">
			<nav class="-mb-px flex space-x-8">
				<button
					class="tab-button {activeTab === 'properties' ? 'active' : ''}"
					on:click={() => handleTabChange('properties')}
				>
					Properties
					<span class="ml-2 bg-blue-100 text-blue-600 px-2 py-1 rounded-full text-xs">
						{$savedListings.length}
					</span>
				</button>
				
				<button
					class="tab-button {activeTab === 'searches' ? 'active' : ''}"
					on:click={() => handleTabChange('searches')}
				>
					Saved Searches
					<span class="ml-2 bg-green-100 text-green-600 px-2 py-1 rounded-full text-xs">
						{$savedSearches.length}
					</span>
				</button>
				
				<button
					class="tab-button {activeTab === 'collections' ? 'active' : ''}"
					on:click={() => handleTabChange('collections')}
				>
					Collections
					<span class="ml-2 bg-purple-100 text-purple-600 px-2 py-1 rounded-full text-xs">
						{$searchCollections.length}
					</span>
				</button>
				
				<button
					class="tab-button {activeTab === 'inquiries' ? 'active' : ''}"
					on:click={() => handleTabChange('inquiries')}
				>
					Inquiries
					<span class="ml-2 bg-orange-100 text-orange-600 px-2 py-1 rounded-full text-xs">
						{$contactInquiries.length}
					</span>
				</button>
				
				<button
					class="tab-button {activeTab === 'alerts' ? 'active' : ''}"
					on:click={() => handleTabChange('alerts')}
				>
					Price Alerts
					<span class="ml-2 bg-red-100 text-red-600 px-2 py-1 rounded-full text-xs">
						{$activePriceAlerts.length}
					</span>
				</button>
			</nav>
		</div>
	</div>

	<!-- Properties Tab -->
	{#if activeTab === 'properties'}
		<div class="space-y-6">
			<!-- Toolbar -->
			<div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
				<div class="flex flex-col sm:flex-row gap-4 flex-1">
					<!-- Search -->
					<div class="relative flex-1 max-w-md">
						<input
							type="text"
							placeholder="Search saved properties..."
							bind:value={searchFilter}
							class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						/>
						<svg class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
						</svg>
					</div>
					
					<!-- Sort -->
					<div class="flex gap-2">
						<select bind:value={sortBy} class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
							<option value="saved_date">Saved Date</option>
							<option value="price">Price</option>
							<option value="posted_date">Posted Date</option>
							<option value="title">Title</option>
						</select>
						
						<button
							on:click={() => sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'}
							class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-700 dark:border-gray-600 dark:hover:bg-gray-600"
						>
							{sortOrder === 'asc' ? '↑' : '↓'}
						</button>
					</div>
				</div>
				
				<!-- Actions -->
				<div class="flex gap-2">
					<button
						on:click={selectAllListings}
						class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:hover:bg-gray-600"
					>
						{selectedListings.size === filteredSavedListings.length ? 'Deselect All' : 'Select All'}
					</button>
					
					<button
						on:click={() => showExportModal = true}
						class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:hover:bg-gray-600"
					>
						Export
					</button>
					
					<button
						on:click={() => showImportModal = true}
						class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:hover:bg-gray-600"
					>
						Import
					</button>
				</div>
			</div>
			
			<!-- Bulk Actions -->
			{#if showBulkActions}
				<div class="bg-blue-50 border border-blue-200 rounded-lg p-4 dark:bg-blue-900/20 dark:border-blue-800">
					<div class="flex items-center justify-between">
						<span class="text-sm text-blue-700 dark:text-blue-300">
							{selectedListings.size} properties selected
						</span>
						<div class="flex gap-2">
							<button
								on:click={handleBulkExport}
								class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
							>
								Export Selected
							</button>
							<button
								on:click={handleBulkRemove}
								class="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
							>
								Remove Selected
							</button>
						</div>
					</div>
				</div>
			{/if}
			
			<!-- Properties Grid/List -->
			{#if filteredSavedListings.length === 0}
				<div class="text-center py-12">
					{#if $savedListings.length === 0}
						<div class="text-gray-500 dark:text-gray-400">
							<svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
							</svg>
							<h3 class="text-lg font-medium mb-2">No saved properties yet</h3>
							<p class="mb-4">Start exploring properties and save your favorites</p>
							<button
								on:click={() => goto('/search')}
								class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
							>
								Browse Properties
							</button>
						</div>
					{:else}
						<div class="text-gray-500 dark:text-gray-400">
							<p>No properties match your search criteria</p>
							<button
								on:click={() => searchFilter = ''}
								class="mt-2 text-blue-600 hover:text-blue-700"
							>
								Clear search
							</button>
						</div>
					{/if}
				</div>
			{:else}
				<div class="grid gap-6 {viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}">
					{#each filteredSavedListings as saved (saved.listing_id)}
						<div class="relative">
							<!-- Selection checkbox -->
							<label class="absolute top-4 left-4 z-10 flex items-center">
								<input
									type="checkbox"
									checked={selectedListings.has(saved.listing_id)}
									on:change={() => handleListingSelect(saved.listing_id)}
									class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
								/>
							</label>
							
							<!-- Listing Card -->
							<div class="listing-card-wrapper" on:click={() => viewListing(saved.listing_id)}>
								<ListingCard listing={saved.listing} compact={viewMode === 'list'} />
							</div>
							
							<!-- Saved info overlay -->
							<div class="absolute bottom-4 right-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 border border-gray-200 dark:border-gray-700">
								<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">
									Saved {formatDate(saved.saved_at)}
								</div>
								{#if saved.notes}
									<div class="text-sm text-gray-700 dark:text-gray-300 mb-2">
										{saved.notes}
									</div>
								{/if}
								{#if saved.price_alerts}
									<div class="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
										<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
											<path d="M10 2L3 7v11h4v-6h6v6h4V7l-7-5z"/>
										</svg>
										Price alerts on
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- Saved Searches Tab -->
	{#if activeTab === 'searches'}
		<div class="space-y-6">
			{#if $savedSearches.length === 0}
				<div class="text-center py-12">
					<div class="text-gray-500 dark:text-gray-400">
						<svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
						</svg>
						<h3 class="text-lg font-medium mb-2">No saved searches yet</h3>
						<p class="mb-4">Save your search criteria to get notified of new matching properties</p>
						<button
							on:click={() => goto('/search')}
							class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
						>
							Create Search
						</button>
					</div>
				</div>
			{:else}
				<div class="grid gap-6 grid-cols-1 md:grid-cols-2">
					{#each $savedSearchesWithAlerts as search (search.id)}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-6">
							<div class="flex items-start justify-between mb-4">
								<div>
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
										{search.name}
									</h3>
									{#if search.description}
										<p class="text-sm text-gray-600 dark:text-gray-400">
											{search.description}
										</p>
									{/if}
								</div>
								
								<div class="flex items-center gap-2">
									{#if search.alertsEnabled}
										<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
											<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
												<path d="M10 2L3 7v11h4v-6h6v6h4V7l-7-5z"/>
											</svg>
											Alerts On
										</span>
									{/if}
								</div>
							</div>
							
							<!-- Search criteria preview -->
							<div class="mb-4 space-y-2">
								{#if search.filters.query}
									<div class="text-sm">
										<span class="text-gray-500 dark:text-gray-400">Query:</span>
										<span class="ml-1 font-medium">{search.filters.query}</span>
									</div>
								{/if}
								
								{#if search.filters.propertyType}
									<div class="text-sm">
										<span class="text-gray-500 dark:text-gray-400">Type:</span>
										<span class="ml-1 font-medium">{search.filters.propertyType}</span>
									</div>
								{/if}
								
								{#if search.filters.minPrice || search.filters.maxPrice}
									<div class="text-sm">
										<span class="text-gray-500 dark:text-gray-400">Price:</span>
										<span class="ml-1 font-medium">
											{formatPrice(search.filters.minPrice?.toString() || '0')} - {formatPrice(search.filters.maxPrice?.toString() || '999999')}
										</span>
									</div>
								{/if}
								
								{#if search.filters.location}
									<div class="text-sm">
										<span class="text-gray-500 dark:text-gray-400">Location:</span>
										<span class="ml-1 font-medium">{search.filters.location}</span>
									</div>
								{/if}
							</div>
							
							<!-- Tags -->
							{#if search.tags.length > 0}
								<div class="mb-4">
									<div class="flex flex-wrap gap-1">
										{#each search.tags as tag}
											<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
												{tag}
											</span>
										{/each}
									</div>
								</div>
							{/if}
							
							<!-- Stats -->
							<div class="mb-4 grid grid-cols-2 gap-4 text-sm">
								<div>
									<span class="text-gray-500 dark:text-gray-400">Created:</span>
									<div class="font-medium">{formatDate(search.createdAt)}</div>
								</div>
								
								{#if search.lastExecuted}
									<div>
										<span class="text-gray-500 dark:text-gray-400">Last run:</span>
										<div class="font-medium">{formatDate(search.lastExecuted)}</div>
									</div>
								{/if}
								
								<div>
									<span class="text-gray-500 dark:text-gray-400">Executions:</span>
									<div class="font-medium">{search.executionCount}</div>
								</div>
								
								{#if search.resultCount !== undefined}
									<div>
										<span class="text-gray-500 dark:text-gray-400">Results:</span>
										<div class="font-medium">{search.resultCount}</div>
									</div>
								{/if}
							</div>
							
							<!-- Actions -->
							<div class="flex gap-2">
								<button
									on:click={() => executeSavedSearch(search.id)}
									class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
								>
									Run Search
								</button>
								
								<button
									on:click={() => searchHistoryActions.deleteSavedSearch(search.id)}
									class="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 text-sm font-medium"
								>
									Delete
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- Collections Tab -->
	{#if activeTab === 'collections'}
		<div class="space-y-6">
			{#if $searchCollections.length === 0}
				<div class="text-center py-12">
					<div class="text-gray-500 dark:text-gray-400">
						<svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
						</svg>
						<h3 class="text-lg font-medium mb-2">No search collections yet</h3>
						<p class="mb-4">Organize your saved searches into collections</p>
						<button
							class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
						>
							Create Collection
						</button>
					</div>
				</div>
			{:else}
				<div class="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
					{#each $searchCollections as collection (collection.id)}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-6">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
								{collection.name}
							</h3>
							
							{#if collection.description}
								<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
									{collection.description}
								</p>
							{/if}
							
							<div class="text-sm text-gray-500 dark:text-gray-400 mb-4">
								{collection.savedSearches.length} saved searches
							</div>
							
							{#if collection.tags.length > 0}
								<div class="mb-4">
									<div class="flex flex-wrap gap-1">
										{#each collection.tags as tag}
											<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
												{tag}
											</span>
										{/each}
									</div>
								</div>
							{/if}
							
							<div class="text-xs text-gray-500 dark:text-gray-400">
								Created {formatDate(collection.createdAt)}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- Inquiries Tab -->
	{#if activeTab === 'inquiries'}
		<div class="space-y-6">
			{#if $contactInquiries.length === 0}
				<div class="text-center py-12">
					<div class="text-gray-500 dark:text-gray-400">
						<svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 7.89a2 2 0 002.83 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
						</svg>
						<h3 class="text-lg font-medium mb-2">No inquiries yet</h3>
						<p class="mb-4">Contact agents about properties you're interested in</p>
						<button
							on:click={() => goto('/search')}
							class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
						>
							Browse Properties
						</button>
					</div>
				</div>
			{:else}
				<div class="space-y-4">
					{#each $recentInquiries as inquiry (inquiry.id)}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
							<div class="flex items-start justify-between mb-4">
								<div>
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
										{inquiry.subject}
									</h3>
									<p class="text-sm text-gray-600 dark:text-gray-400">
										{inquiry.type.replace('_', ' ')} • {formatDate(inquiry.createdAt)}
									</p>
								</div>
								
								<div class="flex items-center gap-2">
									<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium 
										{inquiry.status === 'pending' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
										 inquiry.status === 'responded' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
										 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'}">
										{inquiry.status}
									</span>
									
									<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
										{inquiry.priority === 'urgent' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
										 inquiry.priority === 'high' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' :
										 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}">
										{inquiry.priority}
									</span>
								</div>
							</div>
							
							<div class="mb-4">
								<p class="text-sm text-gray-700 dark:text-gray-300">
									{inquiry.message}
								</p>
							</div>
							
							<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
								<div>
									<span class="text-gray-500 dark:text-gray-400">Property:</span>
									<div class="font-medium">
										<button
											on:click={() => viewListing(inquiry.listingId)}
											class="text-blue-600 hover:text-blue-700 dark:text-blue-400"
										>
											View Listing
										</button>
									</div>
								</div>
								
								<div>
									<span class="text-gray-500 dark:text-gray-400">Contact:</span>
									<div class="font-medium">{inquiry.contactInfo.name}</div>
								</div>
								
								<div>
									<span class="text-gray-500 dark:text-gray-400">Method:</span>
									<div class="font-medium">{inquiry.contactInfo.preferredContact}</div>
								</div>
								
								<div>
									<span class="text-gray-500 dark:text-gray-400">Source:</span>
									<div class="font-medium">{inquiry.source.replace('_', ' ')}</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- Price Alerts Tab -->
	{#if activeTab === 'alerts'}
		<div class="space-y-6">
			{#if $priceAlerts.length === 0}
				<div class="text-center py-12">
					<div class="text-gray-500 dark:text-gray-400">
						<svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-5 5l-5-5h5v-12"></path>
						</svg>
						<h3 class="text-lg font-medium mb-2">No price alerts</h3>
						<p class="mb-4">Enable price alerts on your saved properties to get notified of price changes</p>
						<button
							on:click={() => handleTabChange('properties')}
							class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
						>
							Manage Saved Properties
						</button>
					</div>
				</div>
			{:else}
				<div class="space-y-4">
					{#each $priceAlerts as alert (alert.id)}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
							<div class="flex items-start justify-between mb-4">
								<div>
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
										Price {alert.type.replace('_', ' ')} Alert
									</h3>
									{#if alert.triggered_at}
										<p class="text-sm text-gray-600 dark:text-gray-400">
											Triggered {formatDate(alert.triggered_at)}
										</p>
									{/if}
								</div>
								
								<div class="flex items-center gap-2">
									{#if !alert.acknowledged}
										<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
											New
										</span>
									{/if}
									
									<button
										on:click={() => savedListingsActions.acknowledgePriceAlert(alert.id)}
										class="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
									>
										{alert.acknowledged ? 'Acknowledged' : 'Mark as Read'}
									</button>
								</div>
							</div>
							
							<div class="grid grid-cols-2 gap-4 text-sm">
								<div>
									<span class="text-gray-500 dark:text-gray-400">Property:</span>
									<div class="font-medium">
										<button
											on:click={() => viewListing(alert.listing_id)}
											class="text-blue-600 hover:text-blue-700 dark:text-blue-400"
										>
											View Listing
										</button>
									</div>
								</div>
								
								<div>
									<span class="text-gray-500 dark:text-gray-400">Change:</span>
									<div class="font-medium text-{alert.type === 'price_drop' ? 'green' : 'red'}-600">
										{alert.threshold.toFixed(1)}%
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Export Modal -->
{#if showExportModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
				Export Saved Listings
			</h3>
			
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
				Export all your saved listings as a JSON file that can be imported later.
			</p>
			
			<div class="flex gap-3">
				<button
					on:click={handleExportAll}
					class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
				>
					Export All
				</button>
				<button
					on:click={() => showExportModal = false}
					class="flex-1 px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
				>
					Cancel
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Import Modal -->
{#if showImportModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
				Import Saved Listings
			</h3>
			
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
				Paste the JSON data from a previous export to import saved listings.
			</p>
			
			<textarea
				bind:value={importData}
				placeholder="Paste JSON data here..."
				class="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
			></textarea>
			
			<div class="flex gap-3 mt-4">
				<button
					on:click={handleImport}
					disabled={!importData.trim()}
					class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					Import
				</button>
				<button
					on:click={() => { showImportModal = false; importData = ''; }}
					class="flex-1 px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
				>
					Cancel
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.tab-button {
		@apply py-2 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300;
		white-space: nowrap;
		display: flex;
		align-items: center;
	}
	
	.tab-button.active {
		@apply border-blue-500 text-blue-600 dark:text-blue-400;
	}
	
	.listing-card-wrapper {
		@apply cursor-pointer transition-transform hover:scale-105;
	}
</style>