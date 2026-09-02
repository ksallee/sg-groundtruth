<script>
	import { REPO } from '$lib/site.js';

	let { data } = $props();
</script>

<svelte:head>
	<title>How to use the corpus</title>
	<meta
		name="description"
		content="Point a model at the corpus index, run the probes against your own Flow PT site, and read the scope field to tell what transfers from what you have to measure again."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>How to use it</h1>
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
			Every corpus file declares a <code>scope</code> in its frontmatter. It is the difference between
			a fact about the API and a fact about one installation of it.
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
						<td>A measurement of one site: which custom entities are enabled, which statuses a
							project hides, which fields are populated and how often.</td>
						<td>No. It does not generalise, so it is not stated as fact on a public page.</td>
					</tr>
				</tbody>
			</table>
		</div>
		<p>
			A reader forking this repository has to be able to tell, sentence by sentence, what transfers to
			their site and what they have to measure again. That is what the field is for. Findings marked
			<code>scope: api</code> still attribute any local number inline, beginning "On the probed site".
		</p>
	</section>

	<section id="overlay">
		<h2>Build a local copy that covers your own site</h2>
		<p>
			This site builds from two content sources. The first is <code>corpus/</code>, committed and
			public, filtered to <code>scope: api</code>. The second is
			<code>{data.overlayDir}/</code>, a gitignored directory generated against your own Flow PT site.
			When it is present, its entries render alongside the shipped ones, inside a labelled band, and
			the navigation gains a
			<a href="/site">This site</a> section.
		</p>
		<p>
			The overlay is never committed and so never reaches a public deployment. Building it is how you
			get documentation that covers your custom entities, your status vocabularies and your fill
			rates, with examples drawn from your own data.
		</p>

		<h3>The contract</h3>
		<p>Drop a markdown file in the matching directory. Nothing has to be registered.</p>
		<pre>{data.overlayDir}/findings/&lt;nnn&gt;_&lt;slug&gt;.md          a measurement of one site
{data.overlayDir}/findings/field_types/&lt;type&gt;.md    keyed to a data_type name
{data.overlayDir}/recipes/&lt;nnn&gt;_&lt;slug&gt;.md           a call made against one site</pre>
		<p>Frontmatter is the same shape the shipped corpus uses, with one difference.</p>
		<pre>---
tags: [version, status]
scope: site
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
						<td>On that entry's page, under a labelled band below the shipped card.</td>
					</tr>
					<tr>
						<td>slug matches nothing shipped</td>
						<td>On <code>/site</code>, as a local-only entry.</td>
					</tr>
					<tr>
						<td><code>scope</code> is not <code>site</code></td>
						<td>Skipped, with a warning on the build log. An overlay file can never be published
							as a general fact.</td>
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
			site. The site consumes the contract above and does not care what wrote the files.
		</p>
	</section>
</div>

<style>
	.page {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		gap: var(--space-6);
	}

	header {
		display: grid;
		gap: var(--space-3);
		max-width: var(--measure);
	}

	h1 {
		font-size: var(--text-xl);
	}

	section {
		display: grid;
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
</style>
