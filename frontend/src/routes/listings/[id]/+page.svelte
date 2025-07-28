<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	
	import ImageGallery from '$lib/components/listings/ImageGallery.svelte';
	import PropertyDetails from '$lib/components/listings/PropertyDetails.svelte';
	import ContactSection from '$lib/components/listings/ContactSection.svelte';
	import SimilarProperties from '$lib/components/listings/SimilarProperties.svelte';
	import RecentlyViewed from '$lib/components/engagement/RecentlyViewed.svelte';
	
	export let data: PageData;
	
	$: listing = data.listing;
	$: similarListings = data.similarListings || [];
	$: meta = data.meta;
	
	let scrollY = 0;
	let showScrollTop = false;
	let isLoading = false;
	
	// Update scroll top button visibility
	$: showScrollTop = scrollY > 500;
	
	onMount(() => {
		// Track page view for analytics
		console.log('Property page viewed:', listing.id);
		
		// Update page metadata
		if (meta) {
			document.title = `${meta.title} | ProScrape`;
			
			// Update meta tags
			const updateMetaTag = (name: string, content: string) => {
				let tag = document.querySelector(`meta[name="${name}"]`) || 
						 document.querySelector(`meta[property="${name}"]`);
				if (!tag) {
					tag = document.createElement('meta');
					if (name.startsWith('og:') || name.startsWith('twitter:')) {
						tag.setAttribute('property', name);
					} else {
						tag.setAttribute('name', name);
					}
					document.head.appendChild(tag);
				}
				tag.setAttribute('content', content);
			};
			
			updateMetaTag('description', meta.description);
			updateMetaTag('og:title', meta.title);
			updateMetaTag('og:description', meta.description);
			updateMetaTag('og:url', meta.url);
			updateMetaTag('twitter:title', meta.title);
			updateMetaTag('twitter:description', meta.description);
			
			if (meta.image) {
				updateMetaTag('og:image', meta.image);
				updateMetaTag('twitter:image', meta.image);
			}
		}
	});
	
	function scrollToTop() {
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
	
	function handleContactSubmitted(event: CustomEvent) {
		console.log('Contact form submitted:', event.detail);
		// In a real app, you'd track this for analytics or send to backend
	}
	
	function handleActionTaken(event: CustomEvent) {
		console.log('User action taken:', event.detail);
		// Track user interactions for analytics
	}
	
	function handleViewAllSimilar(event: CustomEvent) {
		const { filters } = event.detail;
		
		// Navigate to listings page with similar property filters
		const searchParams = new URLSearchParams();
		if (filters.minPrice) searchParams.set('min_price', filters.minPrice.toString());
		if (filters.maxPrice) searchParams.set('max_price', filters.maxPrice.toString());
		if (filters.minArea) searchParams.set('min_area', filters.minArea.toString());
		if (filters.maxArea) searchParams.set('max_area', filters.maxArea.toString());
		if (filters.propertyType) searchParams.set('property_type', filters.propertyType);
		if (filters.city) searchParams.set('city', filters.city);
		
		goto(`/listings?${searchParams.toString()}`);
	}
	
	function handleSearchSimilar() {
		goto('/listings');
	}
	
	function handlePropertyViewed(event: CustomEvent) {
		console.log('Similar property viewed:', event.detail);
		// Track similar property clicks for recommendations
	}
	
	function handleImageGalleryEvent(event: CustomEvent) {
		console.log('Image gallery event:', event.detail);
		// Track image interactions
	}

	// Breadcrumb navigation
	$: breadcrumbs = [
		{ label: 'Home', href: '/' },
		{ label: 'Listings', href: '/listings' },
		{ label: listing.title, href: `/listings/${listing.listing_id}`, current: true }
	];
</script>

<svelte:window bind:scrollY />

<svelte:head>
	<title>{meta?.title || listing.title} | ProScrape</title>
	<meta name="description" content={meta?.description || `${listing.title} - Property details`} />
	<link rel="canonical" href={meta?.url || $page.url.toString()} />
</svelte:head>

<div class="min-h-screen bg-gray-50">
	<!-- Breadcrumb Navigation -->
	<div class="bg-white border-b border-gray-200">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<nav class="flex py-3" aria-label="Breadcrumb">
				<ol class="flex items-center space-x-2">
					{#each breadcrumbs as crumb, index}
						<li class="flex items-center">
							{#if index > 0}
								<svg class="w-5 h-5 text-gray-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
								</svg>
							{/if}
							{#if crumb.current}
								<span class="text-sm text-gray-500 truncate max-w-xs" title={crumb.label}>
									{crumb.label}
								</span>
							{:else}
								<a 
									href={crumb.href} 
									class="text-sm text-blue-600 hover:text-blue-700 transition-colors"
								>
									{crumb.label}
								</a>
							{/if}
						</li>
					{/each}
				</ol>
			</nav>
		</div>
	</div>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
		<div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
			<!-- Left Column: Images and Details -->
			<div class="xl:col-span-2 space-y-8">
				<!-- Image Gallery -->
				<section class="bg-white rounded-lg shadow-sm overflow-hidden">
					<ImageGallery 
						images={listing.image_urls}
						title={listing.title}
						virtualTour={listing.video_urls?.[0]}
						on:lightboxOpen={handleImageGalleryEvent}
						on:lightboxClose={handleImageGalleryEvent}
					/>
				</section>

				<!-- Property Details -->
				<section class="bg-white rounded-lg shadow-sm overflow-hidden">
					<PropertyDetails 
						{listing}
						showMap={true}
						trackViewing={true}
						on:favoriteToggled={handleActionTaken}
						on:addedToComparison={handleActionTaken}
						on:propertyShared={handleActionTaken}
						on:visitedOriginalSite={handleActionTaken}
					/>
				</section>
			</div>

			<!-- Right Column: Contact and Actions -->
			<div class="xl:col-span-1 space-y-6">
				<!-- Sticky Contact Section -->
				<div class="xl:sticky xl:top-6">
					<ContactSection 
						{listing}
						on:contactSubmitted={handleContactSubmitted}
						on:actionTaken={handleActionTaken}
					/>
				</div>
			</div>
		</div>

		<!-- Similar Properties Section -->
		{#if similarListings.length > 0}
			<section class="mt-12">
				<SimilarProperties 
					{similarListings}
					currentListing={listing}
					maxItems={4}
					on:viewAllSimilar={handleViewAllSimilar}
					on:searchSimilar={handleSearchSimilar}
					on:propertyViewed={handlePropertyViewed}
				/>
			</section>
		{/if}
		
		<!-- Recently Viewed Section -->
		<section class="mt-12">
			<RecentlyViewed 
				maxItems={4}
				title="Recently Viewed Properties"
				compact={false}
				showClearButton={false}
				on:propertyViewed={handlePropertyViewed}
				on:viewAllHistory={() => goto('/engagement?view=history')}
			/>
		</section>
	</main>

	<!-- Back to Top Button -->
	{#if showScrollTop}
		<button
			on:click={scrollToTop}
			class="fixed bottom-6 right-6 z-40 bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 transform hover:scale-110"
			aria-label="Scroll to top"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
			</svg>
		</button>
	{/if}

	<!-- Loading Overlay -->
	{#if isLoading}
		<div class="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center">
			<div class="bg-white rounded-lg p-6 flex items-center gap-3">
				<svg class="w-6 h-6 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<span class="text-gray-700 font-medium">Loading...</span>
			</div>
		</div>
	{/if}
</div>

<style>
	/* Ensure smooth scrolling behavior */
	html {
		scroll-behavior: smooth;
	}

	/* Custom scrollbar for webkit browsers */
	::-webkit-scrollbar {
		width: 8px;
	}

	::-webkit-scrollbar-track {
		background: #f1f1f1;
	}

	::-webkit-scrollbar-thumb {
		background: #c1c1c1;
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: #a8a8a8;
	}

	/* Focus styles for accessibility */
	:global(:focus-visible) {
		outline: 2px solid #3b82f6 !important;
		outline-offset: 2px !important;
	}

	/* Responsive image handling */
	:global(img) {
		max-width: 100%;
		height: auto;
	}

	/* Print styles */
	@media print {
		.fixed {
			display: none !important;
		}
		
		.bg-gray-50 {
			background-color: white !important;
		}
		
		.shadow-sm, .shadow-lg {
			box-shadow: none !important;
		}
	}

	/* High contrast mode support */
	@media (prefers-contrast: high) {
		.bg-gray-50 {
			background-color: white;
		}
		
		.border-gray-200 {
			border-color: #6b7280;
		}
	}

	/* Reduced motion support */
	@media (prefers-reduced-motion: reduce) {
		* {
			animation-duration: 0.01ms !important;
			animation-iteration-count: 1 !important;
			transition-duration: 0.01ms !important;
		}
		
		html {
			scroll-behavior: auto;
		}
	}

	/* Dark mode support (if needed) */
	@media (prefers-color-scheme: dark) {
		/* Add dark mode styles if implementing dark theme */
	}
</style>