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

<div class="col page">
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
		padding-block: var(--space-7) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
	}

	.lede {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}
</style>
