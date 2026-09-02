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

<div class="page">
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

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}
</style>
