<script>
	import '../app.css';
	import SiteHeader from '$lib/components/SiteHeader.svelte';
	import SiteFooter from '$lib/components/SiteFooter.svelte';
	import { restore } from '$lib/reading.svelte.js';

	let { data, children } = $props();

	// Browser only, so the prerendered HTML is always the API level and a build
	// with no overlay has nothing to restore.
	$effect(() => restore(data));
</script>

<a class="skip" href="#main">Skip to content</a>
<SiteHeader hasOverlay={data.hasOverlay} hasSite={data.hasSite} projects={data.projects} />
<main id="main">
	{@render children?.()}
</main>
<SiteFooter />

<style>
	main {
		display: block;
		padding-bottom: var(--space-9);
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
		font-size: var(--text-sm);
		text-decoration: none;
		transform: translateY(-200%);
		transition: transform var(--duration) var(--ease-out);
	}

	.skip:focus {
		transform: none;
	}
</style>
