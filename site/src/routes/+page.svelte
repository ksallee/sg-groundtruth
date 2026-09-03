<script>
	import Section from '$lib/components/Section.svelte';
	import { REPO } from '$lib/site.js';
	import { countsAt } from '$lib/reading.svelte.js';

	let { data } = $props();

	// The counts answer at the reading level in force, so choosing Site or a
	// project grows the corpus on the front page rather than only on the pages
	// behind it. A public build has one level and one set of numbers.
	const counts = $derived(countsAt(data.counts));

	// Written from finding 027. The API is the same for every caller; what it
	// returns is filtered by permission, and every entry here was measured by a
	// script user with broad access.
	const PERMISSIONS_CAVEAT =
		'Every entry was measured by a script user with broad access. The API is the same for '
		+ 'every caller, but what it returns is filtered by permission, so a lower-permission '
		+ 'account may see fewer rows and fewer fields than an entry records.';

	// Handed to an agent verbatim, so every command in it is one the repository
	// has. The two site-scope probe slugs never appear in it: those are what the
	// deploy check greps the build for.
	const SETUP_PROMPT = `Clone ${REPO} and set it up to document my Flow Production Tracking site.

1. git clone ${REPO} && cd sg-groundtruth
2. Run /sg-groundtruth-setup and follow it. If your agent has no slash commands,
   read .claude/commands/sg-groundtruth-setup.md and follow that instead.

It checks the toolchain before it asks me for a credential, asks for the five values it
needs and says what each is for, proves them with two read-only probes, writes the docs
for my own site and projects, and serves them on localhost.

Everything is read-only. No probe writes anything without --write, and the only project
one may write into is the sandbox I name. My site's data is written to corpus.local/,
which is gitignored and is never committed or deployed.`;

	let copied = $state(false);
	let copyTimer;

	async function copyPrompt() {
		await navigator.clipboard.writeText(SETUP_PROMPT);
		copied = true;
		clearTimeout(copyTimer);
		copyTimer = setTimeout(() => (copied = false), 2000);
	}

	// The four sections, in the order a reader meets them. Counts come from the
	// corpus, so a group that grows says so without an edit here.
	const sections = $derived([
		{
			href: '/reference',
			title: 'Reference',
			count: `${counts.fieldTypes} data types, ${counts.entityTypes} entity types`,
			note: 'Field types, entity types and filters. Complete, and addressed by name.'
		},
		{
			href: '/recipes',
			title: 'Recipes',
			count: `${counts.recipes} ${counts.recipes === 1 ? 'recipe' : 'recipes'}`,
			note: 'A task, the calls that perform it, the response each returned, and the errors hit on the way.'
		},
		{
			href: '/findings',
			title: 'Findings',
			count: `${counts.findings} published`,
			note: 'One question each, chronological, with later entries correcting earlier ones.'
		},
		{
			href: '/how-it-works',
			title: 'How it works',
			count: '',
			note: 'The probes, the scope field, the local overlay, and the reading level.'
		}
	]);
</script>

<svelte:head>
	<title>SG Ground Truth: recorded behaviour of the Flow Production Tracking REST API</title>
	<meta
		name="description"
		content="Every entry is the recorded output of a probe run against a live Flow Production Tracking site: the status code, the error string, the response shape."
	/>
</svelte:head>

<section class="hero">
	<div class="inner">
		<h1>Recorded behaviour of the Flow Production Tracking REST API.</h1>
		<p class="lede">
			The REST documentation is incomplete and in places wrong. Each entry here is the output of a
			probe run against a live site, published in the words the API used. The probes are in the
			repository and run against any site.
		</p>

		<p class="actions">
			<a class="button" href="/reference">The reference</a>
			<a href={REPO}>Read it on GitHub</a>
		</p>
	</div>
</section>

<Section
	label="Start here"
	title="Setup Ground Truth on your Flow Production Tracking site."
	lede="Hand this to an agent with a terminal. It clones the repository, runs the read-only probes against your Flow PT site, and rebuilds this documentation with your own entities, fields, status vocabularies and projects in it."
>
	<figure class="prompt">
		<figcaption>
			<span>Setup prompt</span>
			<button type="button" onclick={copyPrompt}>{copied ? 'Copied' : 'Copy'}</button>
		</figcaption>
		<pre>{SETUP_PROMPT}</pre>
	</figure>

	<p class="body">
		<a href="/how-it-works#overlay">What the local corpus is</a>, which files are picked up, and
		where each one renders.
	</p>
</Section>

<!-- The argument for the thing, made with the corpus's own findings. Every row
     is cited, because the claim is that these failures are silent and a reader
     has no reason to take that on trust. -->
<Section
	label="Why it exists"
	title="The failures are silent, so an agent cannot correct them."
	lede="A 400 names the legal set and an agent recovers from it. A 200 that ignored what you sent tells it nothing. Each row is a published finding."
>
	<div class="scroll-x" tabindex="0">
		<table class="traps">
			<thead>
				<tr><th>you do this</th><th>you get</th><th>what happened</th></tr>
			</thead>
			<tbody>
				<tr>
					<td>Filter on a misspelled field</td>
					<td><code>400</code></td>
					<td>Caught, and the error names the legal set. This is the good case <a href="/findings/028_loud_and_silent">028</a></td>
				</tr>
				<tr>
					<td>Sort on that same misspelled field</td>
					<td><code>200</code></td>
					<td>Ignored. Rows come back id ascending and nothing says so <a href="/findings/026_result_order">026</a></td>
				</tr>
				<tr>
					<td>Read a dotted path through a <code>multi_entity</code> field</td>
					<td><code>200</code></td>
					<td>The key is absent from <code>attributes</code>. Filtering that same path works <a href="/findings/016_dotted_multi_entity">016</a></td>
				</tr>
				<tr>
					<td>Send <code>?fields</code> on a write</td>
					<td><code>200</code></td>
					<td>Ignored. Re-read the row if you need a dotted path <a href="/findings/024_read_after_write">024</a></td>
				</tr>
				<tr>
					<td>Page until <code>links.next</code> is absent</td>
					<td>a <code>next</code>, always</td>
					<td>It is emitted forever, on zero-row pages too. Stop when <code>data</code> is empty <a href="/findings/006_pagination">006</a></td>
				</tr>
				<tr>
					<td>Create a field whose display name is taken</td>
					<td><code>201</code></td>
					<td>You got <code>&lt;name&gt;_1</code>. Read <code>/schema</code> first, never post and hope <a href="/findings/019_create_fields">019</a></td>
				</tr>
				<tr>
					<td>Create rows in a batch</td>
					<td>an id per row</td>
					<td>A batch can return an id for a row it never made <a href="/findings/028_loud_and_silent">028</a></td>
				</tr>
			</tbody>
		</table>
	</div>

</Section>

<Section
	label="What it does"
	title="Four uses."
>
	<div class="scroll-x" tabindex="0">
		<table class="traps">
			<thead>
				<tr><th>use</th><th>how</th></tr>
			</thead>
			<tbody>
				<tr>
					<td>Point an agent at it</td>
					<td>It reads recorded behaviour rather than documentation. Each entry names the probe that
						produced it, so a claim it doubts, it re-runs.</td>
				</tr>
				<tr>
					<td>Feed it code you have</td>
					<td><code>/sg-groundtruth-adopt</code> reads a codebase that calls this API and turns each
						distinct call into a recipe, each retry loop and swallowed error into a probe.</td>
				</tr>
				<tr>
					<td>Answer a new question</td>
					<td><code>/probe</code> asks it against your own site and records what came back.</td>
				</tr>
				<tr>
					<td>Cover your own site</td>
					<td>Your custom entities, field names, status vocabularies and projects, on these same
						pages.</td>
				</tr>
			</tbody>
		</table>
	</div>
</Section>

<!-- Five flat facts, one line each. The privacy one leads, because it is the
     fact a reader most needs and it is stated nowhere else. -->
<Section label="What it is" title="Three things worth knowing before you run it.">
	<ul class="facts">
		<li>
			<h3>Your site's data never leaves it</h3>
			<p>
				The files describing your site are written to <code>corpus.local/</code>, which is gitignored
				and never deployed. Nothing is sent anywhere, including to whoever maintains this.
			</p>
		</li>
		<li>
			<h3>One reading level, set once</h3>
			<p>The API, your site, or one project in it. Every page answers at that level.</p>
		</li>
		<li>
			<h3>Read-only by default</h3>
			<p>
				A probe changes nothing without <code>--write</code>, and deletes anything it creates before
				it exits.
			</p>
		</li>
	</ul>

	{#if PERMISSIONS_CAVEAT}
		<p class="body">{PERMISSIONS_CAVEAT}</p>
	{/if}
</Section>

<Section label="The site" title="Four sections.">
	<ul class="sections">
		{#each sections as item (item.href)}
			<li>
				<h3><a href={item.href}>{item.title}</a></h3>
				{#if item.count}
					<p class="count">{item.count}</p>
				{/if}
				<p>{item.note}</p>
			</li>
		{/each}
	</ul>
</Section>

<style>
	/* The one table on this page. Reads the same density tokens as every other
	   table on the site, so it cannot drift from Prose or from /filters. */
	.traps {
		border-collapse: collapse;
		width: max-content;
		min-width: 100%;
		font-size: var(--text-sm);
	}

	.traps th,
	.traps td {
		text-align: left;
		vertical-align: top;
		padding: var(--cell-y) var(--cell-x);
		line-height: var(--leading-tabular);
		border-bottom: var(--border) solid var(--rule);
	}

	.traps thead th {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-muted);
		border-bottom-color: var(--rule-strong);
		white-space: nowrap;
	}

	.traps tbody tr:last-child td {
		border-bottom: 0;
	}

	.hero {
		padding-block: var(--space-8) var(--space-7);
	}

	.hero .inner {
		max-width: var(--wide);
		margin-inline: auto;
		padding-inline: var(--gutter);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-5);
	}

	h1 {
		font-size: var(--text-display);
		max-width: 20ch;
		letter-spacing: -0.02em;
	}

	.lede {
		font-size: var(--text-md);
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-4);
	}

	.button {
		display: inline-block;
		background: var(--ink);
		color: var(--ground);
		text-decoration: none;
		border-radius: var(--radius);
		padding: var(--space-2) var(--space-4);
		font-weight: 600;
	}

	.button:hover {
		background: var(--accent);
	}

	.body {
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	/* Things of equal weight, so columns of equal width rather than a list that
	   implies an order. */
	.sections,
	.facts {
		list-style: none;
		padding: 0;
		display: grid;
		gap: var(--space-5);
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
	}

	.sections li,
	.facts li {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
		align-content: start;
		border-top: var(--border-bar) solid var(--rule-strong);
		padding-top: var(--space-3);
	}

	.sections h3,
	.facts h3 {
		font-size: var(--text-md);
	}

	.sections p,
	.facts p {
		color: var(--ink-muted);
		font-size: var(--text-sm);
	}

	.sections {
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr));
	}

	/* Five short facts, so a narrower column than the bands above. */
	.facts {
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr));
	}

	.sections .count {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
	}

	/* The prompt is meant to be selected whole, so it scrolls inside its own box
	   rather than wrapping: a wrapped command line is a command that fails when
	   it is pasted back. */
	.prompt {
		margin: 0;
		max-width: var(--measure-wide);
		border: var(--border) solid var(--rule);
		border-radius: var(--radius);
		overflow: hidden;
	}

	.prompt figcaption {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-2) var(--space-3);
		background: var(--ground-raised);
		border-bottom: var(--border) solid var(--rule);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-muted);
	}

	.prompt button {
		font: inherit;
		letter-spacing: inherit;
		text-transform: inherit;
		color: var(--ink);
		background: var(--ground);
		border: var(--border) solid var(--rule-strong);
		border-radius: var(--radius-sm);
		padding: var(--space-1) var(--space-3);
		cursor: pointer;
	}

	.prompt button:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.prompt pre {
		margin: 0;
		background: var(--slab);
		color: var(--slab-ink);
		padding: var(--space-4);
		font-size: var(--text-sm);
		line-height: 1.6;
		overflow-x: auto;
	}
</style>
