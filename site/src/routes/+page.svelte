<script>
	import Section from '$lib/components/Section.svelte';
	import { REPO } from '$lib/site.js';

	let { data } = $props();

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
2. Python 3.11 with requests: python3.11 -m venv .venv && source .venv/bin/activate && pip install requests
3. cp .env.local.example .env.local, then ask me for the values and fill in:
     FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
     FPT_PROBE_SAMPLE_PROJECTS   projects you may read, names or ids, most interesting first
     FPT_PROBE_SANDBOX_PROJECT   the only project you may write into
   .env.local is gitignored. Never print the key.
4. Run the read-only probes in probes/ against my site and read what they print,
   starting with python probes/001_auth.py and python probes/002_schema.py.
   A probe is read-only unless given --write. Do not pass --write.
5. Ask the schema what my site calls things, one type at a time:
     PYTHONPATH=src python -m sg_groundtruth.schema entities --custom
     PYTHONPATH=src python -m sg_groundtruth.schema --project N statuses Version
6. Record what you measured as markdown under corpus.local/, following the contract in
   site/README.md: scope: site files in corpus.local/site/, and scope: project files,
   each with a project: key, in corpus.local/projects/<id>/. corpus.local/ is gitignored
   and is never committed.
7. Build the docs: cd site && npm install && npm run dev, then open http://localhost:5173.`;

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
			count: `${data.counts.fieldTypes} data types, ${data.counts.entityTypes} entity types`,
			note: 'Field types, entity types and filters. Complete, and addressed by name.'
		},
		{
			href: '/recipes',
			title: 'Recipes',
			count: `${data.counts.recipes} ${data.counts.recipes === 1 ? 'recipe' : 'recipes'}`,
			note: 'A task, the calls that perform it, the response each returned, and the errors hit on the way.'
		},
		{
			href: '/findings',
			title: 'Findings',
			count: `${data.counts.findings} published`,
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

<!-- Five flat facts, one line each. The privacy one leads, because it is the
     fact a reader most needs and it is stated nowhere else. -->
<Section label="What it is" title="One corpus ships, one is written on your machine.">
	<ul class="facts">
		<li>
			<h3>Two corpora</h3>
			<p>
				One describes the Flow Production Tracking REST API and ships with the repository. One
				describes your site and is written on your machine.
			</p>
		</li>
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
			<h3>Every claim re-runs</h3>
			<p>
				Each entry names the probe that produced it. Run that probe against your own site and
				compare.
			</p>
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

<Section
	label="Enabling it for your site"
	title="The same documentation on localhost, with your own data in it."
	lede="Hand this to an LLM agent with a terminal. It clones the repository, runs the read-only probes against your Flow PT site, and builds this site locally with what it measured in it."
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
	.hero {
		padding-block: var(--space-8) var(--space-7);
	}

	.hero .inner {
		max-width: var(--wide);
		margin-inline: auto;
		padding-inline: var(--gutter);
		display: grid;
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
		gap: var(--space-2);
		align-content: start;
		border-top: 2px solid var(--rule-strong);
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
