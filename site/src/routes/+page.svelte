<script>
	import Section from '$lib/components/Section.svelte';
	import EntryList from '$lib/components/EntryList.svelte';
	import Prose from '$lib/components/Prose.svelte';
	import LocalBand from '$lib/components/LocalBand.svelte';
	import { REPO } from '$lib/site.js';

	let { data } = $props();

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
6. Record what you measured as scope: site markdown under corpus.local/, following the
   contract in site/README.md. corpus.local/ is gitignored and is never committed.
7. Build the docs: cd site && npm install && npm run dev, then open http://localhost:5173.`;

	let copied = $state(false);
	let copyTimer;

	async function copyPrompt() {
		await navigator.clipboard.writeText(SETUP_PROMPT);
		copied = true;
		clearTimeout(copyTimer);
		copyTimer = setTimeout(() => (copied = false), 2000);
	}

	// Third-party integrations. Rendered only when this array has entries; empty
	// is the shipped state. Fill it from site/RESEARCH-mcp.md when that research
	// lands: one object per project, { name, href, note }. Nothing goes in here
	// that is not a project someone can open.
	// Verified against each repository's default-branch HEAD; see site/RESEARCH-mcp.md
	// for commit anchors. Say what this corpus adds, never what another project
	// gets wrong: the specifics belong in an issue on their tracker, not here.
	const integrations = [
		{
			name: 'fpt-mcp',
			href: 'https://github.com/abrahamADSK/fpt-mcp',
			note: 'A Python MCP server that bundles its own REST reference to ground model output. Read alongside it, this corpus adds the operator vocabulary the API returns per data type, and the condition that ends a paged read.'
		},
		{
			name: 'ShotgunMcpGo',
			href: 'https://github.com/rfletchr/ShotgunMcpGo',
			note: 'A Go MCP server over the REST API, with per-data_type operator and value tables. The matrix here covers the same ground measured against a live site, including the color type and the read shapes for float and status_list.'
		},
		{
			name: 'shotgrid-mcp-server',
			href: 'https://github.com/loonghao/shotgrid-mcp-server',
			note: 'A Python MCP server on PyPI, wrapping shotgun_api3. Its status resource exposes a field\'s valid values; field_types/status_list records that a project\'s usable set is those minus hidden_values, which the server does not subtract for you.'
		}
	];
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
			Each entry is the output of a probe run against a live site. The probes are in the repository
			and run against any site.
		</p>

		<p class="counts">
			{data.counts.fieldTypes} data types, {data.counts.findings} findings, {data.counts.recipes}
			{data.counts.recipes === 1 ? 'recipe' : 'recipes'}.
		</p>

		<p class="actions">
			<a class="button" href="/field-types">The field-type matrix</a>
			<a href={REPO}>Read it on GitHub</a>
		</p>
	</div>
</section>

<Section
	label="What it does"
	title="Two corpora."
	lede="The first is published here. The second is generated on your own machine and stays there."
>
	<ul class="pair">
		<li>
			<h3>Verified Flow PT REST API behaviour</h3>
			<p>
				Findings, recipes and one card per <code>data_type</code>. Every entry is the recorded output
				of a probe: what the API answered, not what a guide remembers.
			</p>
		</li>
		<li>
			<h3>A description of your own site</h3>
			<p>
				Your custom entities, your status vocabularies, your fill rates. It is generated locally into
				a gitignored directory and is never published here.
			</p>
		</li>
	</ul>
</Section>

<Section
	label="What it is for"
	title="The Flow PT REST API as measured, rather than as documented."
	lede="The REST documentation is incomplete and in places wrong."
>
	<p class="body">
		Every entry here was produced by a call to a running Flow Production Tracking site. Where a
		measurement and the documentation disagree, the measurement is what gets published, in the words
		the API used.
	</p>
</Section>

<Section
	label="How it works"
	title="One question per probe."
	lede="A probe runs against a live site. Its recorded output is the reference on this page."
>
	<ol class="steps">
		<li>
			<h3>A probe asks one question</h3>
			<p>
				<code>probes/NNN_slug.py</code> calls a live site. It is read-only unless given
				<code>--write</code>, and deletes anything it creates before it exits.
			</p>
		</li>
		<li>
			<h3>The probe prints</h3>
			<p>
				It writes nothing to the corpus. Its output is the raw answer, with the site URL, the script
				name and the key removed.
			</p>
		</li>
		<li>
			<h3>The finding records it</h3>
			<p>
				The status code, the error string and the response shape, and one sentence saying what a
				caller should do. That file is what this page renders.
			</p>
		</li>
	</ol>
</Section>

<Section
	label="Enabling it for your site"
	title="The same documentation on localhost, with your own data in it."
	lede="Point a clone at your Flow PT site and rebuild. Its custom entities, status vocabularies and fill rates render alongside the shipped corpus, in a labelled band."
>
	<p class="body">
		Hand the following to an LLM agent with a terminal. It clones the repository, fills in the
		variables from <code>.env.local.example</code>, runs the read-only probes, and builds this site
		locally.
	</p>

	<figure class="prompt">
		<figcaption>
			<span>Setup prompt</span>
			<button type="button" onclick={copyPrompt}>{copied ? 'Copied' : 'Copy'}</button>
		</figcaption>
		<pre>{SETUP_PROMPT}</pre>
	</figure>

	<p class="body">
		<a href="/use#overlay">The contract the local corpus follows</a>, including which files are picked
		up and where each one renders.
	</p>
</Section>

<Section
	label="Why it is useful, in detail"
	title="{data.examples.length} behaviours the REST documentation does not describe."
	lede="Each is a recorded probe result. The entry that measured it is linked below it."
>
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
</Section>

<!-- The matrix index, then one card rendered in full. -->
<Section
	label="The field-type matrix"
	title="{data.counts.fieldTypes} data types, each with how it reads, writes, clears and filters."
	lede="One card per data_type. Each gives the schema shape, a real response, the values accepted on write, the values that clear the field, the operator list the API returns for a bogus operator, and the traps."
>
	<EntryList entries={data.fieldTypes} showTags={false} />
</Section>

{#if data.sample}
	<Section label="One card in full" title={data.sample.name} wide>
		<p class="sample-note">
			The <code>{data.sample.name}</code> card in full.
			<a href={data.sample.href}>Its page</a>, or
			<a href="/field-types">the other {data.counts.fieldTypes - 1}</a>.
		</p>
		<div class="sample">
			<p class="verdict">{data.sample.verdict}</p>
			<Prose html={data.sample.html} />
		</div>
	</Section>
{/if}

<!-- FINDINGS. The numbered corpus with its one-line verdicts, exactly as
     corpus/INDEX.md lists them. -->
<Section
	label="Findings"
	title="How the API behaves, one question at a time."
	lede="A finding answers one question and ends in one sentence. Site-scope measurements are not published here."
>
	<EntryList entries={data.findings} showTags={false} />
</Section>

{#if data.recipes.length}
	<Section
		label="Recipes"
		title="A call and the response it returned."
		lede="A recipe records an executable call, the real response, and the errors hit on the way."
	>
		<EntryList entries={data.recipes} showTags={false} />
	</Section>
{/if}

<!-- The overlay band. Absent from every public build, because corpus.local/ is
     gitignored and so never reaches the deployed repository. -->
{#if data.localOnly.length}
	<Section label="This site" title="Measured on the site this build was pointed at." wide>
		<LocalBand title="Local entries">
			<EntryList entries={data.localOnly} tone="site" showTags={false} />
		</LocalBand>
	</Section>
{/if}

<!-- Third-party integrations. Structure only: the copy is a content edit that
     fills `integrations` in the script above, from site/RESEARCH-mcp.md. -->
{#if integrations.length}
	<Section
		label="Integrations"
		title="MCP servers for Flow Production Tracking."
		lede="Each is MIT licensed and maintained. The corpus is markdown, so an agent can read it alongside any of them with no change to either project."
	>
		<ul class="pair">
			{#each integrations as it (it.href)}
				<li>
					<h3><a href={it.href}>{it.name}</a></h3>
					<p>{it.note}</p>
				</li>
			{/each}
		</ul>
	</Section>
{/if}

<Section
	label="How to use it"
	title="Using the corpus."
	lede="The corpus is markdown. Every file carries a one-line verdict in its frontmatter."
>
	<ol class="steps">
		<li>
			<h3>Give a model the index, not the corpus</h3>
			<p>
				<code>corpus/INDEX.md</code> is generated and small enough to load whole. A model reads it,
				then opens the entries it needs.
			</p>
		</li>
		<li>
			<h3>Read the scope field</h3>
			<p>
				<code>scope: api</code> is behaviour that holds anywhere, and is the only content published
				here. <code>scope: site</code> is a measurement of one site's configuration. Those do not
				transfer, so measure them again.
			</p>
		</li>
	</ol>
	<p><a href="/use">The longer version, including the local overlay</a></p>
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

	.counts {
		margin: 0;
		padding-block: var(--space-3);
		border-block: var(--border) solid var(--rule);
		width: fit-content;
		font-family: var(--font-mono);
		font-size: var(--text-sm);
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

	/* Two things of equal weight, so two columns of equal width rather than a
	   list that implies an order. */
	.pair {
		list-style: none;
		padding: 0;
		display: grid;
		gap: var(--space-5);
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
	}

	.pair li {
		display: grid;
		gap: var(--space-2);
		align-content: start;
		border-top: 2px solid var(--rule-strong);
		padding-top: var(--space-3);
	}

	.pair h3 {
		font-size: var(--text-md);
	}

	.pair p {
		color: var(--ink-muted);
		font-size: var(--text-sm);
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

	.sample-note {
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	.sample {
		background: var(--ground-raised);
		border: var(--border) solid var(--rule);
		border-radius: var(--radius);
		padding: var(--space-5);
		display: grid;
		gap: var(--space-4);
		overflow: hidden;
	}

	.sample .verdict {
		font-size: var(--text-md);
		border-left: 3px solid var(--accent);
		padding-left: var(--space-4);
		max-width: var(--measure);
	}

	.steps {
		list-style: none;
		padding: 0;
		counter-reset: step;
		display: grid;
		gap: var(--space-5);
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
	}

	.steps li {
		counter-increment: step;
		display: grid;
		gap: var(--space-2);
		align-content: start;
		border-top: 2px solid var(--rule-strong);
		padding-top: var(--space-3);
	}

	.steps li::before {
		content: counter(step);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.steps h3 {
		font-size: var(--text-md);
	}

	.steps p {
		color: var(--ink-muted);
		font-size: var(--text-sm);
	}
</style>
