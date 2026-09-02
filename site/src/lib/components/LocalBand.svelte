<script>
	// Wraps anything that came from the local overlay (corpus.local/). It exists
	// so a reader can never mistake a measurement of one site for a rule about
	// the API. Every overlay entry on every page is inside one of these.
	//
	// Never rendered when the overlay is absent: the caller checks hasOverlay.
	let { title = 'Measured on this site', children } = $props();
</script>

<aside class="band">
	<div class="head">
		<h2>{title}</h2>
		<p>
			Read from <code>corpus.local/</code>. This describes one Flow PT site's configuration and data,
			not the API. It is not part of the published corpus and does not transfer to another site.
		</p>
	</div>
	{@render children?.()}
</aside>

<style>
	.band {
		border: var(--border) solid var(--accent-local);
		border-left-width: 3px;
		border-radius: var(--radius);
		background: var(--accent-local-quiet);
		padding: var(--space-4) var(--space-5);
		display: grid;
		gap: var(--space-4);
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
		color: var(--accent-local);
	}

	p {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		max-width: var(--measure);
	}
</style>
