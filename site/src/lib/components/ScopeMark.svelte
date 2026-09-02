<script>
	// The one mark that separates the three kinds of information. It names its
	// level in words, draws the level's edge texture beside the word, and takes
	// the level's hue. Colour is the third signal, never the only one.
	//
	// The same component is the flag on a list row, the head of a detail section
	// and the swatch on the reading-level switch, so the three cannot drift.
	let { level = 'api', project = '', as = 'span' } = $props();

	const word = $derived(
		level === 'project' ? project || 'One project' : level === 'site' ? 'This site' : 'The API'
	);
</script>

<svelte:element this={as} class="mark" data-scope={level}>
	<span class="scope-edge" aria-hidden="true"></span>
	<span class="word">{word}</span>
</svelte:element>

<style>
	.mark {
		display: inline-flex;
		align-items: stretch;
		gap: var(--space-2);
		background: var(--scope-quiet);
		border-radius: var(--radius-sm);
		padding: 0 var(--space-2) 0 0;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--scope-ink);
		white-space: nowrap;
	}

	.word {
		padding-block: 0.15em;
	}
</style>
