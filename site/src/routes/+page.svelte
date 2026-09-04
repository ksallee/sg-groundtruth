<script>
	import Section from '$lib/components/Section.svelte';
	import CopyButton from '$lib/components/CopyButton.svelte';
	import { OVERLAY_DIR, REPO } from '$lib/site.js';

	// Written from finding 027. The API is the same for every caller; what it
	// returns is filtered by permission, and every entry here was measured by a
	// script user with broad access.
	const PERMISSIONS_CAVEAT =
		'Every entry was measured by a script user with broad access. The API is the same for '
		+ 'every caller, but what it returns is filtered by permission, so a lower-permission '
		+ 'account may see fewer rows and fewer fields than an entry records.';

	// Two blocks, in the order they run, because the clone cannot be part of what
	// the agent is asked to do. /sg-groundtruth-setup is one of the repository's
	// own commands and is registered when a session starts, so an agent told to
	// clone the repository mid-session never gains it.
	const INSTALL = `# the corpus, the probes that produced it, and the setup command
git clone ${REPO}
cd sg-groundtruth

# start your agent from inside the clone, so it loads the repository's commands
claude`;

	// Handed to the agent verbatim, and it is one the repository has. The two
	// site-scope probe slugs never appear on this page: those are what the deploy
	// check greps the build for.
	const SETUP_PROMPT = '/sg-groundtruth-setup';
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
		The REST documentation is incomplete and in places wrong. Every entry here is what a live site
		answered when a script asked it. The scripts are in the repository and run against any site.
	</p>

	<p class="actions">
		<a class="button" href="/how-it-works">How it works</a>
		<a class="button ghost" href={REPO}>Read it on GitHub</a>
	</p>
</section>

<Section title="Who is it for">
	<div class="scroll-x">
		<table class="who">
			<tbody>
				<tr>
					<td>You</td>
					<td>Every entry is a page on this site.
						<a href="/entity-types">Start with the entity types</a>.</td>
				</tr>
				<tr>
					<td>Your agent</td>
					<td>Given proper instructions, it has a ground truth to refer to and probes it can run to
						check a claim.</td>
				</tr>
				<tr>
					<td>Your code</td>
					<td><code>FPT</code> is the client every probe here uses, so what the corpus records is
						what it does. <a href="/how-it-works#client">Call the API with it</a>.</td>
				</tr>
				<tr>
					<td>Your site</td>
					<td>Live data about your entity types, the fields in use, your status vocabularies and
						your projects.</td>
				</tr>
			</tbody>
		</table>
	</div>
	<p>
		<a href="/recipes">Recipes</a> are a call and the response it returned. The corpus has them.
		<code>/sg-groundtruth-adopt</code> writes new ones from code you already have.
	</p>
</Section>

<Section
	id="start"
	title="Start here"
	lede="Four commands. The last one asks what you want run, then measures your site and rebuilds these pages with your own entities, fields, status vocabularies and projects in them."
>
	<figure class="prompt">
		<figcaption>
			<span>In a terminal</span>
			<CopyButton text={INSTALL} />
		</figcaption>
		<pre>{INSTALL}</pre>
	</figure>

	<figure class="prompt">
		<figcaption>
			<span>Then, in the agent</span>
			<CopyButton text={SETUP_PROMPT} />
		</figcaption>
		<pre>{SETUP_PROMPT}</pre>
	</figure>

	<p class="caveat">
		Read-only. Nothing is written without <code>--write</code>, and what it measures stays in
		<code>{OVERLAY_DIR}/</code>, which is gitignored.
		<a href="/how-it-works#setup">What the command does, step by step</a>.
	</p>
</Section>

<!-- Three rows, each a published finding. The table is the argument, so nothing
     above it argues: the lede states the fact and stops. -->
<Section
	title="Why it exists"
	lede="Some Flow PT API calls fail silently. They answer 200 and do not do what you asked. They are documented here."
>
	<div class="scroll-x">
		<table>
			<thead>
				<tr><th>you do this</th><th>this happens</th></tr>
			</thead>
			<tbody>
				<tr>
					<td>Sort on a misspelled field</td>
					<td><code>200</code>. The sort is ignored, rows come back id ascending, and nothing says
						so <a href="/findings/026_result_order">026</a></td>
				</tr>
				<tr>
					<td>Page until <code>links.next</code> is absent</td>
					<td>It is never absent. It is emitted on zero-row pages too. Stop when <code>data</code>
						is empty <a href="/findings/006_pagination">006</a></td>
				</tr>
				<tr>
					<td>Create rows in a batch</td>
					<td>You get an id per row. A batch can return an id for a row it never made
						<a href="/findings/028_loud_and_silent">028</a></td>
				</tr>
			</tbody>
		</table>
	</div>

	<p class="caveat">{PERMISSIONS_CAVEAT}</p>
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
	.caveat {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	/* The first column names who, the second says what they get, so the name
	   keeps one line and the table reads as a list of names. Scoped: the failures
	   table below has a first column that must be free to wrap. */
	.who td:first-child {
		white-space: nowrap;
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
