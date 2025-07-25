<script lang="ts">
	import { goto } from '$app/navigation';
	import SearchBar from '$lib/components/search/SearchBar.svelte';
	import { filterActions } from '$lib/stores/filters';
	
	// Handle search from homepage
	const handleSearch = (event: CustomEvent<{ query: string }>) => {
		const query = event.detail.query;
		if (query.trim()) {
			goto(`/search?query=${encodeURIComponent(query)}`);
		}
	};
	
	// Handle quick filter buttons
	const handleQuickFilter = (filterId: string) => {
		const filterMap: Record<string, string> = {
			'houses': '/search?propertyType=house',
			'apartments': '/search?propertyType=apartment',
			'under_100k': '/search?maxPrice=100000',
			'100k_200k': '/search?minPrice=100000&maxPrice=200000',
			'over_200k': '/search?minPrice=200000'
		};
		
		const url = filterMap[filterId];
		if (url) {
			goto(url);
		}
	};
</script>

<div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
	<!-- Hero Section -->
	<div class="container mx-auto px-4 py-16">
		<div class="text-center mb-12">
			<h1 class="text-5xl font-bold text-gray-900 mb-4">
				Find Your Perfect <span class="text-primary-600">Property</span> in Latvia
			</h1>
			<p class="text-xl text-gray-600 max-w-2xl mx-auto">
				Search thousands of real estate listings from ss.com, city24.lv, and pp.lv in one place
			</p>
		</div>

		<!-- Search Bar -->
		<div class="max-w-4xl mx-auto mb-16">
			<div class="bg-white rounded-2xl shadow-lg p-8">
				<div class="flex flex-col md:flex-row gap-4">
					<div class="flex-1">
						<SearchBar
							size="lg"
							placeholder="Search by location, property type, or keywords..."
							on:search={handleSearch}
						/>
					</div>
					<a href="/search" class="btn-primary text-lg px-8 py-3 text-center">
						Advanced Search
					</a>
				</div>
				
				<!-- Quick Filters -->
				<div class="flex flex-wrap gap-2 mt-6">
					<button on:click={() => handleQuickFilter('houses')} class="btn-secondary">Houses</button>
					<button on:click={() => handleQuickFilter('apartments')} class="btn-secondary">Apartments</button>
					<button on:click={() => handleQuickFilter('under_100k')} class="btn-secondary">Under €100k</button>
					<button on:click={() => handleQuickFilter('100k_200k')} class="btn-secondary">€100k - €200k</button>
					<button on:click={() => handleQuickFilter('over_200k')} class="btn-secondary">Over €200k</button>
				</div>
			</div>
		</div>

		<!-- Stats -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
			<div class="text-center">
				<div class="text-3xl font-bold text-primary-600">10,000+</div>
				<div class="text-gray-600">Active Listings</div>
			</div>
			<div class="text-center">
				<div class="text-3xl font-bold text-primary-600">3</div>
				<div class="text-gray-600">Data Sources</div>
			</div>
			<div class="text-center">
				<div class="text-3xl font-bold text-primary-600">24/7</div>
				<div class="text-gray-600">Real-time Updates</div>
			</div>
		</div>

		<!-- Featured Listings Preview -->
		<div class="text-center">
			<h2 class="text-3xl font-bold text-gray-900 mb-8">Latest Properties</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				<!-- Placeholder cards -->
				{#each Array(6) as _, i}
					<div class="card">
						<div class="bg-gray-200 h-48 rounded-lg mb-4 animate-pulse"></div>
						<div class="h-4 bg-gray-200 rounded mb-2 animate-pulse"></div>
						<div class="h-4 bg-gray-200 rounded w-2/3 animate-pulse"></div>
					</div>
				{/each}
			</div>
			<div class="mt-8">
				<a href="/listings" class="btn-primary text-lg px-8 py-3">
					View All Listings
				</a>
			</div>
		</div>
	</div>
</div>
