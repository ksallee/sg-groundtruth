<script>
	import Prose from './Prose.svelte';
	import ScopeSection from './ScopeSection.svelte';
	import ScopeLegend from './ScopeLegend.svelte';
	import { REPO } from '$lib/site.js';
	import { visible, mixed } from '$lib/reading.svelte.js';

	// One subject, rendered in full and in one order: what the API does, then
	// what one site configures, then what one project does. Each is its own
	// marked section. A subject the published corpus has no card for renders the
	// local sections alone.
	//
	// `entry.locals` is empty in every public build, so this is the shipped card
	// and nothing else there.
	let { entry, kicker = '', backHref = '', backLabel = '' } = $props();

	const locals = $derived(visible(entry.locals ?? []));

	// The header describes the subject with the API card's line. Without one,
	// each local section carries its own verdict and the header carries none.
	const tags = $derived(entry.hasApi ? entry.tags : (locals[0]?.tags ?? []));

	// One directory per group, mirroring corpus/. Kept as a lookup rather than a
	// chain of ternaries so a new group is one line.
	const SOURCE_DIR = {
		recipes: 'corpus/recipes',
		field_types: 'corpus/findings/field_types',
		entity_types: 'corpus/findings/entity_types',
		findings: 'corpus/findings'
	};

	const sourcePath = $derived(`${SOURCE_DIR[entry.group] ?? 'corpus/findings'}/${entry.slug}.md`);
</script>

<article class="entry">
	<header>
		{#if backHref}
			<p class="back"><a href={backHref}>{backLabel}</a></p>
		{/if}
		{#if kicker}<p class="kicker">{kicker}</p>{/if}
		<h1>{entry.heading}</h1>
		<!-- Kept in view rather than replaced: a reader who cannot see the schema
		     name cannot call anything. -->
		{#if entry.title && entry.title !== entry.slug}
			<p class="slug"><code>{entry.slug}</code></p>
		{/if}

		{#if entry.hasApi}
			<p class="verdict">{entry.verdict}</p>
		{:else if locals.length}
			<p class="absent">
				The published corpus has no entry for this. Everything below was measured locally.
			</p>
		{:else}
			<p class="absent">
				This was measured on one site rather than read off the API. Set the reading level in the
				header to see it.
			</p>
		{/if}

		<ul class="meta">
			{#each tags as tag (tag)}
				<li class="tag">{tag}</li>
			{/each}
			{#if entry.hasApi}
				<li class="src"><a href="{REPO}/blob/main/{sourcePath}">Source markdown</a></li>
			{/if}
		</ul>
	</header>

	{#if mixed()}
		<ScopeLegend />
	{/if}

	{#if entry.hasApi}
		{#if mixed()}
			<ScopeSection level="api">
				<Prose html={entry.html} />
			</ScopeSection>
		{:else}
			<Prose html={entry.html} />
		{/if}
	{/if}

	{#each locals as local (local.level + local.project + local.slug)}
		<ScopeSection level={local.level} project={local.projectLabel} dir={local.project}>
			<p class="local-verdict" data-scope={local.level}>{local.verdict}</p>
			<Prose html={local.html} tone={local.level} />
		</ScopeSection>
	{/each}
</article>

<style>
	.entry {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
		max-width: var(--measure);
	}

	.back {
		font-size: var(--text-sm);
	}

	.kicker {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--ink-muted);
	}

	h1 {
		font-family: var(--font-mono);
		font-size: var(--text-xl);
	}

	/* The verdict is the entry's whole argument in one line, so it is set larger
	   than the body it introduces. */
	.verdict {
		font-size: var(--text-md);
		color: var(--ink);
		border-left: var(--scope-edge-width) solid var(--accent);
		padding-left: var(--space-4);
	}

	.slug {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	.absent {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		border-left: var(--scope-edge-width) solid var(--rule-strong);
		padding-left: var(--space-4);
	}

	.meta {
		list-style: none;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-3);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.tag::before {
		content: '#';
		opacity: 0.5;
	}

	.src {
		margin-left: auto;
	}

	.local-verdict {
		border-left: var(--scope-edge-width) solid var(--scope-ink);
		padding-left: var(--space-4);
		max-width: var(--measure);
	}
</style>
