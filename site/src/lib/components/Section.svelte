<script>
	// One band of the page: a mono label, an optional headline and lede, then
	// whatever the caller puts inside. Every landing-page section is one of these
	// so the vertical rhythm is decided in one place.
	let { label = '', title = '', lede = '', wide = false, children } = $props();
</script>

<section class="section">
	<div class="inner" class:wide>
		{#if label}<p class="label">{label}</p>{/if}
		{#if title}<h2>{title}</h2>{/if}
		{#if lede}<p class="lede">{lede}</p>{/if}
		{@render children?.()}
	</div>
</section>

<style>
	.section {
		padding-block: var(--space-7);
		border-top: var(--border) solid var(--rule);
	}

	.inner {
		max-width: var(--wide);
		margin-inline: auto;
		padding-inline: var(--gutter);
		display: grid;
		gap: var(--space-4);
	}

	.label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--ink-muted);
	}

	h2 {
		font-size: var(--text-xl);
		max-width: var(--measure);
	}

	.lede {
		font-size: var(--text-md);
		color: var(--ink-muted);
		max-width: var(--measure);
	}
</style>
