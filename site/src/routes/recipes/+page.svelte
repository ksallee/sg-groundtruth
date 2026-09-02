<script>
	import EntryList from '$lib/components/EntryList.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>Recipes: verified Flow PT REST calls and the responses they returned</title>
	<meta
		name="description"
		content="A recipe records an executable call against the Flow Production Tracking REST API, the response it returned, and the errors hit on the way to it."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>Recipes</h1>
		<p class="lede">
			A recipe records one call that ran, the response it returned, and the errors hit on the way to
			it. Every recipe was produced by a probe in the repository.
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
</style>
