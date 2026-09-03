<script>
	import { REPO } from '$lib/site.js';
	import { countsAt } from '$lib/reading.svelte.js';

	let { data } = $props();

	const counts = $derived(countsAt(data.counts));

	// Third-party integrations. Rendered only when this array has entries; empty
	// is the shipped state. Fill it from site/RESEARCH-mcp.md when that research
	// lands: one object per project, { name, href, note }. Nothing goes in here
	// that is not a project someone can open.
	// Verified against each repository's default-branch HEAD; see site/RESEARCH-mcp.md
	// for commit anchors. Say what this corpus adds, never what another project
	// gets wrong: the specifics belong in an issue on their tracker, not here.
	//
	// On this page rather than the landing page: an MCP server is a question a
	// reader already has, not one they arrive with.
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
	<title>How it works: what the corpus holds and how to use it</title>
	<meta
		name="description"
		content="What the corpus holds, how to point an agent at it, and how to put your own Flow PT site in it. One question per probe, and every claim re-runs."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>How it works</h1>
		<p class="lede">
			Every entry here is the recorded output of one script asking a live Flow Production Tracking
			site one question. Nothing is written from the documentation, and every claim re-runs.
		</p>
	</header>

	<section>
		<h2>What you get</h2>
		<div class="scroll-x" tabindex="0">
			<table>
				<thead>
					<tr><th>on the site</th><th>answers</th><th>holds</th></tr>
				</thead>
				<tbody>
					<tr>
						<td><a href="/field-types">Field types</a></td>
						<td>What does this data type read, write and clear as, and what can I filter it with</td>
						<td>{counts.fieldTypes} types, each with an operator vocabulary and a value matrix</td>
					</tr>
					<tr>
						<td><a href="/entity-types">Entity types</a></td>
						<td>What is required to create one, what does it link to, how is it identified</td>
						<td>{counts.entityTypes} types</td>
					</tr>
					<tr>
						<td><a href="/filters">Filters</a></td>
						<td>Which relations does this type accept, and what value does each one take</td>
						<td>Generated from the field-type cards, so it cannot drift from them</td>
					</tr>
					<tr>
						<td><a href="/recipes">Recipes</a></td>
						<td>How do I do this, and what does it return</td>
						<td>{counts.recipes} tasks, each with the real response and the errors hit on the way</td>
					</tr>
					<tr>
						<td><a href="/findings">Findings</a></td>
						<td>What does it actually do here, where the docs are silent or wrong</td>
						<td>{counts.findings} questions, chronological, later entries correcting earlier ones</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<section id="use">
		<h2>Use it</h2>

		<h3>Point an agent at the index</h3>
		<p>
			<code>corpus/INDEX.md</code> is generated and small enough to load whole: every entry's name,
			its one-line verdict, its tags. An agent that reads the whole corpus to answer one question
			spends its context on the first call and is useless for the rest of the session.
		</p>
		<pre>Read corpus/INDEX.md first.
Open corpus/findings/&lt;entry&gt;.md only when the one-liner falls short.</pre>

		<h3>Put your own site in it</h3>
		<p>
			One command. It checks the toolchain before asking for a credential, proves the credential with
			two read-only probes, then writes documentation covering your custom entities, your field
			names, your status vocabularies and your projects.
		</p>
		<pre>git clone {REPO} &amp;&amp; cd sg-groundtruth
/sg-groundtruth-setup</pre>
		<p class="note">
			Read-only throughout. No probe writes without <code>--write</code>, and the only project one may
			write into is the sandbox you name. What it measures is written to
			<code>{data.overlayDir}/</code>, which is gitignored and never leaves your machine.
		</p>

		<h3>Grow it as you build</h3>
		<div class="scroll-x" tabindex="0">
			<table>
				<thead>
					<tr><th>command</th><th>when</th></tr>
				</thead>
				<tbody>
					<tr>
						<td><code>/probe &lt;question&gt;</code></td>
						<td>The docs are silent or wrong and you need to know. One question per probe, answered
							against your own site, and the answer is in the corpus for every agent after you.</td>
					</tr>
					<tr>
						<td><code>/recipe &lt;task&gt;</code></td>
						<td>You made a call work and want the call, its real response and the errors you hit
							recorded.</td>
					</tr>
					<tr>
						<td><code>/sg-groundtruth-adopt &lt;path&gt;</code></td>
						<td>You already have code calling this API. It turns each distinct call into a recipe,
							and each retry loop, sleep and swallowed error into a probe.</td>
					</tr>
					<tr>
						<td><code>/inspect-site [project]</code></td>
						<td>You are wiring something to one project and want a profile with the evidence beside
							it rather than a guess.</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<section>
		<h2>How an entry is made</h2>
		<p>
			A probe asks one question, prints what the API answered, and leaves no trace: it deletes
			anything it created before it exits. It never writes the corpus. An agent reads the output,
			judges what is identifying, and writes the entry by hand.
		</p>
		<pre>python probes/017_filter_operators.py</pre>
		<p>
			Every entry names the probe that produced it, so a claim you doubt, you re-run. If your site
			answers differently, either the finding is wrong or your site is configured differently. Both
			are worth knowing, and the probe output says which.
		</p>
	</section>

	<section id="scope">
		<h2>The three levels</h2>
		<p>
			Every file declares a <code>scope</code>, and the switch in the header sets which levels a page
			answers at. Each level adds to the one before it; nothing is removed as it rises.
		</p>
		<div class="scroll-x" tabindex="0">
			<table>
				<thead>
					<tr><th>level</th><th>true of</th><th>public</th></tr>
				</thead>
				<tbody>
					<tr>
						<td><code>api</code></td>
						<td>Any Flow PT site: status codes, error strings, value shapes, operator vocabularies</td>
						<td>Yes. The default, and the only level a public build has</td>
					</tr>
					<tr>
						<td><code>site</code></td>
						<td>One site: which custom entities are enabled, which fields exist,
							<code>valid_values</code>, <code>/preferences</code></td>
						<td>No</td>
					</tr>
					<tr>
						<td><code>project</code></td>
						<td>One project inside it: <code>hidden_values</code>, page columns, fill rates</td>
						<td>No</td>
					</tr>
				</tbody>
			</table>
		</div>
		<p>
			Probe 009 is why the last two are not one level. <code>valid_values</code> is byte-identical at
			every scope and only <code>hidden_values</code> varies by project, so "which statuses can I use"
			has no site-level answer.
		</p>
		<p>
			Above <code>api</code>, every row and section is marked with the level it holds: a word, an edge
			texture and a hue. The texture is what survives greyscale, so a measurement of one site is never
			read as API behaviour. With no overlay nothing is marked and the switch is not drawn.
		</p>
	</section>

	<section id="overlay">
		<h2>Your own site, on these same pages</h2>
		<p>
			What <code>/sg-groundtruth-setup</code> builds renders here, in marked sections on the pages that
			already cover the same subject. It adds no navigation entry: it is depth on the four sections
			that are already there, and it is never committed, so it cannot reach a deployment.
		</p>
		<p>Drop a markdown file in the matching directory. Nothing has to be registered.</p>
		<pre>{data.overlayDir}/site/findings/&lt;nnn&gt;_&lt;slug&gt;.md               one Flow PT site
{data.overlayDir}/site/findings/field_types/&lt;type&gt;.md
{data.overlayDir}/site/findings/entity_types/&lt;Type&gt;.md
{data.overlayDir}/site/recipes/&lt;nnn&gt;_&lt;slug&gt;.md
{data.overlayDir}/projects/&lt;id&gt;/findings/&lt;nnn&gt;_&lt;slug&gt;.md       one project inside it
{data.overlayDir}/projects/&lt;id&gt;/findings/field_types/&lt;type&gt;.md
{data.overlayDir}/projects/&lt;id&gt;/findings/entity_types/&lt;Type&gt;.md
{data.overlayDir}/projects/&lt;id&gt;/recipes/&lt;nnn&gt;_&lt;slug&gt;.md</pre>
		<p>
			Frontmatter is the shape the shipped corpus uses, and the <code>scope</code> has to match the
			directory, so a local measurement can never be published as a general fact. A
			<code>scope: project</code> file also names its project. The full contract, every field and what
			happens to a file that gets one wrong, is in
			<a href="{REPO}/blob/main/site/README.md">site/README.md</a>.
		</p>
	</section>

	<!-- Structure only: the copy is a content edit that fills `integrations` in
	     the script above, from site/RESEARCH-mcp.md. Renders nothing when the
	     list is empty. -->
	{#if integrations.length}
		<section id="mcp">
			<h2>Using this alongside an MCP server</h2>
			<p>
				Each of these is MIT licensed and maintained. The corpus is markdown, so an agent can read it
				alongside any of them with no change to either project.
			</p>
			<ul class="integrations">
				{#each integrations as it (it.href)}
					<li>
						<h3><a href={it.href}>{it.name}</a></h3>
						<p>{it.note}</p>
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

	section {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-4);
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-5);
	}

	h2 {
		font-size: var(--text-lg);
		max-width: var(--measure);
	}

	h3 {
		font-size: var(--text-md);
		max-width: var(--measure);
		margin-top: var(--space-2);
	}

	p {
		max-width: var(--measure);
		color: var(--ink-muted);
	}

	.lede {
		font-size: var(--text-md);
	}

	pre {
		margin: 0;
		background: var(--slab);
		color: var(--slab-ink);
		border-radius: var(--radius);
		padding: var(--space-4);
		font-size: var(--text-sm);
		line-height: 1.5;
		overflow-x: auto;
	}

	table {
		border-collapse: collapse;
		font-size: var(--text-sm);
		width: max-content;
		min-width: 100%;
	}

	th,
	td {
		text-align: left;
		vertical-align: top;
		padding: var(--cell-y) var(--cell-x);
		line-height: var(--leading-tabular);
		border-bottom: var(--border) solid var(--rule);
		max-width: 34ch;
	}

	th {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-muted);
		border-bottom-color: var(--rule-strong);
		white-space: nowrap;
	}

	.note {
		font-size: var(--text-sm);
		border-left: var(--scope-edge-width) solid var(--rule-strong);
		padding-left: var(--space-4);
	}

	.integrations {
		list-style: none;
		padding: 0;
		display: grid;
		gap: var(--space-5);
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
	}

	.integrations li {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
		align-content: start;
		border-top: var(--border-bar) solid var(--rule-strong);
		padding-top: var(--space-3);
	}

	.integrations h3 {
		margin-top: 0;
	}

	.integrations p {
		font-size: var(--text-sm);
	}
</style>
