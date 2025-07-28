<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import PropertyComparison from '$lib/components/engagement/PropertyComparison.svelte';
	import { comparisonProperties } from '$lib/stores/engagement';
	
	// Handle comparison data from URL params (for shared comparisons)
	onMount(() => {
		const comparisonData = $page.url.searchParams.get('data');
		if (comparisonData) {
			try {
				const data = JSON.parse(decodeURIComponent(comparisonData));
				// In a real app, you'd load the properties based on the shared data
				console.log('Loaded shared comparison:', data);
			} catch (error) {
				console.error('Failed to load shared comparison:', error);
			}
		}
	});
	
	function handlePropertyRemoved(event: CustomEvent) {
		console.log('Property removed from comparison:', event.detail);
	}
	
	function handleComparisonCleared(event: CustomEvent) {
		console.log('Comparison cleared');
	}
	
	function handleComparisonShared(event: CustomEvent) {
		console.log('Comparison shared:', event.detail);
	}
	
	function handleComparisonExported(event: CustomEvent) {
		console.log('Comparison exported:', event.detail);
	}
	
	function handlePropertyViewed(event: CustomEvent) {
		const { listing } = event.detail;
		goto(`/listings/${listing.listing_id}`);
	}
	
	function handleAddProperty() {
		goto('/listings');
	}
	
	$: hasProperties = $comparisonProperties.length > 0;
</script>

<svelte:head>
	<title>Property Comparison | ProScrape</title>
	<meta name="description" content="Compare properties side by side to make the best decision. View prices, features, and details in one place." />
</svelte:head>

<div class="min-h-screen bg-gray-50">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Page Header -->
		<div class="mb-8">
			<nav class="flex" aria-label="Breadcrumb">
				<ol class="flex items-center space-x-2">
					<li>
						<a href="/" class="text-gray-500 hover:text-gray-700">Home</a>
					</li>
					<li class="flex items-center">
						<svg class="w-5 h-5 text-gray-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
						</svg>
						<span class="text-gray-500">Property Comparison</span>
					</li>
				</ol>
			</nav>
			
			<div class="mt-4">
				<h1 class="text-3xl font-bold text-gray-900">Property Comparison</h1>
				<p class="mt-2 text-lg text-gray-600">
					{#if hasProperties}
						Compare {$comparisonProperties.length} properties side by side to find your perfect match.
					{:else}
						Start adding properties to compare their features, prices, and details.
					{/if}
				</p>
			</div>
		</div>

		<!-- Comparison Component -->
		<PropertyComparison 
			maxProperties={4}
			showAddButton={true}
			on:propertyRemoved={handlePropertyRemoved}
			on:comparisonCleared={handleComparisonCleared}
			on:comparisonShared={handleComparisonShared}
			on:comparisonExported={handleComparisonExported}
			on:propertyViewed={handlePropertyViewed}
			on:addProperty={handleAddProperty}
		/>
		
		<!-- Help Section -->
		{#if !hasProperties}
			<div class="mt-12 bg-white rounded-lg shadow-sm border border-gray-200 p-8">
				<div class="text-center">
					<svg class="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 008 0m6 0h2a2 2 0 002-2V9a2 2 0 00-2-2h-2m-2 0V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h6z" />
					</svg>
					<h3 class="text-xl font-semibold text-gray-900 mb-2">How to Use Property Comparison</h3>
					<div class="max-w-2xl mx-auto text-gray-600 space-y-4">
						<p>
							Property comparison helps you make informed decisions by viewing multiple properties side by side.
						</p>
						<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6 text-left">
							<div class="flex items-start space-x-3">
								<div class="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
									<span class="text-blue-600 font-medium text-sm">1</span>
								</div>
								<div>
									<h4 class="font-medium text-gray-900">Browse Properties</h4>
									<p class="text-sm text-gray-600">Find properties you're interested in and click the "Compare" button on each listing.</p>
								</div>
							</div>
							<div class="flex items-start space-x-3">
								<div class="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
									<span class="text-blue-600 font-medium text-sm">2</span>
								</div>
								<div>
									<h4 class="font-medium text-gray-900">Compare Side by Side</h4>
									<p class="text-sm text-gray-600">View prices, features, locations, and details in a clear comparison table.</p>
								</div>
							</div>
							<div class="flex items-start space-x-3">
								<div class="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
									<span class="text-blue-600 font-medium text-sm">3</span>
								</div>
								<div>
									<h4 class="font-medium text-gray-900">Make Your Decision</h4>
									<p class="text-sm text-gray-600">Export your comparison or share it with others to help make the best choice.</p>
								</div>
							</div>
						</div>
					</div>
					<div class="mt-8">
						<a 
							href="/listings"
							class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
						>
							<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
							</svg>
							Start Browsing Properties
						</a>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>