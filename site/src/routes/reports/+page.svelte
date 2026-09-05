<script>
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import { parts } from '$lib/text.js';

	let { data } = $props();

	// A table rather than the entry list every other group uses. What a reader
	// wants here is which of these are filed and when each was last seen, and
	// that is one row per report with a column each.
	const rows = $derived(data.entries.filter((e) => e.hasApi));
</script>

<svelte:head>
	<title>Reports: Flow PT REST behaviour that should change</title>
	<meta
		name="description"
		content="Behaviour of the Flow Production Tracking REST API that should change, written for the team that owns it: what was expected, what happened, how to reproduce it, and the proposed fix."
	/>
</svelte:head>

<div class="col page">
	<header>
		<Breadcrumb trail={[{ label: 'Reports' }]} />
		<h1>Reports</h1>
		<p class="lede">
			A finding records what the API does and ends in a line telling a caller what to do about it. A
			report is the same behaviour written for the team that owns the API: what was expected, what
			happened, a transcript anyone can run, and the change that would fix it.
		</p>
		<p class="note">
			Each names the entries that measured it rather than restating them, and dates the last time the
			behaviour was seen. That date is what makes this list the one to re-run after a Flow Production
			Tracking release.
		</p>
	</header>

	<div class="scroll-x">
		<table>
			<thead>
				<tr><th>report</th><th>kind</th><th>status</th><th>confirmed</th></tr>
			</thead>
			<tbody>
				{#each rows as row (row.slug)}
					<tr>
						<td>
							<a href={row.href}>{row.name}</a>
							<p>
								{#each parts(row.verdict) as part, i (i)}{#if part.code}<code>{part.text}</code
									>{:else}{part.text}{/if}{/each}
							</p>
						</td>
						<td><code>{row.kind}</code></td>
						<td><code>{row.status}</code>{row.ticket ? `, ${row.ticket}` : ''}</td>
						<td><code>{row.confirmed}</code></td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

<style>
	.page {
		padding-block: var(--space-7) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
	}

	.lede {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	/* The first column is the report and its one line; the other three are one
	   short literal each and take only what they need. */
	td:first-child {
		min-width: 22rem;
	}

	/* kind, status and confirmed are one short literal each. Left to wrap, the
	   heading broke as "confirm/ed" and the dates as "2026-/09-04". */
	th:not(:first-child),
	td:not(:first-child) {
		white-space: nowrap;
	}

	td p {
		margin: var(--space-1) 0 0;
		color: var(--ink-muted);
		font-size: var(--text-sm);
	}
</style>
