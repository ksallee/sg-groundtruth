<script>
	import EntryDetail from '$lib/components/EntryDetail.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.entry.heading}: Flow PT REST recipe</title>
	<meta name="description" content={data.entry.verdict} />
</svelte:head>

<EntryDetail entry={data.entry} kicker="Recipe" backHref="/recipes" backLabel="All recipes" />
