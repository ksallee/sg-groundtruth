<script>
	import { OVERLAY_DIR } from '$lib/site.js';

	// Wraps anything that came from the local overlay. It exists so a reader can
	// never mistake a measurement of one site, or of one project inside it, for a
	// rule about the API. Every overlay entry on every page is inside one of
	// these.
	//
	// Never rendered when the overlay is absent: the caller checks the level.
	let { level = 'site', project = '', title = '', children } = $props();

	const heading = $derived(
		title || (level === 'project' ? `Measured on ${project}` : 'Measured on this site')
	);
	const source = $derived(level === 'project' ? `${OVERLAY_DIR}/projects/` : `${OVERLAY_DIR}/site/`);
	const subject = $derived(project ? `the ${project} project` : 'one project');
</script>

<aside class="band" class:project={level === 'project'}>
	<div class="head">
		<h2>{heading}</h2>
		{#if level === 'project'}
			<p>
				Read from <code>{source}</code>. This describes {subject} inside one Flow Production Tracking
				site. Hidden statuses, page settings and fill rates are set per project, so it does not
				transfer to another project on the same site.
			</p>
		{:else}
			<p>
				Read from <code>{source}</code>. This describes one Flow Production Tracking site's
				configuration, not the API. It is not part of the published corpus and does not transfer to
				another site.
			</p>
		{/if}
	</div>
	{@render children?.()}
</aside>

<style>
	.band {
		--band: var(--accent-local);
		--band-quiet: var(--accent-local-quiet);
		border: var(--border) solid var(--band);
		border-left-width: 3px;
		border-radius: var(--radius);
		background: var(--band-quiet);
		padding: var(--space-4) var(--space-5);
		display: grid;
		gap: var(--space-4);
	}

	.band.project {
		--band: var(--accent-project);
		--band-quiet: var(--accent-project-quiet);
	}

	.head {
		display: grid;
		gap: var(--space-2);
	}

	h2 {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--band);
	}

	p {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		max-width: var(--measure);
	}
</style>
