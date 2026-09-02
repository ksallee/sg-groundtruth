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
			Findings are chronological and question-shaped, and some correct an earlier one. The
			<a href="/reference">reference</a> is elsewhere: field types, entity types and filters are
			complete and addressed by name.
		</p>
		<p class="scope">
			Only findings marked <code>scope: api</code> are published here. A finding that measures one
			site, or one project inside it, stays in the repository and is excluded from this build.
			<a href="/how-it-works#scope">Why that distinction exists</a>.
		</p>
	</header>

	<EntryList entries={data.findings} />

	{#if data.recipes.length}
		<p class="onward">
			A finding answers a question. <a href="/recipes">A recipe</a> is a call that ran, with the
			response it returned.
		</p>
	{/if}

	<!-- Evidence, beside the entries that recorded it. Four cases rather than a
	     summary of the corpus, so they sit below the index and not above it. -->
	{#if data.examples.length}
		<section class="cited">
			<h2>{data.examples.length} behaviours the REST documentation does not describe</h2>
			<p class="lede">
				Each is a recorded probe result. The entry that measured it is linked below it.
			</p>
			<ul class="examples">
				{#each data.examples as ex (ex.slug)}
					<li>
						<article>
							<h3>{ex.claim}</h3>
							<p>{ex.body}</p>
							<pre>{ex.code}</pre>
							<p class="cite"><a href={ex.href}>{ex.cite}</a></p>
						</article>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>

<style>
	.page {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		gap: var(--space-5);
		grid-template-columns: var(--col);
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

	.cited {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-4);
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-5);
	}

	.cited h2 {
		font-size: var(--text-lg);
		max-width: var(--measure);
	}

	.examples {
		list-style: none;
		padding: 0;
		display: grid;
		gap: var(--space-4);
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 26rem), 1fr));
	}

	.examples article {
		height: 100%;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
		align-content: start;
		background: var(--ground-raised);
		border: var(--border) solid var(--rule);
		border-radius: var(--radius);
		padding: var(--space-4);
	}

	.examples h3 {
		font-size: var(--text-md);
	}

	.examples p {
		color: var(--ink-muted);
		font-size: var(--text-sm);
	}

	/* These samples are short enough to wrap rather than scroll, which keeps
	   every card the same shape. The corpus pages do the opposite: there the
	   line breaks carry meaning, so they scroll. */
	.examples pre {
		margin: 0;
		background: var(--slab);
		color: var(--slab-ink);
		border-radius: var(--radius);
		padding: var(--space-3);
		font-size: var(--text-xs);
		line-height: 1.5;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}

	.cite {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
	}
</style>
