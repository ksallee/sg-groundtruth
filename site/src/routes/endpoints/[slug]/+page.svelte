<script>
	import EntryDetail from '$lib/components/EntryDetail.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.entry.heading}: Flow PT REST endpoint</title>
	<meta name="description" content={data.entry.verdict} />
</svelte:head>

<EntryDetail entry={data.entry} section={{ label: 'Endpoints', href: '/endpoints' }} />

{#if data.links.length}
	<div class="col links">
		<h2>Links</h2>
		{#each data.links as group (group.id)}
			<section>
				<h3>{group.label}</h3>
				<ul>
					{#each group.items as item (item.href)}
						<li><a href={item.href}>{item.name}</a></li>
					{/each}
				</ul>
			</section>
		{/each}
	</div>
{/if}

<style>
	.links {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-5);
		padding-block: var(--space-7) var(--space-8);
	}

	h2 {
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-5);
	}

	/* The group name is the breadcrumb: it says what kind of thing the row opens,
	   without repeating itself down every row of the list. */
	h3 {
		font-size: var(--text-xs);
		font-weight: var(--weight-medium);
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--ink-muted);
		margin-bottom: var(--space-2);
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-4);
	}

	li a {
		font-family: var(--font-mono);
		font-size: var(--text-sm);
	}
</style>
