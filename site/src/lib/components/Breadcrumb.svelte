<script>
	import { NAME } from '$lib/site.js';

	// Where the page sits. The first crumb is always home, which is the intro;
	// the last is the page itself and is not a link.
	let { trail = [] } = $props();

	const crumbs = $derived([{ label: NAME, href: '/' }, ...trail]);
</script>

<nav class="crumbs" aria-label="Breadcrumb">
	<ol>
		{#each crumbs as c, i (i)}
			<li>
				{#if i < crumbs.length - 1}
					<a href={c.href}>{c.label}</a>
					<svg class="sep" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
						<path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" fill="none" />
					</svg>
				{:else}
					<span class="here" aria-current="page">{c.label}</span>
				{/if}
			</li>
		{/each}
	</ol>
</nav>

<style>
	.crumbs {
		font-size: var(--text-menu);
		line-height: 1.6;
		color: var(--ink-muted);
	}

	ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-1) var(--space-2);
	}

	li {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
	}

	a {
		color: var(--ink-muted);
		text-decoration: none;
		transition: color var(--duration) ease;
	}

	a:hover {
		color: var(--ink);
	}

	.sep {
		flex: 0 0 auto;
		color: var(--ink-muted);
		opacity: 0.6;
	}

	.here {
		color: var(--ink);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
