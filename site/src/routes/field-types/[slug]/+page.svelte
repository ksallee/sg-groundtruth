<script>
	import EntryDetail from '$lib/components/EntryDetail.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.entry.heading}: Flow PT field type reference</title>
	<meta name="description" content={data.entry.verdict} />
</svelte:head>

<EntryDetail
	entry={data.entry}
	kicker="Field type"
	backHref="/field-types"
	backLabel="All field types"
/>
