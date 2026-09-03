<script>
	import { page } from '$app/state';
	import { NAME } from '$lib/site.js';
	import ReadingLevel from './ReadingLevel.svelte';
	import { visible } from '$lib/reading.svelte.js';

	// The whole navigation. The name is the way home. Two pages come first,
	// then five groups that open to list what they hold; the lists come from the
	// corpus at build time and grow with the reading level exactly as the index
	// pages do. Every entry carries a dot per level it has content at.
	let { nav, hasOverlay = false, hasSite = false, projects = [], open = false, onclose } = $props();

	const path = $derived(page.url.pathname);
	const here = (href) => path === href || path.startsWith(href + '/');

	// The levels an entry has content at, of the ones the reading level shows.
	// An entry with none is not listed.
	function levelsOf(e) {
		const out = [];
		if (e.hasApi) out.push('api');
		const locals = visible(e.locals ?? []);
		if (locals.some((l) => l.level === 'site')) out.push('site');
		if (locals.some((l) => l.level === 'project')) out.push('project');
		return out;
	}
	const shown = (items) =>
		items.map((e) => ({ ...e, levels: levelsOf(e) })).filter((e) => e.levels.length);

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

	const WORD = { api: 'API', site: 'Site', project: 'Project' };
	const describe = (levels) => levels.map((l) => WORD[l]).join(', ');
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
			<li>
				<a class="item" href="/how-it-works" aria-current={here('/how-it-works') ? 'page' : undefined}
					>How it works</a
				>
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
						<span class="label">{g.label}</span>
						<span class="slot">
							<svg class="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
								<path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" fill="none" />
							</svg>
						</span>
					</button>
					{#if isOpen(g)}
						<ul class="sub" id="sub-{g.id}">
							{#each g.items as e (e.slug)}
								<li>
									<a class="subitem" href={e.href} aria-current={current(e.href) ? 'page' : undefined}>
										{#if e.number}<span class="num">{e.number}</span>{/if}
										<span class="label">{e.title || e.name}</span>
										<span class="dots" role="img" aria-label={describe(e.levels)}>
											{#each e.levels as level (level)}
												<span class="dot" data-scope={level}></span>
											{/each}
										</span>
									</a>
								</li>
							{/each}
						</ul>
					{/if}
				</li>
			{/each}
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
		padding: var(--space-4) var(--space-3);
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		font-size: var(--text-menu);
		line-height: 1.6;
		letter-spacing: var(--tracking-body);
		/* The column at the right of every row: room for three dots, flush right,
		   with the chevron centred over the last one so a single dot sits exactly
		   under it and more dots run leftwards. */
		--slot: 30px;
		--dot: 6px;
		--dot-gap: 4px;
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
		font-size: var(--text-sm);
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
	   it stay put. The scrollbar is a thin thumb that appears on hover, in place
	   of the browser's own. */
	nav {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
		scrollbar-width: thin;
		scrollbar-color: transparent transparent;
		padding-right: var(--space-1);
	}

	nav:hover,
	nav:focus-within {
		scrollbar-color: var(--rule-strong) transparent;
	}

	nav::-webkit-scrollbar {
		width: 6px;
	}

	nav::-webkit-scrollbar-track {
		background: transparent;
	}

	nav::-webkit-scrollbar-thumb {
		background: transparent;
		border-radius: 999px;
	}

	nav:hover::-webkit-scrollbar-thumb,
	nav:focus-within::-webkit-scrollbar-thumb {
		background: var(--rule-strong);
	}

	/* One track the width of the sidebar, never the width of the widest label,
	   so a long entry truncates instead of pushing the tree sideways. */
	.menu,
	.sub {
		list-style: none;
		padding: 0;
		display: grid;
		grid-template-columns: var(--col);
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
		letter-spacing: inherit;
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
	}

	.item[aria-current] {
		background: var(--sidebar-active);
		color: var(--ink);
	}

	.slot {
		flex: 0 0 var(--slot);
		display: flex;
		justify-content: flex-end;
	}

	.chev {
		display: block;
		color: var(--ink-muted);
		transition: transform var(--duration) var(--ease-out);
	}

	.is-open .chev {
		transform: rotate(90deg);
	}

	/* The open list hangs from a faint line, a whisper of the ink. */
	.sub {
		margin: 2px 0 var(--space-2) var(--space-3);
		padding-left: var(--space-2);
		border-left: var(--border) solid color-mix(in srgb, var(--ink) 5%, transparent);
	}

	/* One line per entry. The label gives way; the number and the dots do not. */
	.subitem {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
		padding: 0.2rem var(--space-2);
		border-radius: 6px;
		color: var(--ink-body);
		text-decoration: none;
		transition:
			background var(--duration) ease,
			color var(--duration) ease;
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
		flex: 0 0 auto;
		color: var(--ink-muted);
		font-variant-numeric: tabular-nums;
	}

	.label {
		flex: 1 1 auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* The last dot is centred under the chevron; a second and a third run
	   leftwards from it. */
	.dots {
		flex: 0 0 var(--slot);
		display: flex;
		justify-content: flex-end;
		gap: var(--dot-gap);
		padding-right: calc((14px - var(--dot)) / 2);
	}

	.dot {
		width: var(--dot);
		height: var(--dot);
		border-radius: 50%;
		background: var(--scope-ink);
	}

	.foot {
		border-top: var(--border) solid var(--rule);
		padding-top: var(--space-4);
		display: grid;
		gap: var(--space-2);
	}

	.foot-label {
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
			box-shadow: 0 0 0 var(--border) var(--rule);
		}

		.sidebar.open {
			transform: none;
		}

		.close {
			display: grid;
		}
	}
</style>
