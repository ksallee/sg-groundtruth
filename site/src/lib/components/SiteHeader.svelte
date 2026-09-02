<script>
	import { NAME } from '$lib/site.js';

	// `hasOverlay` comes from the layout load. The /site link exists only when
	// a local overlay was found at build time, so the nav never has a dead entry.
	let { hasOverlay = false } = $props();
</script>

<header>
	<div class="bar">
		<a class="mark" href="/">{NAME}</a>
		<nav aria-label="Sections">
			<a href="/field-types">Field types</a>
			<a href="/findings">Findings</a>
			<a href="/use">How to use it</a>
			{#if hasOverlay}
				<a class="local" href="/site">This site</a>
			{/if}
		</nav>
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

	nav a.local {
		color: var(--accent-local);
	}
</style>
