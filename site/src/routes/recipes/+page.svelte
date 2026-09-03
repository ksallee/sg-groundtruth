<script>
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
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

<div class="col page">
	<header>
		<Breadcrumb trail={[{ label: 'Recipes' }]} />
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
