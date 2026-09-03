<script>
	// The badge that says which level a thing was read at: API, the site, or a
	// project by name, in the level's colour. The same badge heads a section on
	// an entry page, sits on a list row and fills the switch at the top of a
	// page, so the three cannot drift.
	let { level = 'api', project = '', as = 'span' } = $props();

	const word = $derived(
		level === 'project' ? project || 'Project' : level === 'site' ? 'Site' : 'API'
	);
</script>

<svelte:element this={as} class="badge" data-scope={level}>{word}</svelte:element>

<style>
	.badge {
		display: inline-block;
		padding: 0.1em 0.6em;
		border-radius: var(--radius-sm);
		background: var(--scope-quiet);
		color: var(--scope-ink);
		font-size: var(--text-sm);
		font-weight: 400;
		line-height: 1.6;
		letter-spacing: 0;
		white-space: nowrap;
	}
</style>
