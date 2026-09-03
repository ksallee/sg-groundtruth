<script>
	import EntryDetail from '$lib/components/EntryDetail.svelte';
	import StatusTable from '$lib/components/StatusTable.svelte';
	import icons from '$lib/content/status-icons.json';

	// An entity-type card sets its own sections (Type, Identity, Create, Links,
	// Status, Traps) and they are not the field-type ones. EntryDetail renders
	// whatever the markdown holds and assumes no section, so the two share it.
	let { data } = $props();

	// The card's own Status section is prose about how statuses behave on this
	// type. This is the set itself, drawn the same way it is drawn on /reference
	// and in 009_status_lists. Absent when the build had no site configured.
	const st = $derived(icons.entityTypes?.[data.entry.slug] ?? null);
</script>

<svelte:head>
	<title>{data.entry.heading}: Flow PT entity type reference</title>
	<meta name="description" content={data.entry.verdict} />
</svelte:head>

<EntryDetail entry={data.entry} section={{ label: 'Entity types', href: '/entity-types' }} />

{#if st}
	<section class="col statuses">
		<h2>Statuses this type can take</h2>
		<StatusTable
			codes={st.usable}
			hidden={st.hidden}
			caption={st.hidden.length
				? `${st.usable.length} usable: ${st.valid.length} valid minus ${st.hidden.length} hidden on this project. Default ${st.default}.`
				: `${st.usable.length} values. Default ${st.default}.`}
		/>
	</section>
{/if}

<style>
	.statuses {
		padding-top: var(--space-8);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-4);
	}
</style>
