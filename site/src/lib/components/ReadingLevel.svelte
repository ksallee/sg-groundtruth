<script>
	import { reading, choose } from '$lib/reading.svelte.js';

	// The global reading level. Rendered only when the build read an overlay, and
	// only with the levels the overlay can show, so no control on the
	// bar is ever disabled or empty.
	let { hasSite = false, projects = [] } = $props();

	const only = $derived(projects.length === 1 ? projects[0] : null);
	const current = $derived(projects.find((p) => p.id === reading.project) ?? null);
</script>

<div class="switch" role="group" aria-label="Reading level">
	<button
		type="button"
		class="step"
		aria-pressed={reading.level === 'api'}
		onclick={() => choose('api')}>API</button
	>

	{#if hasSite}
		<button
			type="button"
			class="step site"
			aria-pressed={reading.level === 'site'}
			onclick={() => choose('site')}>Site</button
		>
	{/if}

	{#if only}
		<button
			type="button"
			class="step project"
			aria-pressed={reading.level === 'project'}
			onclick={() => choose('project', only.id)}>{only.label}</button
		>
	{:else if projects.length}
		<label class="step project pick" aria-current={reading.level === 'project'}>
			<span class="visually-hidden">Project</span>
			<select
				value={current ? current.id : ''}
				onchange={(e) => (e.currentTarget.value ? choose('project', e.currentTarget.value) : choose('api'))}
			>
				<option value="">Project</option>
				{#each projects as p (p.id)}
					<option value={p.id}>{p.label}</option>
				{/each}
			</select>
		</label>
	{/if}
</div>

<style>
	/* One control, three stops, read left to right: each stop adds to the one
	   before it rather than replacing it. */
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
		align-items: center;
	}

	.step:first-child {
		border-left: 0;
	}

	.step:hover {
		color: var(--ink);
	}

	.step[aria-pressed='true'],
	.step[aria-current='true'] {
		background: var(--accent-quiet);
		color: var(--accent);
	}

	.step.site[aria-pressed='true'] {
		background: var(--accent-local-quiet);
		color: var(--accent-local);
	}

	.step.project[aria-pressed='true'],
	.step.project[aria-current='true'] {
		background: var(--accent-project-quiet);
		color: var(--accent-project);
	}

	.pick {
		padding: 0;
	}

	select {
		font: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: var(--space-1) var(--space-3);
		cursor: pointer;
		max-width: 14ch;
	}

	select:focus-visible {
		outline-offset: -2px;
	}
</style>
