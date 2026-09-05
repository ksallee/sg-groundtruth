<script>
	import EntryDetail from '$lib/components/EntryDetail.svelte';
	import ReportStatus from '$lib/components/ReportStatus.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.entry.heading}: a Flow PT REST behaviour that should change</title>
	<meta name="description" content={data.entry.verdict} />
</svelte:head>

<EntryDetail entry={data.entry} section={{ label: 'Reports', href: '/reports' }}>
	<ReportStatus entry={data.entry} />
</EntryDetail>
