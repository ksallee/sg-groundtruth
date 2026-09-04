<script>
	import { page } from '$app/state';
	import { NAME } from '$lib/site.js';
	import { visible } from '$lib/reading.svelte.js';

	// The whole navigation. The name is the way home. Two pages come first,
	// then five groups that open to list what they hold; the lists come from the
	// corpus at build time and grow with the reading level exactly as the index
	// pages do. Every entry carries a dot per level it has content at, named by
	// a tooltip on the dots, and the foot of the sidebar names the project the
	// overlay was read from.
	let { nav, projects = [], open = false, onclose } = $props();

	const path = $derived(page.url.pathname);
	const here = (href) => path === href || path.startsWith(href + '/');

	// The levels an entry has content at, of the ones the reading level shows:
	// one line per level, worded as the tooltip says it, and a project level
	// names each project. The dots are the distinct levels, so two projects
	// share one dot. An entry with none is not listed.
	function linesOf(e) {
		const out = [];
		if (e.hasApi) out.push({ level: 'api', word: 'API' });
		const locals = visible(e.locals ?? []);
		if (locals.some((l) => l.level === 'site')) out.push({ level: 'site', word: 'Site' });
		for (const p of projects) {
			if (locals.some((l) => l.level === 'project' && l.project === p.id)) {
				out.push({ level: 'project', word: p.label });
			}
		}
		return out;
	}
	const shown = (items) =>
		items
			.map((e) => {
				const lines = linesOf(e);
				return { ...e, lines, levels: [...new Set(lines.map((l) => l.level))] };
			})
			.filter((e) => e.lines.length);

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
	// The badge is one width for every verb, so the paths line up; DELETE is
	// the one word that would not fit it.
	const short = (verb) => (verb === 'DELETE' ? 'DEL' : verb);
	// A path stays on one line and truncates in the middle: its last TAIL
	// characters never give way and the rest ellipsizes from the right, since a
	// row is told apart by its tail.
	const TAIL = 8;

	const describe = (lines) => lines.map((l) => l.word).join(', ');

	// Every tooltip in the tree waits this long on a hover, so a pointer
	// crossing it raises nothing.
	const TIP_DELAY = 400;

	// A path the ellipsis has cut shows itself in full after that wait, in
	// place over the cut text and running past the sidebar's edge, which is
	// why it is fixed to the viewport rather than laid out in the row. It goes
	// the moment the pointer leaves or the tree scrolls.
	let full = $state(null);
	let timer;
	function reveal(row, path) {
		const stem = row.querySelector('.stem');
		if (!stem || stem.scrollWidth <= stem.clientWidth) return;
		timer = setTimeout(() => {
			const r = stem.getBoundingClientRect();
			full = { text: path, x: r.left, y: r.top + r.height / 2 };
		}, TIP_DELAY);
	}
	function conceal() {
		clearTimeout(timer);
		full = null;
	}
</script>

<aside class="sidebar" class:open aria-label="Site" style:--tip-delay="{TIP_DELAY}ms">
	<div class="head">
		<a class="mark" href="/">{NAME}</a>
		<button type="button" class="close" onclick={onclose} aria-label="Close menu">
			<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
				<path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.5" fill="none" />
			</svg>
		</button>
	</div>

	<nav aria-label="Sections" onscroll={conceal}>
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
								{@const name = e.title || e.name}
								{@const verb = verbOf(name)}
								{@const path = verb ? name.replace(VERB, '') : ''}
								<li>
									<a
										class="subitem"
										class:call={verb}
										href={e.href}
										aria-current={current(e.href) ? 'page' : undefined}
										onpointerenter={(ev) => reveal(ev.currentTarget, path)}
										onpointerleave={conceal}
									>
										{#if e.number}<span class="num">{e.number}</span>{/if}
										{#if verb}
											<span class="verb" data-verb={verb}>{short(verb)}</span>
											<span class="label mono"
												><span class="stem">{path.slice(0, -TAIL)}</span><span class="tail"
													>{path.slice(-TAIL)}</span
												></span
											>
										{:else}
											<span class="label">{name}</span>
										{/if}
										<span class="dots" role="img" aria-label={describe(e.lines)}>
											{#each e.levels as level (level)}
												<span class="dot" data-scope={level}></span>
											{/each}
											<span class="tip" aria-hidden="true">
												{#each e.lines as line (line.level + line.word)}
													<span class="line"><span class="dot" data-scope={line.level}></span>{line.word}</span>
												{/each}
											</span>
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

	{#if projects.length}
		<!-- The project the overlay was read from, nothing to choose: a page shows
		     every level it holds. -->
		<ul class="key" aria-label="Project">
			{#each projects as p (p.id)}
				<li><span class="keydot" data-scope="project"></span><span class="label">{p.label}</span></li>
			{/each}
		</ul>
	{/if}

	{#if full}
		<span class="full" style:left="{full.x}px" style:top="{full.y}px" aria-hidden="true">{full.text}</span>
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

	/* A row that opens with a badge sets it nearer the line the list hangs
	   from than a word would sit. */
	.subitem.call {
		padding-left: var(--space-1);
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

	/* A path is an API literal, set in mono at 12px, on one line. The stem
	   gives way and ellipsizes; the tail, the last TAIL characters, never does,
	   so `_upload/multipart` and `_upload/multipart_abort` stay two rows. */
	.label.mono {
		display: flex;
		font-family: var(--font-mono);
		font-size: 0.75rem;
	}

	.stem {
		flex: 0 1 auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.tail {
		flex: 0 0 auto;
		white-space: nowrap;
	}

	/* The verb, as every API reference draws it: a badge in the verb's colour,
	   one width for all so the paths line up, and the word in ink so the colour
	   is the badge's alone. */
	.verb {
		--verb: var(--verb-get);
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 1.125rem;
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--verb) 14%, transparent);
		color: var(--ink);
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		font-weight: var(--weight-medium);
		letter-spacing: 0.02em;
	}

	.verb[data-verb='POST'] {
		--verb: var(--verb-post);
	}

	.verb[data-verb='PUT'] {
		--verb: var(--verb-put);
	}

	.verb[data-verb='DELETE'] {
		--verb: var(--verb-delete);
	}

	.verb[data-verb='PATCH'] {
		--verb: var(--verb-patch);
	}

	/* The last dot is centred under the chevron; a second and a third run
	   leftwards from it. The slot is the full height of the row, so the tooltip
	   answers a pointer anywhere in it and not only on a dot. */
	.dots {
		position: relative;
		flex: 0 0 var(--slot);
		align-self: stretch;
		display: flex;
		align-items: center;
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

	/* The two tooltips share the copy button's look: black, 12px, a hairline of
	   ink. */
	.tip,
	.full {
		padding: 0.275rem var(--space-2);
		border-radius: var(--radius-sm);
		background: #000;
		border: var(--border) solid color-mix(in srgb, var(--ink) 10%, transparent);
		color: #fff;
		font-size: 0.75rem;
		line-height: 1.5;
		white-space: nowrap;
		pointer-events: none;
	}

	/* What the dots mean: one line per level, its dot and its word, to the
	   left of the slot. It waits --tip-delay before showing and goes at once
	   when the pointer leaves. */
	.tip {
		position: absolute;
		z-index: 1;
		right: calc(100% + var(--space-2));
		top: 50%;
		transform: translate(2px, -50%);
		display: grid;
		opacity: 0;
		transition:
			opacity 125ms var(--ease-out),
			transform 125ms var(--ease-out);
	}

	.dots:hover .tip {
		opacity: 1;
		transform: translate(0, -50%);
		transition-delay: var(--tip-delay);
	}

	.line {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	/* The full path sits over the cut one, its text starting where the cut
	   text starts. */
	.full {
		position: fixed;
		z-index: 40;
		transform: translate(calc(-1 * var(--space-2) - var(--border)), -50%);
		font-family: var(--font-mono);
		animation: reveal 125ms var(--ease-out);
	}

	@keyframes reveal {
		from {
			opacity: 0;
			translate: 2px 0;
		}
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
