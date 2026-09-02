<script>
	import EntryList from '$lib/components/EntryList.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>Findings: how the Flow PT REST API behaves</title>
	<meta
		name="description"
		content="The numbered corpus. One finding answers one question about the Flow Production Tracking REST API and ends in a single actionable sentence."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>Findings</h1>
		<p class="lede">
			One finding answers one question and ends in a single actionable sentence. Each names the probe
			that produced it and quotes the status code and error string verbatim.
		</p>
		<p class="lede">
			Findings are chronological and question-shaped, and some correct an earlier one. The reference
			is elsewhere: <a href="/field-types">field types</a>, <a href="/entity-types">entity types</a>,
			<a href="/filters">filters</a> and <a href="/recipes">recipes</a> are complete and addressed by
			name.
		</p>
		<p class="scope">
			Only findings marked <code>scope: api</code> are published here. A finding that measures one
			site, or one project inside it, stays in the repository and is excluded from this build.
			<a href="/use">Why that distinction exists</a>.
		</p>
	</header>

	<EntryList entries={data.findings} />

	{#if data.recipes.length}
		<p class="onward">
			A finding answers a question. <a href="/recipes">A recipe</a> is a call that ran, with the
			response it returned.
		</p>
	{/if}
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

	.onward {
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	.lede {
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	.scope {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		border-left: 3px solid var(--rule-strong);
		padding-left: var(--space-4);
	}
</style>
