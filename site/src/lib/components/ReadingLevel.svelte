<script>
	import { reading, choose, ALL } from '$lib/reading.svelte.js';

	// The global reading level. Rendered only when the build read an overlay, and
	// only with the levels the overlay can show, so no control on the bar is ever
	// disabled or empty.
	//
	// Read left to right: each step adds to the one before it. The step carries
	// the same edge texture the content it adds carries, so the switch teaches
	// the marks on the page below it.
	let { hasSite = false, projects = [] } = $props();

	// One project needs no union: every project is that project.
	const only = $derived(projects.length === 1 ? projects[0] : null);
	const chosen = $derived(reading.level === 'project' ? reading.project : '');
</script>

<div class="switch" role="group" aria-label="Reading level">
	<button
		type="button"
		class="step"
		data-scope="api"
		aria-pressed={reading.level === 'api'}
		onclick={() => choose('api')}
	>
		<span class="scope-edge" aria-hidden="true"></span>API
	</button>

	{#if hasSite}
		<button
			type="button"
			class="step"
			data-scope="site"
			aria-pressed={reading.level === 'site'}
			onclick={() => choose('site')}
		>
			<span class="scope-edge" aria-hidden="true"></span>Site
		</button>
	{/if}

	{#if only}
		<button
			type="button"
			class="step"
			data-scope="project"
			aria-pressed={reading.level === 'project'}
			onclick={() => choose('project', only.id)}
		>
			<span class="scope-edge" aria-hidden="true"></span>{only.label}
		</button>
	{:else if projects.length}
		<label class="step pick" data-scope="project" aria-current={reading.level === 'project'}>
			<span class="scope-edge" aria-hidden="true"></span>
			<span class="visually-hidden">Project</span>
			<select value={chosen} onchange={(e) => choose('project', e.currentTarget.value)}>
				<option value="" disabled>Project</option>
				<option value={ALL}>All projects</option>
				{#each projects as p (p.id)}
					<option value={p.id}>{p.label}</option>
				{/each}
			</select>
		</label>
	{/if}
</div>

<style>
	.switch {
		display: flex;
		align-items: stretch;
		border: var(--border) solid var(--rule-strong);
		border-radius: var(--radius);
		overflow: hidden;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
	}

	.step {
		font: inherit;
		color: var(--ink-muted);
		background: var(--ground);
		border: 0;
		border-left: var(--border) solid var(--rule);
		padding: var(--space-1) var(--space-3);
		cursor: pointer;
		white-space: nowrap;
		display: flex;
		align-items: stretch;
		gap: var(--space-2);
	}

	.step:first-child {
		border-left: 0;
	}

	.step:hover {
		color: var(--ink);
	}

	.step[aria-pressed='true'],
	.step[aria-current='true'] {
		background: var(--scope-quiet);
		color: var(--scope-ink);
	}

	.pick {
		padding-right: 0;
		align-items: center;
	}

	select {
		font: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: var(--space-1) var(--space-3) var(--space-1) 0;
		cursor: pointer;
		max-width: 16ch;
	}

	select:focus-visible {
		outline-offset: -2px;
	}
</style>
