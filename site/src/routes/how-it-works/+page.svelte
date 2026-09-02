<script>
	import { REPO } from '$lib/site.js';

	let { data } = $props();

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
	<title>How it works: probes, scope, and the local overlay</title>
	<meta
		name="description"
		content="One question per probe. Point a model at the corpus index, run the probes against your own Flow PT site, and read the scope field to tell what transfers from what you have to measure again."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>How it works</h1>
		<p class="lede">
			One question per probe. A probe is a script that asks a live Flow Production Tracking site one
			question, and what it prints is the reference.
		</p>
		<p class="lede">
			The corpus is markdown files, each with a one-line verdict in its frontmatter.
		</p>
	</header>

	<section>
		<h2>Point a model at the index, not the corpus</h2>
		<p>
			<code>corpus/INDEX.md</code> is generated and small enough to load whole. It carries every entry's
			name, its one-line verdict and its tags. A model reads the index, then opens the two or three entries
			it needs.
		</p>
		<p>
			A model that reads the whole corpus to answer one question spends its context on the first call
			and is useless for the rest of the session. The index exists to prevent that.
		</p>
		<pre>Read corpus/INDEX.md first.
Open corpus/findings/&lt;entry&gt;.md only when the one-liner falls short.</pre>
	</section>

	<section>
		<h2>Run the probes against your own site</h2>
		<p>
			Every entry names the probe that produced it. A probe asks one question, prints what the API
			answered, and leaves no trace: it is read-only unless given <code>--write</code>, and deletes
			anything it creates before it exits.
		</p>
		<pre>git clone {REPO}
cp .env.local.example .env.local   # site URL, script name, API key
python probes/017_filter_operators.py</pre>
		<p>
			If your site answers differently from what is published here, the finding is wrong or your site
			is configured differently. Both are worth knowing, and the probe output tells you which.
		</p>
	</section>

	<section id="scope">
		<h2>Read the scope field</h2>
		<p>
			Every corpus file declares a <code>scope</code> in its frontmatter. There are three levels, and
			the probes are what proved they are distinct.
		</p>
		<div class="scroll-x">
			<table>
				<thead>
					<tr>
						<th>scope</th>
						<th>means</th>
						<th>published here</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td><code>api</code></td>
						<td>Behaviour that holds on any Flow PT site: status codes, error strings, accepted
							value shapes, operator vocabularies.</td>
						<td>Yes. This is the whole public site.</td>
					</tr>
					<tr>
						<td><code>site</code></td>
						<td>True of one Flow PT site: which custom entities are enabled, which custom fields
							exist, a field's <code>valid_values</code>, what <code>/preferences</code> returns.</td>
						<td>No. It does not generalise, so it is not stated as fact on a public page.</td>
					</tr>
					<tr>
						<td><code>project</code></td>
						<td>True of one project inside one site: <code>hidden_values</code>, page settings and
							visible columns, fill rates. The file also carries a <code>project:</code> key naming
							which project it was measured on.</td>
						<td>No. Not even another project on the same site can be assumed to match.</td>
					</tr>
				</tbody>
			</table>
		</div>
		<p>
			Probe 009 is why the last two are not one level. A status field's <code>valid_values</code> is
			byte-identical at every scope, and only <code>hidden_values</code> varies by project. "Which
			statuses can I use" has no site-level answer.
		</p>
		<p>
			A reader forking this repository has to be able to tell, sentence by sentence, what transfers to
			their site and what they have to measure again. That is what the field is for. Findings marked
			<code>scope: api</code> still attribute any local number inline, beginning "On the probed site".
		</p>
	</section>

	<section id="overlay">
		<h2>Enabling it for your site</h2>
		<p>
			Point a clone at your Flow PT site and rebuild. Its custom entities, status vocabularies and
			fill rates render on the pages that already cover the same subject, in a marked section, at the
			level the header switch is set to. The <a href="/">setup prompt on the front page</a> is one way
			to get there.
		</p>
		<p>
			This site builds from three content sources, one per level. The first is
			<code>corpus/</code>, committed and public, filtered to <code>scope: api</code>. The other two
			are directories under <code>{data.overlayDir}/</code>, gitignored and generated against your own
			Flow PT site. When either is present the header gains a switch that sets which level every page
			answers at. The overlay adds no section to the navigation: it is depth on the four that are
			already there.
		</p>
		<p>
			The overlay is never committed and so never reaches a public deployment. Building it is how you
			get documentation that covers your custom entities, your status vocabularies and your fill
			rates, with examples drawn from your own data.
		</p>

		<h3>The contract</h3>
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
			Frontmatter is the same shape the shipped corpus uses. The scope has to match the directory, and
			a project file names its project. An optional <code>title</code> names the thing the way a person
			does, <code>Lenses</code> for <code>CustomEntity19</code>; the schema name stays beside it and
			stays the URL.
		</p>
		<pre>---
tags: [version, status]
scope: project
project: &lt;the project this was measured on&gt;
verdict: One line. What a reader of this site should do.
---

# &lt;heading&gt;</pre>
		<div class="scroll-x">
			<table>
				<thead>
					<tr>
						<th>file</th>
						<th>renders</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td>slug matches a shipped entry</td>
						<td>On that entry's page, in a marked section below the shipped card, and as a mark
							on that entry's row in the list.</td>
					</tr>
					<tr>
						<td>slug matches nothing shipped</td>
						<td>As a row of its own in the list the group belongs to, and a page of its own under
							it, with no API section on it.</td>
					</tr>
					<tr>
						<td><code>scope</code> does not match the directory</td>
						<td>Skipped, with a warning on the build log. An overlay file can never be published
							as a general fact.</td>
					</tr>
					<tr>
						<td><code>scope: project</code> with no <code>project:</code> key</td>
						<td>Skipped, with a warning on the build log.</td>
					</tr>
					<tr>
						<td>directory absent or empty</td>
						<td>Nothing changes. The public build is this case.</td>
					</tr>
				</tbody>
			</table>
		</div>
		<p class="note">
			The generator that populates the overlay lives in <code>probes/</code> and is separate from this
			site. <code>python probes/build_overlay.py</code> reads your site and writes every file above
			that it can measure; it is read-only and re-runnable. The site consumes the contract above and
			does not care what wrote the files.
		</p>
	</section>

	<section id="level">
		<h2>Set the reading level once</h2>
		<p>
			The switch in the header is global. It is chosen once, applied to every page, and remembered
			across navigation and reloads in <code>localStorage</code>. Each level adds to the one before
			it, so the API content is on the page whatever is selected.
		</p>
		<div class="scroll-x">
			<table>
				<thead>
					<tr>
						<th>level</th>
						<th>on the page</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td>API</td>
						<td>The shipped corpus. The default, and the only level a public build has.</td>
					</tr>
					<tr>
						<td>Site</td>
						<td>The shipped corpus, and what one Flow PT site configures.</td>
					</tr>
					<tr>
						<td>Project</td>
						<td>Both of those, and one project inside that site, or every project the overlay
							holds at once. With more than one selected, each section names the project it was
							measured on.</td>
					</tr>
				</tbody>
			</table>
		</div>
		<p>
			Every list row and every section on an entry page is marked with the kind of information it
			holds: a word, an edge texture and a hue, so a measurement of one site is never read as API
			behaviour, and the distinction survives a greyscale screen. Local sections are inset on their
			own ground; API content sits flush on the page. A legend states the marks where they first
			appear. With no overlay nothing is marked and the switch is not drawn.
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
		padding: var(--space-2) var(--space-3);
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
		border-left: 3px solid var(--rule-strong);
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
		border-top: 2px solid var(--rule-strong);
		padding-top: var(--space-3);
	}

	.integrations h3 {
		margin-top: 0;
	}

	.integrations p {
		font-size: var(--text-sm);
	}
</style>
