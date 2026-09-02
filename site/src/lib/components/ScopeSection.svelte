<script>
	import ScopeMark from './ScopeMark.svelte';
	import { OVERLAY_DIR } from '$lib/site.js';

	// One section of an entry page, marked with where it was read from. Every
	// section of every entry page is one of these once the reading level is
	// above `api`, so a reader never has to work out which kind they are looking
	// at from the content.
	//
	// The API section sits flush on the page. A local section is inset: its own
	// ground, its own border and the level's edge texture down its left side. A
	// measurement of one site can therefore never be mistaken for API behaviour
	// with the hues removed.
	let { level = 'api', project = '', dir = '', children } = $props();

	const source = $derived(
		level === 'project'
			? `${OVERLAY_DIR}/projects/${dir}/`
			: level === 'site'
				? `${OVERLAY_DIR}/site/`
				: ''
	);
</script>

<section class="scoped" class:inset={level !== 'api'} data-scope={level}>
	<header>
		<ScopeMark {level} {project} />
		{#if source}<code>{source}</code>{/if}
	</header>
	{@render children?.()}
</section>

<style>
	.scoped {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-4);
		justify-items: start;
	}

	.inset {
		position: relative;
		background: var(--scope-quiet);
		border: var(--border) solid var(--rule);
		border-left: 0;
		border-radius: var(--radius);
		padding: var(--space-4) var(--space-5);
		padding-left: calc(var(--space-5) + var(--scope-edge-width));
	}

	/* The edge texture, not a colour: solid for the API, dashed for one site,
	   dotted for one project. It is the signal that survives greyscale. */
	.inset::before {
		content: '';
		position: absolute;
		inset-block: 0;
		left: 0;
		width: var(--scope-edge-width);
		background-image: var(--scope-edge);
		border-start-start-radius: var(--radius);
		border-end-start-radius: var(--radius);
	}

	header {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-2) var(--space-3);
	}

	code {
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}
</style>
