<script>
	import '../app.css';
	import SiteHeader from '$lib/components/SiteHeader.svelte';
	import SiteFooter from '$lib/components/SiteFooter.svelte';

	let { data, children } = $props();
</script>

<a class="skip" href="#main">Skip to content</a>
<SiteHeader hasOverlay={data.hasOverlay} />
<main id="main">
	{@render children?.()}
</main>
<SiteFooter />

<style>
	main {
		display: block;
	}

	.skip {
		position: absolute;
		left: var(--space-3);
		top: var(--space-3);
		z-index: 20;
		background: var(--ground-raised);
		border: var(--border) solid var(--rule-strong);
		border-radius: var(--radius);
		padding: var(--space-2) var(--space-3);
		transform: translateY(-200%);
		transition: transform var(--duration);
	}

	.skip:focus {
		transform: none;
	}
</style>
