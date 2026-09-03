<script>
	import EntryList from '$lib/components/EntryList.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>Entity types: Flow PT schema names, create contracts and links</title>
	<meta
		name="description"
		content="One reference card per Flow Production Tracking entity type: the schema name and REST slug, the identity field, what a create requires, every link field and its valid types, the status field, and the traps."
	/>
</svelte:head>

<div class="col page">
	<header>
		<h1>Entity types</h1>
		<p class="lede">
			One card per entity type. Each gives the schema name and the REST slug, the field that
			identifies a row, what a create is refused without, every link field with the types it accepts,
			the status field, and the traps.
		</p>
		<p class="note">
			The card is named for the schema name, so <code>/entity-types/Version</code> is the same string
			the API answers to.
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

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}
</style>
