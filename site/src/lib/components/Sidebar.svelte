<script>
	import { page } from '$app/state';
	import { NAME } from '$lib/site.js';
	import { visible } from '$lib/reading.svelte.js';

	// The whole navigation. The name is the way home. Two pages come first,
	// then five groups that open to list what they hold; the lists come from the
	// corpus at build time and grow with the reading level exactly as the index
	// pages do. Every entry carries a dot per level it has content at, and the
	// foot of the sidebar is the key to the colours.
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
		{ id: 'endpoints', label: 'Endpoints', href: '/endpoints', items: shown(nav.endpoints) },
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

	// An endpoint card is named by its call, `POST /entity/_batch`. The verb is a
	// badge and the path is the label, which is the shape every API reference
	// uses and the only thing keeping four rows that end in `/fields/<field>`
	// apart from one another.
	const VERB = /^(GET|POST|PUT|DELETE|PATCH)\s+/;
	const verbOf = (name) => (VERB.exec(name) ?? [])[1] ?? '';
	// A path has no spaces, so a wrap breaks wherever it runs out of room and
	// `/follow` becomes `follo` and `w`. A zero-width space after each separator
	// offers the line breaker somewhere better; `overflow-wrap` still catches a
	// single segment too long for the column.
	const pathOf = (name) => name.replace(VERB, '').replace(/([/.])/g, '$1\u200B');

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
										{#if verbOf(e.title || e.name)}
											<span class="verb" data-verb={verbOf(e.title || e.name)}
												>{verbOf(e.title || e.name)}</span
											>
											<span class="label mono">{pathOf(e.title || e.name)}</span>
										{:else}
											<span class="label">{e.title || e.name}</span>
										{/if}
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
		<!-- A key to the colours, nothing to choose: a page shows every level it
		     holds. -->
		<ul class="key" aria-label="Colours">
			<li><span class="keydot" data-scope="api"></span>API</li>
			{#if hasSite}
				<li><span class="keydot" data-scope="site"></span>Site</li>
			{/if}
			{#each projects as p (p.id)}
				<li><span class="keydot" data-scope="project"></span><span class="label">{p.label}</span></li>
			{/each}
		</ul>
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
		margin-top: var(--space-5);
		overflow-y: auto;
		overflow-x: hidden;
		scrollbar-width: thin;
		scrollbar-color: transparent transparent;
		padding-right: var(--space-1);
		/* Room for the last entry to scroll clear of the fade over the key. */
		padding-bottom: var(--key-fade);
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

	/* A path is an API literal, so it is set in mono at 12px. Most sit on one line
	   at this width. The eleven that do not, `/entity/<type>/<id>/<field>/_upload/
	   multipart_abort` among them, wrap onto a second rather than truncate: an
	   endpoint is told apart by its tail, so an ellipsis on the right turns
	   `_upload/multipart` and `_upload/multipart_abort` into the same row. Fitting
	   the longest on one line needs a 32rem sidebar, which is more than a third of
	   the viewport for navigation. */
	.label.mono {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		white-space: normal;
		overflow: visible;
		overflow-wrap: anywhere;
	}

	/* The verb, as every API reference draws it: short, uppercase, in its own
	   colour, and never competing with the path for width. */
	.verb {
		flex: 0 0 auto;
		width: 2.75rem;
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		font-weight: var(--weight-medium);
		letter-spacing: 0.02em;
		text-align: right;
		color: var(--verb-get);
	}

	.verb[data-verb='POST'] {
		color: var(--verb-post);
	}

	.verb[data-verb='PUT'] {
		color: var(--verb-put);
	}

	.verb[data-verb='DELETE'] {
		color: var(--verb-delete);
	}

	.verb[data-verb='PATCH'] {
		color: var(--verb-patch);
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

	/* The key sits on the page colour with no rule above it. Instead a fade
	   rises from it over the foot of the tree, so entries scrolling under it
	   dissolve: nothing --key-fade above the key, page colour at the key. */
	.key {
		position: relative;
		list-style: none;
		padding: var(--space-2) var(--space-2) 0;
		margin: 0;
		background: var(--sidebar);
		display: grid;
		gap: var(--space-1);
		color: var(--ink-muted);
	}

	.key::before {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 100%;
		height: var(--key-fade);
		background: linear-gradient(to top, var(--sidebar) 0, transparent 100%);
		pointer-events: none;
	}

	.key li {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
	}

	.keydot {
		flex: 0 0 auto;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--scope-ink);
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
