<script>
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
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

<div class="col page">
	<header>
		<Breadcrumb trail={[{ label: 'Findings' }]} />
		<h1>Findings</h1>
		<p class="lede">
			One finding answers one question and ends in a single actionable sentence. Each names the probe
			that produced it and quotes the status code and error string verbatim.
		</p>
		<p>
			Findings are chronological and question-shaped, and some correct an earlier one. The
			<a href="/field-types">field types</a>, <a href="/entity-types">entity types</a> and
			<a href="/filters">filters</a> are the other half: complete, and addressed by name.
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
			<header>
				<h2>{data.examples.length} behaviours the REST documentation does not describe</h2>
				<p class="lede">
					Each is a recorded probe result. The entry that measured it is linked below it.
				</p>
			</header>
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
		padding-block: var(--space-7) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
	}

	.lede {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}

	.scope,
	.onward {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	.cited {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
		margin-top: var(--space-6);
		padding-top: var(--space-8);
		border-top: var(--border) solid var(--rule);
	}

	.examples {
		list-style: none;
		padding: 0;
	}

	.examples li + li {
		margin-top: var(--space-6);
		padding-top: var(--space-6);
		border-top: var(--border) solid var(--rule);
	}

	.examples article {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
	}

	/* These samples are short enough to wrap rather than scroll. The corpus
	   pages do the opposite: there the line breaks carry meaning, so they
	   scroll. */
	.examples pre {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		margin-top: var(--space-1);
	}

	.cite {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
	}

	.cite a {
		color: var(--ink-muted);
	}

	.cite a:hover {
		color: var(--ink);
	}
</style>
