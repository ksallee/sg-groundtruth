<script>
	import { page } from '$app/state';
	import ScopeMark from './ScopeMark.svelte';
	import { reading, ALL } from '$lib/reading.svelte.js';

	// Says what the marks on this page mean, once, where the distinction first
	// appears. Rendered only above the API level: at `api` every mark would say
	// the same thing, so nothing is marked and nothing has to be explained.
	//
	// What the overlay holds comes from the layout load, which every page
	// already carries, so no route passes it down.
	const hasSite = $derived(page.data.hasSite ?? false);
	const projects = $derived(page.data.projects ?? []);

	// The projects a reader chose: one of them, or every one at once.
	const named = $derived(
		reading.level !== 'project'
			? []
			: reading.project === ALL
				? projects
				: projects.filter((p) => p.id === reading.project)
	);
</script>

{#if reading.level !== 'api'}
	<dl class="legend">
		<div>
			<dt><ScopeMark level="api" /></dt>
			<dd>True of any Flow Production Tracking site. This is the published corpus.</dd>
		</div>

		{#if hasSite}
			<div>
				<dt><ScopeMark level="site" /></dt>
				<dd>Measured on your Flow PT site. Another site is configured differently.</dd>
			</div>
		{/if}

		{#each named as p (p.id)}
			<div>
				<dt><ScopeMark level="project" project={p.label} /></dt>
				<dd>Measured on that project. Another project on the same site can differ.</dd>
			</div>
		{/each}
	</dl>
{/if}

<style>
	/* One kind per line, the mark first, at the size it appears at below. */
	.legend {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
		border-block: var(--border) solid var(--rule);
		padding-block: var(--space-3);
	}

	.legend > div {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-1) var(--space-3);
	}

	dt {
		display: flex;
		flex: 0 0 auto;
	}

	dd {
		margin: 0;
		flex: 1 1 16rem;
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}
</style>
