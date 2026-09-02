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
		<p class="scope">
			Only findings marked <code>scope: api</code> are published here. A finding that measures one
			site's configuration stays in the repository and is excluded from this build.
			<a href="/use">Why that distinction exists</a>.
		</p>
	</header>

	<EntryList entries={data.findings} />

	{#if data.recipes.length}
		<section>
			<h2>Recipes</h2>
			<p class="lede">A verified call and its real response.</p>
			<EntryList entries={data.recipes} />
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
	}

	header {
		display: grid;
		gap: var(--space-3);
		max-width: var(--measure);
	}

	h1 {
		font-size: var(--text-xl);
	}

	h2 {
		font-size: var(--text-lg);
		margin-bottom: var(--space-2);
	}

	section {
		display: grid;
		gap: var(--space-3);
		margin-top: var(--space-5);
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
