<script>
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import Prose from '$lib/components/Prose.svelte';
	import ScopeSection from '$lib/components/ScopeSection.svelte';
	import { REPO } from '$lib/site.js';

	// One door, rendered from the generated file and nothing else. A door is
	// built from the shipped corpus alone, so it is the `api` level whatever the
	// reading level on an entry page says, and it carries the badge that says so.
	let { data } = $props();

	const door = $derived(data.door);
	const kb = (bytes) => Math.round(bytes / 1024);
</script>

<svelte:head>
	<title>{door.title}: a door into the Flow PT corpus</title>
	<meta name="description" content={door.blurb} />
</svelte:head>

<article class="col page">
	<header>
		<Breadcrumb trail={[{ label: 'Doors', href: '/doors' }, { label: door.title }]} />
		<h1 class:literal={door.literal}>{door.title}</h1>
		<div class="lede">{@html door.blurbHtml}</div>
		<ul class="meta">
			<li>{kb(door.bytes)} KB</li>
			<!-- The same file twice: this URL for a client that wants the bytes,
			     the repository for a person who wants the generator beside them. -->
			<li class="src"><a href={door.md}>Markdown</a></li>
			<li class="src"><a href="{REPO}/blob/main/{door.source}">Source</a></li>
		</ul>
	</header>

	<ScopeSection level="api">
		<Prose html={door.html} />
	</ScopeSection>
</article>

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
		padding-bottom: var(--space-6);
		border-bottom: var(--border) solid var(--rule);
	}

	h1.literal {
		font-family: var(--font-mono);
		font-weight: var(--weight-medium);
		letter-spacing: 0;
	}

	.lede {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}

	.lede :global(p) {
		margin: 0;
	}

	.meta {
		list-style: none;
		padding: 0;
		margin-top: var(--space-2);
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-2) var(--space-3);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.src {
		margin-left: auto;
	}

	.src + .src {
		margin-left: 0;
	}

	.src a {
		color: var(--ink-muted);
	}

	.src a:hover {
		color: var(--ink);
	}
</style>
