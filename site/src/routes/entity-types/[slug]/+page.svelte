<script>
	import EntryDetail from '$lib/components/EntryDetail.svelte';

	// An entity-type card sets its own sections (Type, Identity, Create, Links,
	// Status, Traps) and they are not the field-type ones. EntryDetail renders
	// whatever the markdown holds and assumes no section, so the two share it.
	let { data } = $props();
</script>

<svelte:head>
	<title>{data.entry.fullName}: Flow PT entity type reference</title>
	<meta name="description" content={data.entry.verdict} />
</svelte:head>

<EntryDetail
	entry={data.entry}
	kicker="Entity type"
	backHref="/entity-types"
	backLabel="All entity types"
/>
