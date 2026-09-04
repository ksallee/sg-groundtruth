<script>
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import { REPO } from '$lib/site.js';
	import { countsAt } from '$lib/reading.svelte.js';

	let { data } = $props();

	const counts = $derived(countsAt(data.counts));

	// Third-party integrations. Rendered only when this array has entries; empty
	// is the shipped state. Fill it from site/RESEARCH-mcp.md when that research
	// lands: one object per project, { name, href, note }. Nothing goes in here
	// that is not a project someone can open.
	// Verified against each repository's default-branch HEAD; see site/RESEARCH-mcp.md
	// for commit anchors. Say what each one is and what this corpus adds. What
	// another project gets wrong belongs in an issue on their tracker, not here.
	//
	// On this page rather than the landing page: an MCP server is a question a
	// reader already has, not one they arrive with.
	const integrations = [
		{
			name: 'fpt-mcp',
			href: 'https://github.com/abrahamADSK/fpt-mcp',
			note: 'Python. Bundles its own REST reference. This corpus adds the operator vocabulary per data type, and the condition that ends a paged read.'
		},
		{
			name: 'ShotgunMcpGo',
			href: 'https://github.com/rfletchr/ShotgunMcpGo',
			note: 'Go. Per-data_type operator and value tables. The matrix here was measured against a live site, and covers the color type and the read shapes for float and status_list.'
		},
		{
			name: 'shotgrid-mcp-server',
			href: 'https://github.com/loonghao/shotgrid-mcp-server',
			note: 'Python, on PyPI, wrapping shotgun_api3. Its status resource exposes a field\'s valid values. The usable set is those minus hidden_values, which it does not subtract for you (field_types/status_list).'
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

<div class="col page">
	<header>
		<Breadcrumb trail={[{ label: 'How it works' }]} />
		<h1>How it works</h1>
		<p class="lede">
			Every entry is what a live Flow Production Tracking site answered when a script asked it one
			question. Nothing here comes from the documentation.
		</p>
	</header>

	<section>
		<h2>What is on it</h2>
		<div class="scroll-x">
			<table>
				<thead>
					<tr><th>page</th><th>answers</th><th>holds</th></tr>
				</thead>
				<tbody>
					<tr>
						<td><a href="/entity-types">Entity types</a></td>
						<td>What is required to create one, what does it link to, how is it identified</td>
						<td>{counts.entityTypes} types</td>
					</tr>
					<tr>
						<td><a href="/field-types">Field types</a></td>
						<td>What does this data type read, write and clear as, and what can I filter it with</td>
						<td>{counts.fieldTypes} types, each with an operator vocabulary and a value matrix</td>
					</tr>
					<tr>
						<td><a href="/endpoints">Endpoints</a></td>
						<td>What does this call take, and what does it answer</td>
						<td>{counts.endpoints} calls, each with a recorded response and its status codes</td>
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
						<td>What does it do here, where the docs are silent or wrong</td>
						<td>{counts.findings} questions, grouped by the phase they bite in</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<section id="read">
		<h2>Read it</h2>
		<p>Nothing to install. Clone it and give an agent one line.</p>
		<pre>git clone {REPO}</pre>
		<pre>Read sg-groundtruth/corpus/INDEX.md first.
Open an entry only when its one-liner falls short.</pre>
		<p class="note">
			67 KB, generated. One line per entry: name, verdict, tags. The corpus behind it is much larger.
		</p>
	</section>

	<section id="serve">
		<h2>Mount it over MCP</h2>
		<p>
			The same corpus as {data.mcpTools} tools, so an agent looks up one entry instead of loading the
			index. Standard library only. Call <code>filter_operators</code> before building anything that
			filters.
		</p>
		<pre>PYTHONPATH=src python -m sg_groundtruth.mcp</pre>
		<p class="note">
			<code>PYTHONPATH</code> is not optional: the package is not installed. Registration, for Claude
			Code and any other stdio client: <a href="{REPO}/blob/main/docs/mcp.md">docs/mcp.md</a>.
		</p>
	</section>

	<section id="setup">
		<h2>Put your own site in it</h2>
		<p>
			These pages cover any Flow PT site. One command measures yours: custom entities, field names,
			status vocabularies, projects.
		</p>
		<pre>cd sg-groundtruth
claude</pre>
		<pre>/sg-groundtruth-setup</pre>
		<p class="note">The command loads with the session, so start the agent inside the clone.</p>

		<div class="scroll-x">
			<table>
				<thead>
					<tr><th>step</th><th>what happens</th></tr>
				</thead>
				<tbody>
					<tr><td>1</td><td>Asks what you want run. It measures nothing silently</td></tr>
					<tr><td>2</td><td>Checks the toolchain</td></tr>
					<tr><td>3</td><td>Asks for five values, and says what each is for</td></tr>
					<tr><td>4</td><td>Proves them with two read-only probes</td></tr>
					<tr><td>5</td><td>Writes your site's documentation to <code>{data.overlayDir}/</code></td></tr>
					<tr><td>6</td><td>Serves it on localhost, then hands you the four commands above</td></tr>
				</tbody>
			</table>
		</div>

		<div class="scroll-x">
			<table>
				<tbody>
					<tr>
						<td>Writes to your site</td>
						<td>Nothing, unless a probe is run with <code>--write</code></td>
					</tr>
					<tr>
						<td>Project it may write into</td>
						<td>The sandbox you name, and no other</td>
					</tr>
					<tr>
						<td>Where your data goes</td>
						<td><code>{data.overlayDir}/</code>, gitignored, never leaves your machine</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<section id="add">
		<h2>Add to it</h2>
		<div class="scroll-x">
			<table>
				<thead>
					<tr><th>command</th><th>what it does</th></tr>
				</thead>
				<tbody>
					<tr>
						<td><code>/probe &lt;question&gt;</code></td>
						<td>Asks one question against your own site and records what came back.</td>
					</tr>
					<tr>
						<td><code>/recipe &lt;task&gt;</code></td>
						<td>Records a call you got working, its real response, and the errors you hit.</td>
					</tr>
					<tr>
						<td><code>/sg-groundtruth-adopt &lt;path&gt;</code></td>
						<td>Reads code that already calls this API. Each distinct call becomes a recipe, and
							each retry loop, sleep and swallowed error becomes a probe.</td>
					</tr>
					<tr>
						<td><code>/inspect-site [project]</code></td>
						<td>Measures one project and proposes a profile, with the evidence beside it.</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<section>
		<h2>Probes</h2>
		<p>
			A probe asks one question, prints what the API answered, and deletes anything it created. It
			never writes the corpus: an agent reads the output and writes the entry.
		</p>
		<pre>python probes/017_filter_operators.py</pre>
		<p>
			Every entry names the probe that produced it. Run it against your own site to check.
		</p>
	</section>

	<section id="scope">
		<h2>Scopes</h2>
		<p>Every file declares a <code>scope</code>.</p>
		<div class="scroll-x">
			<table>
				<thead>
					<tr><th>scope</th><th>true of</th><th>public</th></tr>
				</thead>
				<tbody>
					<tr>
						<td><code>api</code></td>
						<td>Any Flow PT site: status codes, error strings, value shapes, operator vocabularies</td>
						<td>Yes. The default, and all a public build has</td>
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
			<code>valid_values</code> is byte-identical at every scope. Only <code>hidden_values</code>
			varies by project, so "which statuses can I use" has no site-level answer (probe 009).
		</p>
		<p>
			Badges mark the scope: blue <code>api</code>, orange <code>site</code>, green
			<code>project</code>. A public build has only <code>api</code>.
		</p>
	</section>

	<section id="overlay">
		<h2>The overlay</h2>
		<p>
			<code>/sg-groundtruth-setup</code> writes <code>{data.overlayDir}/</code>. These pages read it
			and render its sections beside the <code>api</code> ones. It is gitignored, so it cannot reach
			a deployment.
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
			Frontmatter is the shape the shipped corpus uses. The <code>scope</code> must match the
			directory, so a local measurement cannot ship as a general fact. A
			<code>scope: project</code> file also names its project. Every field:
			<a href="{REPO}/blob/main/site/README.md">site/README.md</a>.
		</p>
	</section>

	<!-- Structure only: the copy is a content edit that fills `integrations` in
	     the script above, from site/RESEARCH-mcp.md. Renders nothing when the
	     list is empty. -->
	<section id="mcp">
		<h2>MCP servers for Flow PT</h2>
		<p>
			These call the API. <a href="#serve">This corpus</a> says what the API does. An agent given both
			has to be told which is which.
		</p>
		<p class="note">
			Each is MIT licensed and maintained. What is recorded was read from their source at a pinned
			commit, in <a href="{REPO}/blob/main/site/RESEARCH-mcp.md">RESEARCH-mcp.md</a>. Nothing was
			installed and no agent was measured using one.
		</p>
		{#if integrations.length}
			<div class="scroll-x">
				<table>
					<thead>
						<tr><th>server</th><th>what it is</th></tr>
					</thead>
					<tbody>
						{#each integrations as it (it.href)}
							<tr>
								<td><a href={it.href}>{it.name}</a></td>
								<td>{it.note}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
</div>

<style>
	.page {
		padding-block: var(--space-7) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-7);
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

	section {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--gap-prose);
		padding-top: var(--space-6);
		border-top: var(--border) solid var(--rule);
	}

	h2 {
		margin-bottom: var(--space-1);
	}

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	/* The first column names the thing; the second explains it. The name keeps
	   one line so the table reads as a list of names. */
	td:first-child {
		white-space: nowrap;
	}
</style>
