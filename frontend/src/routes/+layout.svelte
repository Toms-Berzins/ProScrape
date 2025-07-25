<script>
	import '../app.css';
	import Header from '$lib/components/layout/Header.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';
</script>

<div class="min-h-screen flex flex-col">
	<Header />
	<main class="flex-1">
		<slot />
	</main>
	<Footer />
</div>