<script>
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	// ROUTE CHOICE: /doors, beside the five groups. A door is not a sixth kind of
	// entry, so it is not in the sidebar with them; it is the tier between the map
	// and an entry, and this page is where a reader is told what that means. The
	// footer links it, because the client that wants it did not arrive at the
	// front door.
	let { data } = $props();

	const kb = (bytes) => Math.round(bytes / 1024);
	const sizes = $derived(data.kinds.flatMap((k) => k.doors.map((d) => d.bytes)));

	// What one row of a door is. An endpoint door is one section per call; every
	// other door is one per entry, except the two that are a flat list.
	const UNIT = {
		endpoints: ['call', 'calls'],
		reports: ['report', 'reports'],
		tags: ['tag', 'tags']
	};
	const holds = (kind, door) => {
		const [one, many] = UNIT[kind] ?? ['entry', 'entries'];
		return `${door.count} ${door.count === 1 ? one : many}`;
	};
</script>

<svelte:head>
	<title>Doors: the rules for what you already hold</title>
	<meta
		name="description"
		content="A door carries one line per entry and that entry's rules, copied whole. One per findings phase, one per endpoint family, one each for the field types, entity types, recipes, reports and tags."
	/>
</svelte:head>

<div class="col page">
	<header>
		<Breadcrumb trail={[{ label: 'Doors' }]} />
		<h1>Doors</h1>
		<p class="lede">
			A door carries one line per entry and that entry's rules, copied whole. Open the one that
			answers what you already hold, and an entry only when a rule needs its evidence.
		</p>
		<div class="scroll-x">
			<table>
				<thead>
					<tr><th>tier</th><th>holds</th><th>size</th></tr>
				</thead>
				<tbody>
					<tr>
						<td><a href="/llms.txt"><code>/llms.txt</code></a></td>
						<td>the map: every entry by name, and the door to open for each way in</td>
						<td>{kb(data.llmsBytes)} KB</td>
					</tr>
					<tr>
						<td>a door</td>
						<td>the rules, copied whole from the entries in one group</td>
						<td>{kb(Math.min(...sizes))} to {kb(Math.max(...sizes))} KB</td>
					</tr>
					<tr>
						<td>an entry</td>
						<td>the transcript, the sample and the tables behind one rule</td>
						<td>{kb(data.entries.min)} to {kb(data.entries.max)} KB</td>
					</tr>
				</tbody>
			</table>
		</div>
		<p class="note">
			Generated from the corpus by <code>probes/index.py</code>, and served here as written. Append
			<code>.md</code> to a door's URL for the file itself. A door is built from the shipped corpus
			alone, so it is the <code>api</code> level whatever the reading level on an entry page says.
		</p>
	</header>

	{#each data.kinds as kind (kind.id)}
		<section>
			<h2 id={kind.id.replace('_', '-')}>{kind.title}</h2>
			{#if kind.note}<p class="note">{kind.note}</p>{/if}
			<div class="scroll-x">
				<table>
					<thead>
						<tr><th>door</th><th>holds</th><th>size</th></tr>
					</thead>
					<tbody>
						{#each kind.doors as door (door.name)}
							<tr>
								<td><a href={door.href}>{door.title}</a></td>
								<td>{holds(kind.id, door)}</td>
								<td>{kb(door.bytes)} KB</td>
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
		padding-block: var(--space-7) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-7);
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

	section {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-4);
		padding-top: var(--space-5);
		border-top: var(--border) solid var(--rule);
	}

	.note {
		font-size: var(--text-sm);
		color: var(--ink-muted);
	}

	/* The first column names the door; the rest are counts. The name keeps one
	   line so the table reads as a list of names. */
	td:first-child {
		white-space: nowrap;
	}
</style>
