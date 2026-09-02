<script>
	import EntryList from '$lib/components/EntryList.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>Field types: {data.counts.fieldTypes} Flow PT data types, read, write, clear and filter</title>
	<meta
		name="description"
		content="One reference card per Flow Production Tracking data_type: the read shape, every value accepted on write, every value that clears it, the full operator list, and the traps."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>Field types</h1>
		<p class="lede">
			One card per <code>data_type</code>, {data.counts.fieldTypes} in all. Each was probed on a real
			field of that type: how it reads, every value accepted on write, every value that clears it, the
			complete operator list the API returns when sent a bogus one, and the traps.
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
		gap: var(--space-5);
	}

	header {
		display: grid;
		gap: var(--space-3);
		max-width: var(--measure);
	}

	h1 {
		font-size: var(--text-xl);
	}

	.lede {
		color: var(--ink-muted);
	}
</style>
