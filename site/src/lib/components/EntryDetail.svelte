<script>
	import Prose from './Prose.svelte';
	import ScopeSection from './ScopeSection.svelte';
	import Breadcrumb from './Breadcrumb.svelte';
	import { REPO } from '$lib/site.js';
	import { visible } from '$lib/reading.svelte.js';

	// One subject, rendered in full and in one order: what the API does, then
	// what one site configures, then what one project does. Each is a section
	// under its badge. A subject the published corpus has no card for renders
	// the local sections alone.
	//
	// `section` is the group the entry belongs to, for the breadcrumb.
	let { entry, section } = $props();

	const locals = $derived(visible(entry.locals ?? []));

	// The header describes the subject with the API card's line. Without one,
	// each local section carries its own verdict and the header carries none.
	const tags = $derived(entry.hasApi ? entry.tags : (locals[0]?.tags ?? []));

	// One directory per group, mirroring corpus/. Kept as a lookup rather than a
	// chain of ternaries so a new group is one line.
	const SOURCE_DIR = {
		recipes: 'corpus/recipes',
		field_types: 'corpus/findings/field_types',
		entity_types: 'corpus/findings/entity_types',
		findings: 'corpus/findings'
	};

	const sourcePath = $derived(`${SOURCE_DIR[entry.group] ?? 'corpus/findings'}/${entry.slug}.md`);

	// A field type, or an entity type with no display title, is named by the
	// API's own literal, so the heading is set in mono, exactly as the API
	// spells it. The number is in the breadcrumb, so the heading is the name.
	const literal = $derived(
		!entry.title && (entry.group === 'field_types' || entry.group === 'entity_types')
	);
	const heading = $derived(entry.title || entry.name || entry.fullName.replace(/^\d+\s+/, ''));

	// Every section on the page, in order. With one section there is nothing to
	// tell apart, so no badge and no switch is drawn.
	const anchor = (l) => (l.level === 'site' ? 'scope-site' : `scope-project-${l.project}`);
	const sections = $derived([
		...(entry.hasApi ? [{ id: 'scope-api', level: 'api', label: 'API' }] : []),
		...locals.map((l) => ({
			id: anchor(l),
			level: l.level,
			label: l.level === 'site' ? 'Site' : l.projectLabel || 'Project'
		}))
	]);
	const several = $derived(sections.length > 1);

	// The switch follows the scroll: the active section is the last one whose
	// top has passed the switch.
	let active = $state('');
	$effect(() => {
		if (!several) return;
		const ids = sections.map((s) => s.id);
		const update = () => {
			let cur = ids[0];
			for (const id of ids) {
				const el = document.getElementById(id);
				if (el && el.getBoundingClientRect().top <= 96) cur = id;
			}
			active = cur;
		};
		update();
		addEventListener('scroll', update, { passive: true });
		return () => removeEventListener('scroll', update);
	});

	function jump(id) {
		document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
</script>

<article class="col entry">
	{#if several}
		<div class="jump" role="group" aria-label="Sections on this page">
			{#each sections as s (s.id)}
				<button
					type="button"
					data-scope={s.level}
					aria-pressed={active === s.id}
					onclick={() => jump(s.id)}>{s.label}</button
				>
			{/each}
		</div>
	{/if}

	<header>
		<div class="crumbs">
			<Breadcrumb trail={[section, { label: entry.title || entry.fullName }]} />
		</div>
		<h1 class:literal>{heading}</h1>
		<!-- Kept in view rather than replaced: a reader who cannot see the schema
		     name cannot call anything. -->
		{#if entry.title && entry.title !== entry.slug}
			<p class="slug"><code>{entry.slug}</code></p>
		{/if}

		{#if entry.hasApi}
			<p class="verdict">{entry.verdict}</p>
		{:else if locals.length}
			<p class="absent">
				The published corpus has no entry for this. Everything below was measured locally.
			</p>
		{:else}
			<p class="absent">This was measured on one site rather than read off the API.</p>
		{/if}

		<ul class="meta">
			{#each tags as tag (tag)}
				<li class="tag">{tag}</li>
			{/each}
			{#if entry.hasApi}
				<li class="src"><a href="{REPO}/blob/main/{sourcePath}">Source markdown</a></li>
			{/if}
		</ul>
	</header>

	{#if entry.hasApi}
		<ScopeSection level="api" id="scope-api" badge={several}>
			<Prose html={entry.html} />
		</ScopeSection>
	{/if}

	{#each locals as local (local.level + local.project + local.slug)}
		<ScopeSection level={local.level} project={local.projectLabel} id={anchor(local)} badge={several}>
			<p class="local-verdict">{local.verdict}</p>
			<Prose html={local.html} tone={local.level} />
		</ScopeSection>
	{/each}
</article>

<style>
	.entry {
		padding-block: var(--space-7) 0;
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-6);
	}

	/* Top right, and it stays there while the page scrolls. It sits on the
	   breadcrumb's line: the row it occupies is pulled back out of the flow. */
	.jump {
		position: sticky;
		top: var(--space-3);
		z-index: 5;
		justify-self: end;
		display: flex;
		gap: 2px;
		padding: 2px;
		background: var(--ground);
		border: var(--border) solid var(--rule);
		border-radius: var(--radius-pill);
		margin-bottom: calc(-1 * (1.75rem + var(--space-6)));
	}

	.jump button {
		font: inherit;
		font-size: var(--text-xs);
		line-height: 1.6;
		letter-spacing: 0;
		border: 0;
		background: none;
		color: var(--ink-muted);
		padding: 0.1rem 0.7rem;
		border-radius: var(--radius-pill);
		transition:
			background var(--duration) ease,
			color var(--duration) ease;
	}

	.jump button:hover {
		color: var(--ink);
	}

	.jump button[aria-pressed='true'] {
		background: var(--scope-quiet);
		color: var(--scope-ink);
	}

	header {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--space-3);
		padding-bottom: var(--space-6);
		border-bottom: var(--border) solid var(--rule);
	}

	/* Leaves the right of its line to the switch. */
	.crumbs {
		max-width: 62%;
	}

	h1.literal {
		font-family: var(--font-mono);
		font-weight: var(--weight-medium);
		letter-spacing: 0;
	}

	.slug code {
		font-size: var(--text-sm);
		color: var(--ink-muted);
		background: none;
		padding: 0;
	}

	/* The verdict is the entry's whole argument in one line. It is set as the
	   page's lede, in the full ink, and nothing else on the page is boxed or
	   ruled to compete with it. */
	.verdict,
	.local-verdict {
		font-size: var(--text-lede);
		line-height: 1.5;
		color: var(--ink);
	}

	.verdict {
		margin-top: var(--space-1);
	}

	.absent {
		font-size: var(--text-sm);
		color: var(--ink-muted);
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

	.tag::before {
		content: '#';
		opacity: 0.6;
	}

	.src {
		margin-left: auto;
	}

	.src a {
		color: var(--ink-muted);
	}

	.src a:hover {
		color: var(--ink);
	}
</style>
