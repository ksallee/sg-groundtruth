<script>
	// One band of the landing page: a small mono label, a headline and a lede,
	// then whatever the caller puts inside. Every section is one of these so
	// the vertical rhythm is decided in one place. `literal` sets the title in
	// mono, for a title that is an API literal.
	let { label = '', title = '', lede = '', literal = false, children } = $props();
</script>

<section class="col section">
	{#if label || title || lede}
		<header>
			{#if label}<p class="label">{label}</p>{/if}
			{#if title}<h2 class:literal>{title}</h2>{/if}
			{#if lede}<p class="lede">{lede}</p>{/if}
		</header>
	{/if}
	{@render children?.()}
</section>

<style>
	.section {
		padding-top: var(--space-8);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
	}

	.label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	h2.literal {
		font-family: var(--font-mono);
		letter-spacing: 0;
	}

	.lede {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}
</style>
