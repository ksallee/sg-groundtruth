<script>
	// ROUTE CHOICE: /filters, not /reference/filters. /reference is an index page
	// over this route, /field-types and /entity-types; it groups them without
	// owning their URLs, so every reference route stays one flat segment and no
	// link has to move.
	//
	// TWO HALVES, TWO QUESTIONS. "Which operators does this type accept" is a
	// comparison and reads across the types, so it stays one table per family.
	// "What do I send to this operator" is a lookup and reads down one type, so
	// it gets a section each, with an anchor to link to and no control to open.
	let { data } = $props();

	// Every cell in the corpus writes API literals in backticks. Split rather
	// than render HTML: this file is the only place that needs it, and it takes
	// no dependency.
	function parts(text) {
		return text.split('`').map((t, i) => ({ text: t, code: i % 2 === 1 }));
	}

	const rows = $derived(data.types.reduce((n, t) => n + t.rows.length, 0));
	const gaps = $derived(data.types.reduce((n, t) => n + t.rows.filter((r) => r.gap).length, 0));
</script>

<svelte:head>
	<title>Filters: the operator vocabulary Flow PT returns per data type</title>
	<meta
		name="description"
		content="Every filter operator the Flow Production Tracking REST API accepts, per data_type, and the value each one takes. Read out of the reference cards. Five data types accept no operator at all."
	/>
</svelte:head>

<div class="page">
	<header>
		<h1>Filters</h1>
		<p class="lede">
			The relations each <code>data_type</code> accepts in a filter, and the value to send with each
			one. Every list here is the API's own, taken from the 400 it returns when sent an operator it
			does not know.
		</p>
		<p class="note">
			Read out of the <a href="/field-types">field-type cards</a> when this page is built, so the two
			cannot disagree. An unknown operator is always a 400 and never a silent no-op, so a typo in a
			filter cannot pass as "no filter". Measured by
			<a href="/findings/017_filter_operators">probe 017</a>.
		</p>
	</header>

	<section class="part">
		<h2>Operators, by family</h2>

		{#each data.families as family (family.id)}
			<section class="block">
				<h3>{family.title}</h3>
				<p class="block-note">
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
									<th scope="row"><a href="#{row.slug}">{row.name}</a></th>
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
	</section>

	<section class="part">
		<h2>Values, by data type</h2>
		<p class="block-note">
			{rows} rows across {data.types.length} data types. A matrix has one row per value shape, so an
			operator can appear more than once, and it includes the operators the API refuses, whose
			<code>matches</code> is the 400.
			{#if gaps}
				{gaps === 1 ? 'One row reads' : `${gaps} rows read`}
				<span class="gap">not measured</span>: the operator is in the API's own list and the card
				never sent it.
			{/if}
		</p>

		<nav aria-label="Data types">
			<ul class="jump">
				{#each data.types as type (type.slug)}
					<li><a href="#{type.slug}">{type.name}</a></li>
				{/each}
			</ul>
		</nav>

		{#each data.types as type (type.slug)}
			<section class="block" id={type.slug}>
				<h3><a href={type.href}>{type.name}</a></h3>

				{#if !type.filterable}
					<p class="block-note"><span class="empty">No relation is accepted.</span></p>
				{:else}
					<p class="block-note">
						{type.operators.length} operators, {type.rows.length} rows.
						{#if type.extra.length}
							The card also records
							{#each type.extra as column, i (column)}{i > 0
									? i === type.extra.length - 1
										? ' and '
										: ', '
									: ''}<em>{column}</em>{/each}.
						{/if}
					</p>

					<div class="scroll-x" tabindex="0">
						<table class="matrix">
							<thead>
								<tr>
									<th scope="col">Operator</th>
									<th scope="col">Value</th>
									<th scope="col">Matches</th>
								</tr>
							</thead>
							<tbody>
								{#each type.rows as row, i (i)}
									<tr class:is-gap={row.gap}>
										<th scope="row">
											{#each parts(row.operator) as part, n (n)}{#if part.code}<code
													>{part.text}</code
												>{:else}{part.text}{/if}{/each}
										</th>
										{#each [row.value, row.matches] as cell, n (n)}
											<td>
												{#if row.gap}
													<span class="gap">{cell}</span>
												{:else}
													{#each parts(cell) as part, m (m)}{#if part.code}<code>{part.text}</code
														>{:else}{part.text}{/if}{/each}
												{/if}
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</section>
		{/each}
	</section>
</div>

<style>
	.page {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-7);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
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

	.part {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-5);
	}

	.part > h2 {
		font-size: var(--text-lg);
		border-top: var(--border) solid var(--rule-strong);
		padding-top: var(--space-4);
	}

	.block {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
		/* The anchor lands below the header rather than under it. */
		scroll-margin-top: var(--space-5);
	}

	h3 {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		font-weight: 600;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--ink-muted);
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-3);
	}

	.block-note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	.jump {
		list-style: none;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-3);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
	}

	table {
		border-collapse: collapse;
		width: 100%;
		font-size: var(--text-sm);
	}

	/* Three columns of prose need a floor, or the value and the matches columns
	   collapse to one word each on a phone. Below it the container scrolls and
	   the page does not. */
	.matrix {
		min-width: 36rem;
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

	.matrix td {
		/* A uuid or a quoted error string is one long token. */
		overflow-wrap: anywhere;
	}

	.matrix code {
		white-space: pre-wrap;
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

	/* An operator the API lists and the card never sent. It is a hole in the
	   corpus, so it is marked rather than left blank or dropped. */
	.is-gap {
		background: var(--ground-sunken);
	}

	.gap {
		color: var(--ink-muted);
		font-style: italic;
		border-bottom: var(--border) dashed var(--rule-strong);
	}
</style>
