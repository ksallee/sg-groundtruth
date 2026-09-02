<script>
	import Prose from './Prose.svelte';
	import LocalBand from './LocalBand.svelte';
	import { REPO } from '$lib/site.js';

	// One corpus entry, rendered in full: the shipped card, then the local
	// overlay for the same slug if one was generated. `entry.local` is absent in
	// every public build.
	let { entry, kicker = '', backHref = '', backLabel = '' } = $props();

	const sourcePath = $derived(
		entry.group === 'recipes'
			? `corpus/recipes/${entry.slug}.md`
			: entry.group === 'field_types'
				? `corpus/findings/field_types/${entry.slug}.md`
				: `corpus/findings/${entry.slug}.md`
	);
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

	{#if entry.local}
		<LocalBand>
			<Prose html={entry.local.html} tone="site" />
		</LocalBand>
	{/if}
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
</style>
