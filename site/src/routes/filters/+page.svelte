<script>
	// ROUTE CHOICE: /filters, not /reference/filters. /reference is an index page
	// over this route, /field-types and /entity-types; it groups them without
	// owning their URLs, so every reference route stays one flat segment and no
	// link has to move.
	let { data } = $props();

	// Family notes are written with backticks, the way the corpus writes API
	// literals. Split rather than render HTML: this file is the only place that
	// needs it, and it takes no dependency.
	function parts(note) {
		return note.split('`').map((text, i) => ({ text, code: i % 2 === 1 }));
	}
</script>

<svelte:head>
	<title>Filters: the operator vocabulary Flow PT returns per data type</title>
	<meta
		name="description"
		content="Every filter operator the Flow Production Tracking REST API accepts, per data_type, read out of the reference cards. Five data types accept no operator at all."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>Filters</h1>
		<p class="lede">
			The relations each <code>data_type</code> accepts in a filter. Every list here is the API's own,
			taken from the 400 it returns when sent an operator it does not know.
		</p>
		<p class="note">
			Read out of the <a href="/field-types">field-type cards</a> when this page is built, so the two
			cannot disagree. An unknown operator is always a 400 and never a silent no-op, so a typo in a
			filter cannot pass as "no filter". Measured by
			<a href="/findings/017_filter_operators">probe 017</a>.
		</p>
	</header>

	{#each data.families as family (family.id)}
		<section>
			<h2>{family.title}</h2>
			<p class="family-note">
				{#each parts(family.note) as part, i (i)}{#if part.code}<code>{part.text}</code
					>{:else}{part.text}{/if}{/each}
				{#if family.shared}
					All {family.rows.length} return the identical list of {family.size}.
				{/if}
			</p>

			<div class="scroll-x" tabindex="0">
				<table>
					<thead>
						<tr>
							<th scope="col">Data type</th>
							<th scope="col">Relations</th>
						</tr>
					</thead>
					<tbody>
						{#each family.rows as row (row.slug)}
							<tr>
								<th scope="row"><a href={row.href}>{row.name}</a></th>
								<td>
									{#if row.operators.length}
										<ul class="ops">
											{#each row.operators as op (op)}
												<li><code>{op}</code></li>
											{/each}
										</ul>
									{:else}
										<span class="empty">No relation is accepted.</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/each}
</div>

<style>
	.page {
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

	h1 {
		font-size: var(--text-xl);
	}

	.lede {
		color: var(--ink-muted);
	}

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		border-left: 3px solid var(--rule-strong);
		padding-left: var(--space-4);
	}

	section {
		display: grid;
		gap: var(--space-3);
	}

	h2 {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--ink-muted);
		border-top: var(--border) solid var(--rule-strong);
		padding-top: var(--space-3);
	}

	.family-note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	table {
		border-collapse: collapse;
		width: 100%;
		font-size: var(--text-sm);
	}

	th,
	td {
		text-align: left;
		vertical-align: top;
		padding: var(--space-3);
		border-bottom: var(--border) solid var(--rule);
	}

	thead th {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-muted);
		border-bottom-color: var(--rule-strong);
		white-space: nowrap;
	}

	tbody th {
		font-family: var(--font-mono);
		font-weight: 600;
		white-space: nowrap;
	}

	tbody tr:last-child th,
	tbody tr:last-child td {
		border-bottom: 0;
	}

	/* The operators wrap inside their cell rather than widening the table, so a
	   narrow screen scrolls only when the type names alone are too wide. */
	.ops {
		list-style: none;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-2);
	}

	.ops code {
		background: var(--ground-sunken);
		border: var(--border) solid var(--rule);
		border-radius: var(--radius-sm);
		padding: 0.1em 0.35em;
	}

	.empty {
		color: var(--ink-muted);
	}
</style>
