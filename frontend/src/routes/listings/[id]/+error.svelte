<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	$: error = $page.error;
	$: listingId = $page.params.id;

	function goBack() {
		if (history.length > 1) {
			history.back();
		} else {
			goto('/listings');
		}
	}

	function searchSimilar() {
		goto('/listings');
	}

	function reportIssue() {
		const subject = encodeURIComponent(`Issue with listing ${listingId}`);
		const body = encodeURIComponent(`I encountered an issue with listing ID: ${listingId}\n\nError: ${error?.message}\n\nPlease investigate.`);
		window.location.href = `mailto:support@proscrape.com?subject=${subject}&body=${body}`;
	}
</script>

<svelte:head>
	<title>Property Not Found | ProScrape</title>
	<meta name="description" content="The requested property listing could not be found." />
</svelte:head>

<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4 sm:px-6 lg:px-8">
	<div class="max-w-md w-full text-center">
		<!-- Error Icon -->
		<div class="mb-8">
			{#if error?.status === 404}
				<svg class="w-24 h-24 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
				</svg>
			{:else}
				<svg class="w-24 h-24 mx-auto text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
				</svg>
			{/if}
		</div>

		<!-- Error Message -->
		<div class="mb-8">
			{#if error?.status === 404}
				<h1 class="text-3xl font-bold text-gray-900 mb-4">
					Property Not Found
				</h1>
				<p class="text-lg text-gray-600 mb-2">
					Sorry, we couldn't find the property listing you're looking for.
				</p>
				<p class="text-gray-500">
					Listing ID: <span class="font-mono font-medium">{listingId}</span>
				</p>
			{:else}
				<h1 class="text-3xl font-bold text-gray-900 mb-4">
					Something Went Wrong
				</h1>
				<p class="text-lg text-gray-600 mb-2">
					We encountered an error while loading this property.
				</p>
				{#if error?.message}
					<p class="text-sm text-gray-500 bg-gray-100 rounded-lg p-3 mb-4 font-mono">
						{error.message}
					</p>
				{/if}
			{/if}
		</div>

		<!-- Possible Reasons -->
		{#if error?.status === 404}
			<div class="bg-blue-50 rounded-lg p-4 mb-8 text-left">
				<h3 class="font-semibold text-blue-900 mb-2">This might happen if:</h3>
				<ul class="text-sm text-blue-800 space-y-1">
					<li>• The property listing has been removed or sold</li>
					<li>• The listing ID is incorrect or outdated</li>
					<li>• The property was temporarily delisted</li>
					<li>• You followed an old or broken link</li>
				</ul>
			</div>
		{/if}

		<!-- Action Buttons -->
		<div class="space-y-3">
			<div class="flex flex-col sm:flex-row gap-3 justify-center">
				<button
					on:click={goBack}
					class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
				>
					<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
					Go Back
				</button>

				<button
					on:click={searchSimilar}
					class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
				>
					<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
					Browse Properties
				</button>
			</div>

			{#if error?.status !== 404}
				<button
					on:click={reportIssue}
					class="inline-flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
				>
					<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
					</svg>
					Report this issue
				</button>
			{/if}
		</div>

		<!-- Help Section -->
		<div class="mt-12 pt-8 border-t border-gray-200">
			<h3 class="text-lg font-medium text-gray-900 mb-4">Need Help?</h3>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
				<a 
					href="/listings" 
					class="flex items-center justify-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
				>
					<svg class="w-5 h-5 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
					</svg>
					All Properties
				</a>
				
				<a 
					href="/search" 
					class="flex items-center justify-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
				>
					<svg class="w-5 h-5 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
					Advanced Search
				</a>
			</div>
		</div>
	</div>
</div>