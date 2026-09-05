<script>
	// What a report holds that a finding does not: who it is for, whether anyone
	// has filed it, and when the behaviour was last seen. The date is the point:
	// a report is a claim about a moving target, and this group is what to re-run
	// after a Flow Production Tracking release.
	let { entry } = $props();

	const KIND = {
		api: 'The behaviour should change',
		docs: 'The behaviour is defensible and undocumented'
	};
</script>

<dl>
	<div>
		<dt>Kind</dt>
		<dd>{KIND[entry.kind] ?? entry.kind}</dd>
	</div>
	<div>
		<dt>Status</dt>
		<dd>{entry.status}{entry.ticket ? `, ${entry.ticket}` : ''}</dd>
	</div>
	<div>
		<dt>Confirmed</dt>
		<dd><code>{entry.confirmed}</code></dd>
	</div>
	{#if entry.evidence.length}
		<div>
			<dt>Evidence</dt>
			<dd>
				<!-- Never restated here. These are the entries holding the calls, the
				     responses and the error strings verbatim.

				     Drawn in the shape an endpoint card draws its Links: mono, spaced,
				     one per item. Comma-separated, they read as a sentence that happened
				     to be underlined. -->
				<ul class="refs">
					{#each entry.evidence as e (e.href)}
						<li><a href={e.href}>{e.name}</a></li>
					{/each}
				</ul>
			</dd>
		</div>
	{/if}
</dl>

<style>
	dl {
		margin: 0 0 var(--space-5);
		display: grid;
		gap: var(--space-2) var(--space-4);
		font-size: var(--text-sm);
	}

	div {
		display: grid;
		grid-template-columns: 7rem 1fr;
		gap: var(--space-3);
		align-items: baseline;
	}

	dt {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	dd {
		margin: 0;
		color: var(--ink-body);
	}

	.refs {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-4);
	}

	.refs a {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
	}
</style>
