<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import EngagementDashboard from '$lib/components/engagement/EngagementDashboard.svelte';
	
	// Get view from query params, default to overview
	let currentView: 'overview' | 'favorites' | 'comparison' | 'history' | 'alerts' = 'overview';
	
	onMount(() => {
		const view = $page.url.searchParams.get('view');
		if (view && ['overview', 'favorites', 'comparison', 'history', 'alerts'].includes(view)) {
			currentView = view as typeof currentView;
		}
	});
	
	function handleTabChanged(event: CustomEvent) {
		const { tab } = event.detail;
		currentView = tab;
		
		// Update URL without page reload
		const url = new URL($page.url);
		url.searchParams.set('view', tab);
		goto(url.toString(), { replaceState: true });
	}
	
	function handleBrowseProperties() {
		goto('/listings');
	}
	
	function handleEngagementEvent(event: CustomEvent) {
		// Handle various engagement events
		console.log('Engagement event:', event.type, event.detail);
	}
</script>

<svelte:head>
	<title>Engagement Dashboard | ProScrape</title>
	<meta name="description" content="Manage your saved properties, comparison lists, viewing history, and property alerts on ProScrape." />
</svelte:head>

<div class="min-h-screen bg-gray-50">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<EngagementDashboard 
			view={currentView}
			showQuickActions={true}
			on:tabChanged={handleTabChanged}
			on:browseProperties={handleBrowseProperties}
			on:favoriteAction={handleEngagementEvent}
			on:comparisonAction={handleEngagementEvent}
			on:historyAction={handleEngagementEvent}
			on:alertAction={handleEngagementEvent}
			on:dataExported={handleEngagementEvent}
			on:dataCleared={handleEngagementEvent}
			on:exportError={handleEngagementEvent}
		/>
	</div>
</div>