<script>
	import { NAME } from '$lib/site.js';

	// The bar a phone gets: the name, which is the way home, and the button that
	// opens the sidebar as a drawer. On a desktop the sidebar is always in view
	// and this bar is not drawn.
	let { onmenu } = $props();
</script>

<header class="bar">
	<button type="button" class="menu" onclick={onmenu} aria-label="Open menu">
		<svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true">
			<path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.5" />
		</svg>
	</button>
	<a class="mark" href="/">{NAME}</a>
</header>

<style>
	.bar {
		display: none;
	}

	@media (max-width: 63.99rem) {
		.bar {
			position: sticky;
			top: 0;
			z-index: 10;
			display: flex;
			align-items: center;
			gap: var(--space-2);
			min-height: 3.5rem;
			padding-inline: var(--gutter);
			background: var(--ground);
			border-bottom: var(--border) solid var(--rule);
			font-size: var(--text-sm);
		}
	}

	.menu {
		border: 0;
		background: none;
		color: var(--ink);
		padding: var(--space-2);
		margin-left: calc(-1 * var(--space-2));
		border-radius: 6px;
		display: grid;
		place-items: center;
	}

	.menu:hover {
		background: var(--ground-sunken);
	}

	.mark {
		font-weight: var(--weight-bold);
		color: var(--ink);
		text-decoration: none;
	}
</style>
