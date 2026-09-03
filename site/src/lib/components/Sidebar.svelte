<script>
	import { page } from '$app/state';
	import { afterNavigate } from '$app/navigation';
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

	// A group is open while the reader is inside it. A reader can open or close
	// any group by hand; that choice lasts until the next navigation.
	let toggled = $state({});
	const isOpen = (g) => toggled[g.id] ?? here(g.href);
	const toggle = (g) => (toggled[g.id] = !isOpen(g));
	afterNavigate(() => (toggled = {}));

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
					<div class="row">
						<a class="item" href={g.href} aria-current={path === g.href ? 'page' : undefined}
							>{g.label}</a
						>
						<button
							type="button"
							class="chev"
							aria-expanded={isOpen(g)}
							aria-controls="sub-{g.id}"
							aria-label="{isOpen(g) ? 'Collapse' : 'Expand'} {g.label}"
							onclick={() => toggle(g)}
						>
							<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
								<path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" fill="none" />
							</svg>
						</button>
					</div>
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
		overflow-y: auto;
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

	nav {
		flex: 1;
	}

	.menu,
	.sub {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 2px;
	}

	.row {
		display: flex;
		align-items: stretch;
		gap: 2px;
	}

	.item {
		flex: 1;
		display: block;
		padding: var(--space-1) var(--space-2);
		border-radius: 6px;
		color: var(--ink-body);
		text-decoration: none;
		transition:
			background var(--duration) ease,
			color var(--duration) ease;
	}

	.item:hover,
	.chev:hover {
		background: var(--sidebar-hover);
		color: var(--ink);
	}

	.group.here > .row > .item {
		color: var(--ink);
		font-weight: var(--weight-medium);
	}

	.item[aria-current] {
		background: var(--sidebar-active);
		color: var(--ink);
		font-weight: var(--weight-medium);
	}

	.chev {
		flex: 0 0 1.75rem;
		border: 0;
		background: none;
		color: var(--ink-muted);
		border-radius: 6px;
		display: grid;
		place-items: center;
	}

	.chev svg {
		transition: transform var(--duration) var(--ease-out);
	}

	.is-open .chev svg {
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
