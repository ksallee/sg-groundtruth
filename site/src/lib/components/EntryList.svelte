<script>
	// The corpus index, as a list. One row is a name, its one-line verdict and
	// its tags. Used on the landing page and on every index route.
	let { entries = [], tone = 'api', showTags = true } = $props();
</script>

<ul class="list" class:local={tone === 'site'}>
	{#each entries as entry (entry.group + entry.slug)}
		<li>
			<article>
				<h3>
					<a href={entry.href}>
						{#if entry.number}<span class="num">{entry.number}</span>{/if}
						<span class="name">{entry.name}</span>
					</a>
					{#if entry.hasLocal}
						<span class="flag" title="This entry also has a measurement of your site"
							>+ this site</span
						>
					{/if}
				</h3>
				<p class="verdict">{entry.verdict}</p>
				{#if showTags && entry.tags.length}
					<ul class="tags">
						{#each entry.tags as tag (tag)}
							<li>{tag}</li>
						{/each}
					</ul>
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
		gap: 0;
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
		gap: var(--space-2);
		max-width: var(--measure);
	}

	h3 {
		font-size: var(--text-md);
		font-weight: 600;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
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

	.flag {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--accent-local);
		background: var(--accent-local-quiet);
		border-radius: var(--radius-sm);
		padding: 0 var(--space-2);
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

	.list.local h3 a {
		color: var(--accent-local);
	}
</style>
