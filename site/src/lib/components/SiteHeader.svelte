<script>
	import { NAME } from '$lib/site.js';
	import ReadingLevel from './ReadingLevel.svelte';

	// The overlay facts come from the layout load. The reading level switch
	// exists only when a local overlay was found at build time, so a public build
	// carries no control that does nothing. The overlay has no nav entry: it is
	// depth on the four sections, not a fifth one.
	let { hasOverlay = false, hasSite = false, projects = [] } = $props();
</script>

<header>
	<div class="bar">
		<a class="mark" href="/">{NAME}</a>
		<nav aria-label="Sections">
			<a href="/reference">Reference</a>
			<a href="/recipes">Recipes</a>
			<a href="/findings">Findings</a>
			<a href="/how-it-works">How it works</a>
		</nav>
		{#if hasOverlay}
			<ReadingLevel {hasSite} {projects} />
		{/if}
	</div>
</header>

<style>
	header {
		border-bottom: var(--border) solid var(--rule);
		background: var(--ground);
		position: sticky;
		top: 0;
		z-index: 10;
	}

	.bar {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-3) var(--gutter);
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-3) var(--space-5);
	}

	.mark {
		font-family: var(--font-mono);
		font-size: var(--text-base);
		font-weight: 600;
		color: var(--ink);
		text-decoration: none;
		margin-right: auto;
	}

	nav {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-4);
		font-size: var(--text-sm);
	}

	nav a {
		color: var(--ink-muted);
		text-decoration: none;
	}

	nav a:hover {
		color: var(--ink);
		text-decoration: underline;
	}
</style>
