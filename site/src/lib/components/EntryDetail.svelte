<script>
	import Prose from './Prose.svelte';
	import LocalBand from './LocalBand.svelte';
	import { REPO } from '$lib/site.js';
	import { visible } from '$lib/reading.svelte.js';

	// One corpus entry, rendered in full: the shipped card, then whatever the
	// overlay measured about the same subject, at the reading level in force.
	// `entry.locals` is empty in every public build.
	let { entry, kicker = '', backHref = '', backLabel = '' } = $props();

	const locals = $derived(visible(entry.locals ?? []));

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
		<h1>{entry.fullName}</h1>
		<p class="verdict">{entry.verdict}</p>
		<ul class="meta">
			{#each entry.tags as tag (tag)}
				<li class="tag">{tag}</li>
			{/each}
			<li class="src"><a href="{REPO}/blob/main/{sourcePath}">Source markdown</a></li>
		</ul>
	</header>

	<Prose html={entry.html} />

	{#each locals as local (local.level + local.project + local.slug)}
		<LocalBand level={local.level} project={local.projectLabel}>
			<p class="local-verdict" class:project={local.level === 'project'}>{local.verdict}</p>
			<Prose html={local.html} tone={local.level} />
		</LocalBand>
	{/each}
</article>

<style>
	.entry {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		gap: var(--space-6);
	}

	header {
		display: grid;
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
		border-left: 3px solid var(--accent);
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
		border-left: 3px solid var(--accent-local);
		padding-left: var(--space-4);
		max-width: var(--measure);
	}

	.local-verdict.project {
		border-left-color: var(--accent-project);
	}
</style>
