<script>
	import EntryDetail from '$lib/components/EntryDetail.svelte';
	import StatusTable from '$lib/components/StatusTable.svelte';
	import icons from '$lib/content/status-icons.json';

	let { data } = $props();

	// 009 is the subtraction itself: valid_values minus hidden_values, per entity type, for one
	// project. The markdown states it as a table of codes, which is what an agent reading the file
	// gets. On the site the same set is drawn the way it is drawn on /reference and on an entity
	// type, so a reader never meets a status as a bare code in one place and a badge in another.
	const sets = $derived(
		data.entry.slug === '009_status_lists'
			? Object.entries(icons.entityTypes ?? {})
					.filter(([, v]) => v.usable?.length)
					.sort(([a], [b]) => a.localeCompare(b))
			: []
	);
</script>

<svelte:head>
	<title>{data.entry.heading}: Flow PT REST finding</title>
	<meta name="description" content={data.entry.verdict} />
</svelte:head>

<EntryDetail entry={data.entry} kicker="Finding" backHref="/findings" backLabel="All findings" />

{#if sets.length}
	<section class="sets">
		<h2>The subtraction, drawn</h2>
		<p class="lede">
			The same sets the table above lists as codes. Where a type hides values, the hidden ones are
			shown struck below the usable set rather than omitted, because the API still accepts them on
			a write.
		</p>
		{#each sets as [type, v] (type)}
			<article>
				<h3>{type}</h3>
				<StatusTable
					codes={v.usable}
					hidden={v.hidden}
					caption={v.hidden.length
						? `${v.usable.length} usable — ${v.valid.length} valid minus ${v.hidden.length} hidden. Default ${v.default}.`
						: `${v.usable.length} values, none hidden. Default ${v.default}.`}
				/>
			</article>
		{/each}
	</section>
{/if}

<style>
	.sets {
		max-width: var(--measure);
		margin-inline: auto;
		padding-block: var(--space-6);
	}

	h2 {
		font-size: var(--text-lg);
		margin-block-end: var(--space-2);
	}

	.lede {
		color: var(--ink-muted);
		font-size: var(--text-sm);
		margin-block-end: var(--space-5);
	}

	article + article {
		margin-block-start: var(--space-6);
	}

	h3 {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		margin-block-end: var(--space-2);
	}
</style>
