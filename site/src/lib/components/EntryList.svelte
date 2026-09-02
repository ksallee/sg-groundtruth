<script>
	import ScopeMark from './ScopeMark.svelte';
	import ScopeLegend from './ScopeLegend.svelte';
	import { visible, mixed } from '$lib/reading.svelte.js';

	// The corpus index, as a list. One row is a name, its one-line verdict and
	// its tags, and it grows rather than moves as the reading level rises: the
	// API rows are the same rows at every level, joined by whatever the overlay
	// measured about the same subject and by the subjects the API says nothing
	// about at all.
	//
	// At the API level nothing is marked, because everything on the page is the
	// same kind of thing. Above it every row states what it holds.
	let { entries = [], showTags = true } = $props();

	// A row exists at this level if it has an API card, or a local card the
	// level shows. Nothing is ever hidden as the level rises; rows are added.
	const rows = $derived(
		entries
			.map((entry) => {
				const locals = visible(entry.locals ?? []);
				return { entry, locals, lead: entry.hasApi ? null : locals[0] };
			})
			.filter((row) => row.entry.hasApi || row.locals.length)
	);
</script>

{#if mixed()}
	<ScopeLegend />
{/if}

<ul class="list">
	{#each rows as { entry, locals, lead } (entry.group + entry.slug)}
		<li data-scope={lead ? lead.level : 'api'} class:local-only={Boolean(lead)}>
			<article>
				<h3>
					<a href={entry.href}>
						{#if entry.number}<span class="num">{entry.number}</span>{/if}
						<span class="name">{entry.title || entry.name}</span>
					</a>
					<!-- The slug is what a caller writes into a URL or a filter, so it
					     stays on the row whenever the label is something else. -->
					{#if entry.title && entry.title !== entry.slug}
						<code class="slug">{entry.slug}</code>
					{/if}
					{#if mixed()}
						{#if entry.hasApi}
							<ScopeMark level="api" />
						{/if}
						{#each locals as local (local.level + local.project)}
							<ScopeMark level={local.level} project={local.projectLabel} />
						{/each}
					{/if}
				</h3>
				<p class="verdict">{entry.hasApi ? entry.verdict : (lead?.verdict ?? '')}</p>
				{#if showTags}
					{@const tags = entry.hasApi ? entry.tags : (lead?.tags ?? [])}
					{#if tags.length}
						<ul class="tags">
							{#each tags as tag (tag)}
								<li>{tag}</li>
							{/each}
						</ul>
					{/if}
				{/if}
			</article>
		</li>
	{/each}
</ul>

<style>
	.list {
		list-style: none;
		padding: 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: 0;
	}

	.list > li {
		border-top: var(--border) solid var(--rule);
	}

	.list > li:last-child {
		border-bottom: var(--border) solid var(--rule);
	}

	/* A row the published corpus knows nothing about is inset, on its own
	   ground, behind the level's edge texture. The same treatment a detail
	   section gets, so the two read as one signal. */
	.list > li.local-only {
		position: relative;
		background: var(--scope-quiet);
		padding-left: calc(var(--space-4) + var(--scope-edge-width));
		padding-right: var(--space-4);
	}

	.list > li.local-only::before {
		content: '';
		position: absolute;
		inset-block: 0;
		left: 0;
		width: var(--scope-edge-width);
		background-image: var(--scope-edge);
	}

	article {
		padding: var(--space-4) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-2);
		max-width: var(--measure);
	}

	h3 {
		font-size: var(--text-md);
		font-weight: 600;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-2) var(--space-3);
	}

	h3 a {
		color: var(--ink);
		text-decoration: none;
		display: inline-flex;
		align-items: baseline;
		gap: var(--space-2);
	}

	h3 a:hover .name {
		text-decoration: underline;
	}

	.num,
	.name {
		font-family: var(--font-mono);
	}

	.num {
		color: var(--ink-muted);
		font-size: var(--text-sm);
		font-weight: 400;
	}

	.slug {
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.verdict {
		color: var(--ink-muted);
	}

	.tags {
		list-style: none;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-2);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.tags li::before {
		content: '#';
		opacity: 0.5;
	}
</style>
