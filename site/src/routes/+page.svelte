<script>
	import Section from '$lib/components/Section.svelte';
	import CopyButton from '$lib/components/CopyButton.svelte';
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

	// The sections, in the order a reader meets them. Counts come from the
	// corpus, so a group that grows says so without an edit here.
	const sections = $derived([
		{
			href: '/field-types',
			title: 'Field types',
			count: `${counts.fieldTypes} data types`,
			note: 'One card per data_type: what it reads, writes and clears as, and what filters it.'
		},
		{
			href: '/entity-types',
			title: 'Entity types',
			count: `${counts.entityTypes} entity types`,
			note: 'One card per schema name: identity, the create contract, every link field, the status field.'
		},
		{
			href: '/endpoints',
			title: 'Endpoints',
			count: `${counts.endpoints} calls`,
			note: 'One card per REST call: what it takes, what it answers, a real response, and the edge cases.'
		},
		{
			href: '/filters',
			title: 'Filters',
			count: '',
			note: 'Every relation each data type accepts and the value to send with it, generated from the field-type cards.'
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
			note: 'One question each, grouped by the phase of a session it bites in.'
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

<section class="col hero">
	<h1>Recorded behaviour of the Flow Production Tracking REST API.</h1>
	<p class="lede">
		The REST documentation is incomplete and in places wrong. Each entry here is the output of a
		probe run against a live site, published in the words the API used. The probes are in the
		repository and run against any site.
	</p>

	<p class="actions">
		<a class="button" href="/field-types">Start with the field types</a>
		<a class="button ghost" href={REPO}>Read it on GitHub</a>
	</p>
</section>

<Section
	label="Start here"
	title="Setup Ground Truth on your Flow Production Tracking site."
	lede="Hand this to an agent with a terminal. It clones the repository, runs the read-only probes against your Flow PT site, and rebuilds this documentation with your own entities, fields, status vocabularies and projects in it."
>
	<figure class="prompt">
		<figcaption>
			<span>Setup prompt</span>
			<CopyButton text={SETUP_PROMPT} />
		</figcaption>
		<pre>{SETUP_PROMPT}</pre>
	</figure>

	<p>
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
	<div class="scroll-x">
		<table>
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

<Section label="What it does" title="Four uses.">
	<div class="scroll-x">
		<table>
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

<!-- Three flat facts, one each. The privacy one leads, because it is the fact
     a reader most needs and it is stated nowhere else. -->
<Section label="What it is" title="Three things worth knowing before you run it.">
	<ul class="items">
		<li>
			<h3>Your site's data never leaves it</h3>
			<p>
				The files describing your site are written to <code>corpus.local/</code>, which is gitignored
				and never deployed. Nothing is sent anywhere, including to whoever maintains this.
			</p>
		</li>
		<li>
			<h3>Every level on one page</h3>
			<p>The API, your site and your projects, each section under its badge, on the pages that already
				cover the subject.</p>
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
		<p class="caveat">{PERMISSIONS_CAVEAT}</p>
	{/if}
</Section>

<Section label="The site" title="What is on it.">
	<ul class="items">
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
	.hero {
		padding-block: var(--space-8) var(--space-5);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-5);
	}

	h1 {
		font-size: var(--text-display);
		line-height: var(--leading-tight);
		letter-spacing: var(--tracking-display);
	}

	.lede {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-5);
		font-size: var(--text-sm);
		margin-top: var(--space-2);
	}

	.button {
		display: inline-flex;
		align-items: center;
		min-height: 2.5rem;
		padding: 0 var(--space-5);
		background: var(--ink);
		color: var(--ground);
		border-radius: var(--radius-pill);
		text-decoration: none;
		font-weight: var(--weight-medium);
		transition:
			background var(--duration) ease,
			transform var(--duration-press) var(--ease-out);
	}

	.button:hover {
		background: var(--ink-soft);
	}

	.button:active {
		transform: scale(0.97);
	}

	/* The same pill with nothing filled in: a hairline for the ink, drawn
	   inside so the two buttons stand the same height. */
	.ghost {
		background: none;
		color: var(--ink);
		box-shadow: inset 0 0 0 var(--border) var(--rule-strong);
	}

	.ghost:hover {
		background: var(--ground-sunken);
	}

	/* Things of equal weight, one after another. */
	.items {
		list-style: none;
		padding: 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-5);
	}

	.items li {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
	}

	.items h3 a {
		text-decoration-color: transparent;
	}

	.items h3 a:hover {
		text-decoration-color: currentColor;
	}

	.count {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.caveat {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	/* The prompt is meant to be selected whole, so it scrolls inside its own box
	   rather than wrapping: a wrapped command line is a command that fails when
	   it is pasted back. */
	.prompt {
		border: var(--border) solid var(--slab-rule);
		border-radius: var(--radius-lg);
		overflow: hidden;
	}

	/* The box's title bar: same surface as the body, a divider between them. */
	.prompt figcaption {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-2) var(--space-3) var(--space-2) var(--space-5);
		background: var(--slab);
		border-bottom: var(--border) solid var(--slab-divider);
		font-size: var(--text-xs);
		font-weight: var(--weight-medium);
		color: var(--ink-muted);
	}

	.prompt pre {
		border: 0;
		border-radius: 0;
	}
</style>
