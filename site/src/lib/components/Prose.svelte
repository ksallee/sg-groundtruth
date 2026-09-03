<script>
	// Renders one corpus entry's body. The HTML is produced at build time by
	// src/lib/content/corpus.js from markdown in this repo, so it is trusted.
	let { html, tone = 'api' } = $props();
</script>

<div class="prose" class:local={tone === 'site'} class:project={tone === 'project'}>
	{@html html}
</div>

<style>
	.prose {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--gap-prose);
		min-width: 0;
	}

	.prose > :global(*) {
		min-width: 0;
	}

	/* The corpus opens a section with a bold label at the start of a paragraph
	   rather than with a heading: Data type, Read, Write, Clear, Filter and
	   Traps on a field-type card; Type, Identity, Create, Links, Status and
	   Traps on an entity type; Q, Endpoint, Docs claim, Actual and Teaches on
	   a finding. The label is set on its own line in the full ink, with a
	   section's worth of air above it. The markdown is untouched. */
	.prose :global(p > strong:first-child) {
		display: block;
		margin-top: var(--space-3);
		margin-bottom: var(--space-1);
		letter-spacing: var(--tracking-heading);
	}

	.prose > :global(:first-child > strong:first-child) {
		margin-top: 0;
	}

	/* The few real headings the corpus has sit below the page's own h1. */
	.prose :global(h2) {
		font-size: 1.375rem;
		margin-top: var(--space-4);
	}

	.prose :global(h3) {
		font-size: var(--text-body);
		font-weight: var(--weight-bold);
		margin-top: var(--space-2);
	}

	.prose :global(ul),
	.prose :global(ol) {
		padding-left: var(--space-5);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
	}

	.prose :global(li::marker) {
		color: var(--ink-muted);
	}

	.prose :global(li > ul),
	.prose :global(li > ol) {
		margin-top: var(--space-2);
	}

	.prose :global(blockquote) {
		padding-left: var(--space-4);
		border-left: 2px solid var(--rule-strong);
		color: var(--ink-muted);
	}

	/* Locally measured content reuses every rule above and changes only the
	   link hue, so a reader never has to learn a second layout. */
	.prose.local :global(a) {
		color: var(--accent-local);
	}

	.prose.project :global(a) {
		color: var(--accent-project);
	}
</style>
