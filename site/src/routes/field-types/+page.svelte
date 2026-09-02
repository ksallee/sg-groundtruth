<script>
	import EntryList from '$lib/components/EntryList.svelte';
	import { countsAt } from '$lib/reading.svelte.js';

	let { data } = $props();

	// The lede counts what is in the list, which grows with the reading level.
	// The page title stays at the API count: it is prerendered, and a browser
	// tab is not the place to state what one site configures.
	const counts = $derived(countsAt(data.counts));
</script>

<svelte:head>
	<title>Field types: {data.counts.api.fieldTypes} Flow PT data types, read, write, clear and filter</title>
	<meta
		name="description"
		content="One reference card per Flow Production Tracking data_type: the read shape, every value accepted on write, every value that clears it, the full operator list, and the traps."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>Field types</h1>
		<p class="lede">
			One card per <code>data_type</code>, {counts.fieldTypes} in all. Each was probed on a real
			field of that type: how it reads, every value accepted on write, every value that clears it, the
			complete operator list the API returns when sent a bogus one, and the traps.
		</p>
		<p class="note">
			Every card's operator list is collected into one table on
			<a href="/filters">Filters</a>.
		</p>
	</header>

	<EntryList entries={data.entries} />
</div>

<style>
	.page {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-5);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
		max-width: var(--measure);
	}

	h1 {
		font-size: var(--text-xl);
	}

	.lede {
		color: var(--ink-muted);
	}

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}
</style>
