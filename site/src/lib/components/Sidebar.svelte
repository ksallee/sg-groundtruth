<script>
	import { page } from '$app/state';
	import { NAME } from '$lib/site.js';
	import ReadingLevel from './ReadingLevel.svelte';
	import { visible } from '$lib/reading.svelte.js';

	// The whole navigation. Two plain pages, Intro and How it works, and five
	// groups that open to list what they hold. The lists come from the corpus at
	// build time and grow with the reading level exactly as the index pages do.
	// The name at the top is the way home.
	let { nav, hasOverlay = false, hasSite = false, projects = [], open = false, onclose } = $props();

	const path = $derived(page.url.pathname);
	const here = (href) => path === href || path.startsWith(href + '/');

	// A subject exists at this level if it has an API card, or a local card the
	// level shows. Nothing is hidden as the level rises; subjects are added.
	const shown = (items) => items.filter((e) => e.hasApi || visible(e.locals ?? []).length);

	// Filters has one section per data type, so its list is the field types
	// again, pointing at the anchors.
	const groups = $derived([
		{ id: 'field-types', label: 'Field types', href: '/field-types', items: shown(nav.fieldTypes) },
		{
			id: 'entity-types',
			label: 'Entity types',
			href: '/entity-types',
			items: shown(nav.entityTypes)
		},
		{
			id: 'filters',
			label: 'Filters',
			href: '/filters',
			items: shown(nav.fieldTypes).map((e) => ({ ...e, href: `/filters#${e.slug}` }))
		},
		{ id: 'recipes', label: 'Recipes', href: '/recipes', items: shown(nav.recipes) },
		{ id: 'findings', label: 'Findings', href: '/findings', items: shown(nav.findings) }
	]);

	// A group opens and closes by hand, any number at once, and stays as the
	// reader left it across navigations. The group the reader is inside opens on
	// its own; nothing ever closes on its own.
	let expanded = $state({});
	$effect(() => {
		for (const g of groups) if (here(g.href)) expanded[g.id] = true;
	});
	const isOpen = (g) => Boolean(expanded[g.id]);
	const toggle = (g) => (expanded[g.id] = !expanded[g.id]);

	const current = (href) =>
		href.includes('#') ? path + page.url.hash === href : path === href;

	// A field type, or an entity type with no display title, is the API's own
	// literal, and is set in mono.
	const mono = (g, e) => g.id !== 'recipes' && g.id !== 'findings' && !e.title;
</script>

<aside class="sidebar" class:open aria-label="Site">
	<div class="head">
		<a class="mark" href="/">{NAME}</a>
		<button type="button" class="close" onclick={onclose} aria-label="Close menu">
			<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
				<path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.5" fill="none" />
			</svg>
		</button>
	</div>

	<nav aria-label="Sections">
		<ul class="menu">
			<li>
				<a class="item" href="/" aria-current={path === '/' ? 'page' : undefined}>Intro</a>
			</li>

			{#each groups as g (g.id)}
				<li class="group" class:here={here(g.href)} class:is-open={isOpen(g)}>
					<button
						type="button"
						class="item toggle"
						aria-expanded={isOpen(g)}
						aria-controls="sub-{g.id}"
						onclick={() => toggle(g)}
					>
						<span>{g.label}</span>
						<svg class="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
							<path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" fill="none" />
						</svg>
					</button>
					{#if isOpen(g)}
						<ul class="sub" id="sub-{g.id}">
							{#each g.items as e (e.slug)}
								<li>
									<a
										class="subitem"
										class:mono={mono(g, e)}
										href={e.href}
										aria-current={current(e.href) ? 'page' : undefined}
									>
										{#if e.number}<span class="num">{e.number}</span>{/if}
										<span>{e.title || e.name}</span>
									</a>
								</li>
							{/each}
						</ul>
					{/if}
				</li>
			{/each}

			<li>
				<a class="item" href="/how-it-works" aria-current={here('/how-it-works') ? 'page' : undefined}
					>How it works</a
				>
			</li>
		</ul>
	</nav>

	{#if hasOverlay}
		<div class="foot">
			<p class="foot-label">Reading level</p>
			<ReadingLevel {hasSite} {projects} />
		</div>
	{/if}
</aside>

<style>
	.sidebar {
		position: sticky;
		top: 0;
		height: 100dvh;
		overflow: hidden;
		background: var(--sidebar);
		border-right: var(--border) solid var(--rule);
		padding: var(--space-4) var(--space-3);
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		font-size: var(--text-sm);
		line-height: 1.6;
	}

	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
		min-height: 2rem;
		padding-inline: var(--space-2);
	}

	.mark {
		font-weight: var(--weight-bold);
		color: var(--ink);
		text-decoration: none;
	}

	.close {
		display: none;
		border: 0;
		background: none;
		color: var(--ink-muted);
		padding: var(--space-1);
		border-radius: var(--radius-sm);
		place-items: center;
	}

	.close:hover {
		color: var(--ink);
		background: var(--sidebar-hover);
	}

	/* The tree scrolls on its own. The name above it and the reading level below
	   it stay put. */
	nav {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		scrollbar-width: thin;
	}

	.menu,
	.sub {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 2px;
	}

	.item {
		display: block;
		width: 100%;
		padding: var(--space-1) var(--space-2);
		border-radius: 6px;
		color: var(--ink-body);
		text-decoration: none;
		transition:
			background var(--duration) ease,
			color var(--duration) ease;
	}

	.item:hover {
		background: var(--sidebar-hover);
		color: var(--ink);
	}

	/* A group is a button, not a link: it opens, it never navigates. */
	.toggle {
		font: inherit;
		text-align: left;
		border: 0;
		background: none;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
	}

	.group.here > .toggle {
		color: var(--ink);
		font-weight: var(--weight-medium);
	}

	.item[aria-current] {
		background: var(--sidebar-active);
		color: var(--ink);
		font-weight: var(--weight-medium);
	}

	.chev {
		flex: 0 0 auto;
		color: var(--ink-muted);
		transition: transform var(--duration) var(--ease-out);
	}

	.is-open .chev {
		transform: rotate(90deg);
	}

	.sub {
		margin: 2px 0 var(--space-2) var(--space-3);
		padding-left: var(--space-3);
		border-left: var(--border) solid var(--rule);
	}

	.subitem {
		display: flex;
		gap: var(--space-2);
		align-items: baseline;
		padding: 0.2rem var(--space-2);
		border-radius: 6px;
		font-size: var(--text-xs);
		color: var(--ink-body);
		text-decoration: none;
		transition:
			background var(--duration) ease,
			color var(--duration) ease;
	}

	.subitem.mono {
		font-family: var(--font-mono);
		letter-spacing: 0;
	}

	.subitem:hover {
		background: var(--sidebar-hover);
		color: var(--ink);
	}

	.subitem[aria-current] {
		background: var(--sidebar-active);
		color: var(--ink);
	}

	.num {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.foot {
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-4);
		display: grid;
		gap: var(--space-2);
	}

	.foot-label {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
		padding-inline: var(--space-2);
	}

	/* Below the desktop width the sidebar is a drawer, opened from the top bar
	   and closed by its own button, the backdrop, Escape or a navigation. */
	@media (max-width: 63.99rem) {
		.sidebar {
			position: fixed;
			inset: 0 auto 0 0;
			width: min(var(--sidebar-width), 85vw);
			z-index: 30;
			transform: translateX(-100%);
			transition: transform var(--duration) var(--ease-out);
		}

		.sidebar.open {
			transform: none;
		}

		.close {
			display: grid;
		}
	}
</style>
