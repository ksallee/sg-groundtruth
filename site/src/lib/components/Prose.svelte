<script>
	// Renders one corpus entry's body. The HTML is produced at build time by
	// src/lib/content/corpus.js from markdown in this repo, so it is trusted.
	let { html, tone = 'api' } = $props();
</script>

<div class="prose" class:local={tone === 'site'} class:project={tone === 'project'}>
	{@html html}
</div>

<style>
	/* Two widths in one column. Prose is capped at --measure so it stays
	   readable; the reference tables and payload slabs are wider by nature (one
	   row per input, one column per outcome) and are allowed out to
	   --measure-wide, scrolling inside themselves past that.
	   The container itself is unconstrained, so the cap has to sit on the
	   children. Capping .prose instead traps the tables at --measure. */
	.prose {
		display: grid;
		grid-template-columns: var(--col);
		justify-items: start;
		gap: var(--space-4);
		max-width: 100%;
	}

	.prose > :global(*) {
		max-width: var(--measure);
		width: 100%;
	}

	.prose > :global(.scroll-x),
	.prose > :global(pre) {
		max-width: var(--measure-wide);
	}

	/* The section head is larger than the body under it and set in ink. It was
	   --text-xs uppercase muted, which drew it identically to the table head
	   beneath it and left a reader scrolling for a name nothing to scan for. */
	.prose :global(h2) {
		font-family: var(--font-mono);
		font-size: var(--text-md);
		font-weight: 600;
		line-height: var(--leading-tight);
		color: var(--ink);
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-3);
		margin-top: var(--space-5);
	}

	.prose :global(h3) {
		font-size: var(--text-md);
	}

	/* The corpus marks its section heads with bold at the start of a paragraph
	   (**Read**, **Write**, **Clear**, **Filter**, **Traps**) rather than with
	   headings, and nothing here can turn those into real headings without
	   editing the corpus, which this site does not do. A bold run that opens a
	   paragraph is drawn as a run-in label instead: the card's structure is
	   visible without a heading existing. Bold anywhere else stays bold. */
	.prose :global(strong) {
		font-weight: 650;
	}

	.prose :global(p > strong:first-child) {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--ink-muted);
	}

	.prose :global(a) {
		color: var(--accent);
	}

	.prose :global(ul),
	.prose :global(ol) {
		padding-left: var(--space-5);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
	}

	/* A tint, no border. These paragraphs are 40 to 60% literals, and a bordered
	   chip per literal renders a sentence as a row of boxes. */
	.prose :global(code) {
		background: var(--ground-sunken);
		border-radius: var(--radius-sm);
		padding: 0.1em 0.3em;
	}

	.prose :global(pre) {
		background: var(--slab);
		color: var(--slab-ink);
		border-radius: var(--radius);
		padding: var(--space-4);
		overflow-x: auto;
		font-size: var(--text-sm);
		line-height: 1.5;
	}

	.prose :global(pre code) {
		background: none;
		border: 0;
		padding: 0;
		color: inherit;
		font-size: inherit;
	}

	.prose :global(table) {
		border-collapse: collapse;
		font-size: var(--text-sm);
		/* Cells hold API literals and error strings. Let the table find its own
		   width and scroll, rather than wrapping every cell to nothing. */
		width: max-content;
		min-width: 100%;
	}

	.prose :global(th),
	.prose :global(td) {
		text-align: left;
		vertical-align: top;
		padding: var(--cell-y) var(--cell-x);
		line-height: var(--leading-tabular);
		border-bottom: var(--border) solid var(--rule);
	}

	.prose :global(th) {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-muted);
		border-bottom-color: var(--rule-strong);
		white-space: nowrap;
	}

	.prose :global(tbody tr:last-child td) {
		border-bottom: 0;
	}

	.prose :global(blockquote) {
		margin: 0;
		padding-left: var(--space-4);
		border-left: 2px solid var(--rule-strong);
		color: var(--ink-muted);
	}

	/* Locally measured content reuses every rule above and changes only the
	   accent, so a reader never has to learn a second layout. */
	.prose.local :global(a) {
		color: var(--accent-local);
	}

	.prose.project :global(a) {
		color: var(--accent-project);
	}
</style>
