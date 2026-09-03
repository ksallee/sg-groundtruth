<script>
	import { page } from '$app/state';
	import { NAME } from '$lib/site.js';
	import ReadingLevel from './ReadingLevel.svelte';

	// The overlay facts come from the layout load. The reading level switch
	// exists only when a local overlay was found at build time, so a public build
	// carries no control that does nothing. The overlay has no nav entry: it is
	// depth on the four sections, not a fifth one.
	let { hasOverlay = false, hasSite = false, projects = [] } = $props();

	// Reference is an index over three routes it does not own, so its entry is
	// the current one on all four.
	const links = [
		{
			href: '/reference',
			label: 'Reference',
			covers: ['/reference', '/field-types', '/entity-types', '/filters']
		},
		{ href: '/recipes', label: 'Recipes', covers: ['/recipes'] },
		{ href: '/findings', label: 'Findings', covers: ['/findings'] },
		{ href: '/how-it-works', label: 'How it works', covers: ['/how-it-works'] }
	];

	const current = (link) =>
		link.covers.some((c) => page.url.pathname === c || page.url.pathname.startsWith(c + '/'));
</script>

<header>
	<div class="col bar" class:switched={hasOverlay}>
		<a class="mark" href="/">{NAME}</a>
		<nav aria-label="Sections">
			{#each links as link (link.href)}
				<a href={link.href} aria-current={current(link) ? 'page' : undefined}>{link.label}</a>
			{/each}
		</nav>
		{#if hasOverlay}
			<ReadingLevel {hasSite} {projects} />
		{/if}
	</div>
</header>

<style>
	header {
		position: sticky;
		top: 0;
		z-index: 10;
		background: var(--ground);
		border-bottom: var(--border) solid var(--rule);
	}

	.bar {
		min-height: var(--space-8);
		padding-block: var(--space-2);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-2) var(--space-5);
		font-size: var(--text-sm);
	}

	.mark {
		font-weight: var(--weight-bold);
		color: var(--ink);
		text-decoration: none;
		margin-right: auto;
	}

	nav {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-5);
	}

	nav a {
		color: var(--ink-muted);
		text-decoration: none;
	}

	nav a:hover,
	nav a[aria-current] {
		color: var(--ink);
	}

	/* With the reading-level switch on the bar, the three do not fit one row of
	   the column, so the bar is two rows on purpose: the name and the switch,
	   then the sections. Without a switch it is one row. */
	.switched nav {
		order: 3;
		flex: 1 0 100%;
	}

	/* On a phone the bar would wrap to three or four rows and hold a fifth of
	   the screen on every scroll. The nav takes one row of its own and scrolls
	   sideways instead, and the bar stays two rows tall. */
	@media (max-width: 40rem) {
		nav {
			order: 3;
			flex: 1 0 100%;
			flex-wrap: nowrap;
			overflow-x: auto;
			scrollbar-width: none;
			gap: var(--space-5);
			padding-bottom: var(--space-1);
		}

		nav::-webkit-scrollbar {
			display: none;
		}

		nav a {
			white-space: nowrap;
		}
	}
</style>
