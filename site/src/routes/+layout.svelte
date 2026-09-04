<script>
	import '../app.css';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import SiteHeader from '$lib/components/SiteHeader.svelte';
	import SiteFooter from '$lib/components/SiteFooter.svelte';
	import { afterNavigate } from '$app/navigation';
	import { restore } from '$lib/reading.svelte.js';

	let { data, children } = $props();

	// The drawer state matters on a phone only; on a desktop the sidebar is
	// always in view and this is never read.
	let menuOpen = $state(false);

	// Browser only, so the prerendered HTML is always the API level and a build
	// with no overlay has nothing to restore.
	$effect(() => restore(data));
	afterNavigate(() => (menuOpen = false));

	// The annotation toolbar, dev server only. See src/lib/dev/annotation.js.
	$effect(() => {
		if (import.meta.env.DEV) import('$lib/dev/annotation.js').then((m) => m.mount());
	});
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (menuOpen = false)} />

<a class="skip" href="#main">Skip to content</a>
<div class="shell">
	<Sidebar
		nav={data.nav}
		projects={data.projects}
		open={menuOpen}
		onclose={() => (menuOpen = false)}
	/>
	{#if menuOpen}
		<button type="button" class="backdrop" aria-label="Close menu" onclick={() => (menuOpen = false)}
		></button>
	{/if}
	<div class="page">
		<SiteHeader onmenu={() => (menuOpen = true)} />
		<main id="main">
			{@render children?.()}
		</main>
		<SiteFooter />
	</div>
</div>

<style>
	.shell {
		min-height: 100dvh;
	}

	/* The sidebar and the page, side by side. The reading column centres in
	   what is left. */
	@media (min-width: 64rem) {
		.shell {
			display: grid;
			grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
		}
	}

	.page {
		min-width: 0;
	}

	/* The bottom edge of the main area fades the page out as it scrolls off:
	   nothing --main-fade up, page colour at the edge. Fixed, over the page
	   only, and under the section list at the right. */
	.page::after {
		content: '';
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
		height: var(--main-fade);
		background: linear-gradient(to top, var(--ground) 0, transparent 100%);
		pointer-events: none;
		z-index: 4;
	}

	@media (min-width: 64rem) {
		.page::after {
			left: var(--sidebar-width);
		}
	}

	main {
		display: block;
		padding-bottom: var(--space-9);
	}

	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 20;
		border: 0;
		padding: 0;
		background: rgb(0 0 0 / 0.4);
		cursor: default;
	}

	@media (min-width: 64rem) {
		.backdrop {
			display: none;
		}
	}

	.skip {
		position: absolute;
		left: var(--space-3);
		top: var(--space-3);
		z-index: 40;
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
