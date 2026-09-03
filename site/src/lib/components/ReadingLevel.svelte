<script>
	import { reading, choose, ALL } from '$lib/reading.svelte.js';

	// The global reading level, at the foot of the sidebar. Rendered only when the
	// build read an overlay, and only with the levels the overlay can show, so
	// nothing here is ever disabled or empty.
	//
	// Each level is a dot in its colour. The same dot sits beside every entry in
	// the tree above, so the switch teaches the dots.
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
		<span class="dot" aria-hidden="true"></span>API
	</button>

	{#if hasSite}
		<button
			type="button"
			class="step"
			data-scope="site"
			aria-pressed={reading.level === 'site'}
			onclick={() => choose('site')}
		>
			<span class="dot" aria-hidden="true"></span>Site
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
			<span class="dot" aria-hidden="true"></span><span class="label">{only.label}</span>
		</button>
	{:else if projects.length}
		<label class="step pick" data-scope="project" aria-current={reading.level === 'project'}>
			<span class="dot" aria-hidden="true"></span>
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
		display: grid;
		gap: 2px;
		font-size: var(--text-menu);
		line-height: 1.6;
	}

	.step {
		font: inherit;
		text-align: left;
		color: var(--ink-muted);
		background: none;
		border: 0;
		border-radius: 6px;
		padding: var(--space-1) var(--space-2);
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
		transition:
			color var(--duration) ease,
			background var(--duration) ease;
	}

	.step:hover {
		color: var(--ink);
		background: var(--sidebar-hover);
	}

	.step[aria-pressed='true'],
	.step[aria-current='true'] {
		background: var(--sidebar-active);
		color: var(--ink);
	}

	.dot {
		flex: 0 0 auto;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--scope-ink);
	}

	.label {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	select {
		font: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
		min-width: 0;
		max-width: 100%;
	}

	select:focus-visible {
		outline-offset: -2px;
	}
</style>
