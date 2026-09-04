<script>
	import ScopeMark from './ScopeMark.svelte';
	import { parts } from '$lib/text.js';
	import { visible } from '$lib/reading.svelte.js';

	// The corpus index, as a list. One row is a name, its one-line verdict and
	// its tags, and it grows rather than moves as the reading level rises: the
	// API rows are the same rows at every level, joined by whatever the overlay
	// measured about the same subject and by the subjects the API says nothing
	// about at all.
	//
	// A row that holds more than one level, or none of the API's, says so with a
	// badge per level. A row that is the API alone needs no badge.
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

	// A field type, or an entity type with no display title, is named by the
	// API's own literal and is set in mono, exactly as the API spells it.
	const literal = (entry) =>
		entry.group === 'endpoints' ||
		(!entry.title && (entry.group === 'field_types' || entry.group === 'entity_types'));

	const nameOf = (entry) => entry.title || entry.name || entry.fullName.replace(/^\d+\s+/, '');
</script>

<ul class="list">
	{#each rows as { entry, locals, lead } (entry.group + entry.slug)}
		<li>
			<article class:literal={literal(entry)}>
				<h3>
					<a href={entry.href}>
						{#if entry.number}<span class="num">{entry.number}</span>{/if}
						<span class="name">{nameOf(entry)}</span>
					</a>
					<!-- The slug is what a caller writes into a URL or a filter, so it
					     stays on the row whenever the label is something else. -->
					{#if entry.title && entry.title !== entry.slug}
						<code class="slug">{entry.slug}</code>
					{/if}
					{#if locals.length}
						{#if entry.hasApi}
							<ScopeMark level="api" />
						{/if}
						{#each locals as local (local.level + local.project)}
							<ScopeMark level={local.level} project={local.projectLabel} />
						{/each}
					{/if}
					<!-- A card whose calls were not all made and answered must not read
					     like one that was. The badge is on the row, not only the page. -->
					{#if entry.coverage && entry.coverage !== 'measured'}
						<span class="coverage" data-coverage={entry.coverage}>{entry.coverage}</span>
					{/if}
				</h3>
				<p class="verdict">
					{#each parts(entry.hasApi ? entry.verdict : (lead?.verdict ?? '')) as part, i (i)}{#if part.code}<code
							>{part.text}</code
						>{:else}{part.text}{/if}{/each}
				</p>
				{#if entry.unmeasured}
					<p class="unmeasured"><strong>Not measured.</strong> {entry.unmeasured}</p>
				{/if}
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
	}

	.list > li {
		border-top: var(--border) solid var(--rule);
	}

	.list > li:last-child {
		border-bottom: var(--border) solid var(--rule);
	}

	article {
		padding: var(--space-4) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-1);
	}

	h3 {
		font-size: var(--text-body);
		font-weight: var(--weight-medium);
		line-height: var(--leading-body);
		letter-spacing: var(--tracking-body);
		text-wrap: pretty;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-2) var(--space-3);
	}

	h3 a {
		text-decoration: none;
		display: inline-flex;
		align-items: baseline;
		gap: var(--space-2);
	}

	h3 a:hover .name {
		text-decoration: underline;
		text-decoration-color: var(--underline);
		text-decoration-thickness: 1px;
		text-underline-offset: 0.18em;
	}

	.num {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 400;
		color: var(--ink-muted);
	}

	.literal .name {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
	}

	.slug {
		font-size: var(--text-xs);
		color: var(--ink-muted);
		background: none;
		padding: 0;
	}

	.coverage {
		font-size: var(--text-xs);
		font-family: var(--mono);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 0.1em 0.45em;
		border-radius: 0.25em;
		border: var(--border) solid currentColor;
		color: var(--ink-3);
		vertical-align: 0.15em;
	}

	.coverage[data-coverage='untested'] {
		color: var(--warn, var(--ink-2));
	}

	.unmeasured {
		font-size: var(--text-sm);
		color: var(--ink-3);
		border-left: var(--border) solid var(--rule);
		padding-left: var(--space-3);
	}

	.verdict {
		font-size: var(--text-sm);
		line-height: 1.5;
		color: var(--ink-body);
	}

	.tags {
		list-style: none;
		padding: 0;
		margin-top: var(--space-1);
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-2);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.tags li::before {
		content: '#';
		opacity: 0.6;
	}
</style>
