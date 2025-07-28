<script>
	import '../app.css';
	import Header from '$lib/components/layout/Header.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';
	import ToastContainer from '$lib/components/notifications/ToastContainer.svelte';
	import ConnectionStatus from '$lib/components/notifications/ConnectionStatus.svelte';
</script>

<div class="min-h-screen flex flex-col">
	<Header />
	<main class="flex-1">
		<slot />
	</main>
	<Footer />
</div>

<!-- Global Toast Notifications -->
<ToastContainer />

<!-- Global Connection Status -->
<ConnectionStatus />