<script>
	import { page } from '$app/state';
	import { NAME } from '$lib/site.js';
	import { reading, visible } from '$lib/reading.svelte.js';

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
		{
			id: 'entity-types',
			label: 'Entity types',
			href: '/entity-types',
			items: shown(nav.entityTypes)
		},
		{ id: 'field-types', label: 'Field types', href: '/field-types', items: shown(nav.fieldTypes) },
		{ id: 'endpoints', label: 'Endpoints', href: '/endpoints', items: shown(nav.endpoints) },
		{
			id: 'filters',
			label: 'Filters',
			href: '/filters',
			items: shown(nav.fieldTypes).map((e) => ({ ...e, href: `/filters#${e.slug}` }))
		},
		{ id: 'recipes', label: 'Recipes', href: '/recipes', items: shown(nav.recipes) },
		{ id: 'findings', label: 'Findings', href: '/findings', items: shown(nav.findings) },
		// Last, because a report is read after the finding behind it and never
		// instead of one.
		{ id: 'reports', label: 'Reports', href: '/reports', items: shown(nav.reports) }
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

	// One tooltip for the tree, above whatever asked for it. Fixed to the
	// viewport, so it can hang past the sidebar's edge and the scrolling nav
	// never clips it. It waits TIP_DELAY on a hover, so a pointer crossing the
	// tree raises nothing, and goes the moment the pointer leaves or the tree
	// scrolls. Two things ask for it, and one state means they never show at
	// once: the dots name their levels, centred above the dots; a path the
	// ellipsis has cut shows in full, its text starting above the cut text.
	const TIP_DELAY = 400;
	let tip = $state(null);
	let timer;
	function raise(build) {
		clearTimeout(timer);
		timer = setTimeout(() => (tip = build()), TIP_DELAY);
	}
	function lower() {
		clearTimeout(timer);
		tip = null;
	}
	function nameLevels(dots, lines) {
		raise(() => {
			// The dots themselves, not the row-tall slot around them.
			const ds = dots.querySelectorAll('.dot');
			const a = ds[0].getBoundingClientRect();
			const b = ds[ds.length - 1].getBoundingClientRect();
			return { lines, x: (a.left + b.right) / 2, y: a.top, centred: true };
		});
	}
	// A cut path in full, with its verb: two rows can share a path and differ
	// only by the verb, so the path alone does not say which row is being read.
	// The verb is spelled out here even though the badge abbreviates DELETE.
	// Aligned to the badge, not to the path, so the tooltip is the same line as
	// the row directly above it.
	function revealPath(label, text, verb) {
		const stem = label.querySelector('.stem');
		if (stem.scrollWidth <= stem.clientWidth) return;
		raise(() => {
			const badge = label.parentElement.querySelector('.verb');
			const r = (badge ?? stem).getBoundingClientRect();
			return { text, verb, x: r.left, y: r.top, centred: false };
		});
	}
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

	<nav aria-label="Sections" onscroll={lower}>
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
									>
										{#if e.number}<span class="num">{e.number}</span>{/if}
										{#if verb}
											<span class="verb">{short(verb)}</span>
											<!-- svelte-ignore a11y_no_static_element_interactions -->
											<span
												class="label mono"
												onpointerenter={(ev) => revealPath(ev.currentTarget, path, verb)}
												onpointerleave={lower}
												><span class="stem">{path.slice(0, -TAIL)}</span><span class="tail"
													>{path.slice(-TAIL)}</span
												></span
											>
										{:else}
											<span class="label">{name}</span>
										{/if}
										<span
											class="dots"
											role="img"
											aria-label={describe(e.lines)}
											onpointerenter={(ev) => nameLevels(ev.currentTarget, e.lines)}
											onpointerleave={lower}
										>
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

	{#if projects.length > 1}
		<!-- Several projects in the overlay, read one at a time. Everything
		     downstream reads `reading.project`, so choosing here filters the dots
		     beside every entry, the sections on an entry page and the counts. -->
		<p class="key">
			<span class="keydot" data-scope="project"></span>
			<select bind:value={reading.project} aria-label="Project">
				{#each projects as p (p.id)}
					<option value={p.id}>{p.label}</option>
				{/each}
			</select>
			<svg class="chev down" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
				<path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" fill="none" />
			</svg>
		</p>
	{:else if projects.length}
		<!-- One project: the name of the one the overlay was read from. -->
		<p class="key">
			<span class="keydot" data-scope="project"></span><span class="label">{projects[0].label}</span>
		</p>
	{/if}

	{#if tip}
		<span
			class="tip"
			class:centred={tip.centred}
			class:mono={tip.text}
			style:left="{tip.x}px"
			style:top="{tip.y}px"
			aria-hidden="true"
		>
			{#if tip.text}
				<span class="line"
					>{#if tip.verb}<span class="verb">{tip.verb}</span>{/if}{tip.text}</span
				>
			{:else}
				{#each tip.lines as line (line.level + line.word)}
					<span class="line"><span class="dot" data-scope={line.level}></span>{line.word}</span>
				{/each}
			{/if}
		</span>
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

	/* The verb: a neutral badge, one width for all so the paths line up, and
	   quieter than the path, so the scope dots keep the row's only colour. */
	.verb {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 1.125rem;
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--ink) 4%, transparent);
		color: var(--ink-muted);
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		font-weight: var(--weight-medium);
		letter-spacing: 0.02em;
	}

	/* The last dot is centred under the chevron; a second and a third run
	   leftwards from it. The slot is the full height of the row, so the tooltip
	   answers a pointer anywhere in it and not only on a dot. */
	.dots {
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

	/* The tooltip, in the copy button's look. It was #000 on a #111112 sidebar,
	   painted darker than its own ground, and read as a hole rather than a
	   layer. It is the lightest surface the theme has, with the strong rule for
	   an edge and the one drop shadow on the site to lift it.
	   Never set `color-scheme` here: it resolves light-dark() the other way and
	   hands back the black-on-black this replaced.
	   Its text starts above the text it names, --space-1 up, and it rises into
	   place. */
	.tip {
		position: fixed;
		z-index: 40;
		display: grid;
		padding: 0.275rem var(--space-2);
		border-radius: var(--radius-sm);
		background: var(--ground-sunken);
		border: var(--border) solid var(--rule-strong);
		box-shadow: var(--shadow-raised);
		color: var(--ink);
		font-size: 0.75rem;
		line-height: 1.5;
		white-space: nowrap;
		pointer-events: none;
		transform: translate(calc(-1 * var(--space-2) - var(--border)), calc(-100% - var(--space-2)));
		animation: rise 125ms var(--ease-out);
	}

	/* Centred above the dots. It may hang past the sidebar's edge, which is
	   what fixing it to the viewport is for. */
	.tip.centred {
		transform: translate(-50%, calc(-100% - var(--space-2)));
	}

	.tip.mono {
		font-family: var(--font-mono);
	}

	/* The row's badge is one fixed width so the paths line up under each other.
	   Here there is one line and the verb is spelled out, so it takes the width
	   of its own word. */
	.tip .verb {
		width: auto;
		height: auto;
		padding: 0 0.4em;
		margin-right: var(--space-2);
		background: color-mix(in srgb, var(--ink) 8%, transparent);
		color: var(--ink-muted);
	}

	.line {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	@keyframes rise {
		from {
			opacity: 0;
			translate: 0 2px;
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

	.key {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-width: 0;
		padding-bottom: var(--space-2);
	}

	/* The picker is the label, not a control drawn on top of one: the sidebar's
	   own type and colour, the chrome removed, and the full width so a long
	   project name has the room the static line had. */
	.key select {
		flex: 1 1 auto;
		min-width: 0;
		appearance: none;
		border: 0;
		padding: 0;
		background: none;
		color: inherit;
		font: inherit;
		cursor: pointer;
	}

	.key:has(select):hover {
		color: var(--ink);
	}

	/* The group chevron, turned to point down: the same mark the tree uses for
	   a thing that opens, so the picker reads as one. */
	.chev.down {
		flex: 0 0 auto;
		transform: rotate(90deg);
	}

	.key select:focus-visible {
		outline: var(--border) solid var(--rule-strong);
		outline-offset: var(--space-1);
		border-radius: var(--radius-sm);
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
