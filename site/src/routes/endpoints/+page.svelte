<script>
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import EntryList from '$lib/components/EntryList.svelte';

	// ROUTE CHOICE: /endpoints, one flat segment, beside /field-types and
	// /entity-types. The fourth way in. An agent about to make a call holds the
	// call, and until these cards existed the corpus had no door on it: findings
	// were addressed by probe number, which is the order the probes ran in and
	// nothing a caller knows.
	let { data } = $props();
</script>

<svelte:head>
	<title>Endpoints: every Flow PT REST call, recorded</title>
	<meta
		name="description"
		content="One card per Flow Production Tracking REST call: what it takes, every status code it answers with, a real recorded response, and the edge cases that live on the call."
	/>
</svelte:head>

<div class="col page">
	<header>
		<Breadcrumb trail={[{ label: 'Endpoints' }]} />
		<h1>Endpoints</h1>
		<p class="lede">
			One card per call. What it takes, every status code it answers with, a real response, and the
			edge cases that live on the call rather than on a data type.
		</p>
		<p>
			The path is the canonical spelling: <code>&lt;type&gt;</code> is the plural URL segment,
			<code>&lt;Type&gt;</code>
			the schema name. Every <a href="/findings">finding</a> and <a href="/recipes">recipe</a> names
			the calls it covers in that same spelling, so each card carries the verdicts of everything that
			measured it.
		</p>
		<p class="scope">
			Grouped by the resource each one acts on, in the order a client meets them. The grouping is
			read off the path, so a card cannot fall outside it.
		</p>
		<p class="contribute">
			A card marked <span class="coverage" data-coverage="partial">partial</span> or
			<span class="coverage" data-coverage="untested">untested</span> says on its own row what was
			not reached. Every one of them today is a webhook delivery call: on the site these probes run
			against, entity events reach no hook at all, so the delivery payload,
			<code>X-SG-SIGNATURE</code> and the batch headers cannot be recorded here.
			<strong>If you run a site where webhooks deliver, those are the entries to contribute.</strong>
			A probe and the response it actually got is the whole ask.
		</p>
	</header>

	{#each data.families as fam (fam.id)}
		<section class="family">
			<h2 id={fam.id.toLowerCase()}>{fam.id}</h2>
			<EntryList entries={fam.entries} />
		</section>
	{/each}
</div>

<style>
	.family {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-4);
	}

	.family > h2 {
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-5);
	}

	.page {
		padding-block: var(--space-7) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-8);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
	}

	.contribute {
		border-left: var(--border) solid var(--rule);
		padding-left: var(--space-3);
		color: var(--ink-2);
	}

	.coverage {
		font-size: var(--text-xs);
		font-family: var(--mono);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 0.1em 0.45em;
		border-radius: 0.25em;
		border: var(--border) solid currentColor;
		color: var(--ink-3);
	}

	.lede {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}

	.scope {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}
</style>
