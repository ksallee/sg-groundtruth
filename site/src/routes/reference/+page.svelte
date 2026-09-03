<script>
	// Three cards, written out rather than looped: each carries its own code
	// spans, and there are three of them. Every number is read off the corpus at
	// build time, so a group that grows says so with no edit here.
	import { countsAt } from '$lib/reading.svelte.js';
	import StatusTable from '$lib/components/StatusTable.svelte';
	import icons from '$lib/content/status-icons.json';

	let { data } = $props();

	const counts = $derived(countsAt(data.counts));

	// Every status the site defines. Unlike the three groups above this is a
	// site-level fact, so it is only drawn when the build had credentials.
	const all = $derived(Object.keys(icons.statuses ?? {}));
</script>

<svelte:head>
	<title>Reference: Flow PT field types, entity types and filters</title>
	<meta
		name="description"
		content="The three complete references: every Flow Production Tracking data type, every entity type, and the filter operators the API accepts for each."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>Reference</h1>
		<p class="lede">
			Three groups. Each covers its subject completely and is addressed by name, so a name missing
			from one is a name the corpus does not have yet.
		</p>
		<p class="note">
			<a href="/findings">Findings</a> are the other half. They are chronological and question-shaped,
			and some correct an earlier one.
		</p>
	</header>

	<ul class="groups">
		<li>
			<h2><a href="/field-types">Field types</a></h2>
			<p class="count">{counts.fieldTypes} data types</p>
			<p>One card per <code>data_type</code>, probed on a real field of that type.</p>
			<p>
				Answers what comes back on a read, every value accepted on a write, every value that clears
				the field, and the traps.
			</p>
		</li>

		<li>
			<h2><a href="/entity-types">Entity types</a></h2>
			<p class="count">{counts.entityTypes} entity types</p>
			<p>One card per entity type, named for the schema name the API answers to.</p>
			<p>
				Answers what the REST slug is, which field identifies a row, what a create is refused
				without, and every link field with the types it accepts.
			</p>
		</li>

		<li>
			<h2><a href="/filters">Filters</a></h2>
			<p class="count">{data.filters.types} data types, {data.filters.families} families</p>
			<p>One table, generated from the field-type cards, so the two cannot disagree.</p>
			<p>
				Answers which relations a filter on a given type accepts, in the words the API's own 400 uses,
				and names the {data.filters.unfilterable} types that accept none.
			</p>
		</li>
	</ul>

	{#if all.length}
		<section class="statuses">
			<h2>Statuses</h2>
			<p>
				Every status this site defines, with the label a person sees, the code the API stores and
				the colour. A status is drawn the same way here, on an entity type, and in
				<code>009_status_lists</code>.
			</p>
			<p class="note">
				The stock icons are not in the API. They are cells in the web app's own sprite, matched
				from its stylesheet at build time — see <a href="/findings">010_status_icons</a>.
			</p>
			<StatusTable codes={all} caption={`${all.length} statuses defined site-wide`} />
		</section>
	{/if}
</div>

<style>
	.page {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
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

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	.groups {
		list-style: none;
		padding: 0;
		display: grid;
		gap: var(--space-5);
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
	}

	.groups li {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
		align-content: start;
		border-top: 2px solid var(--rule-strong);
		padding-top: var(--space-3);
	}

	.groups h2 {
		font-size: var(--text-md);
	}

	.groups p {
		color: var(--ink-muted);
		font-size: var(--text-sm);
	}

	.count {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
	}
</style>
