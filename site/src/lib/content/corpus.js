// Content plumbing. Reads markdown off disk at build time, parses the frontmatter
// the corpus already carries, renders the body to HTML, and merges the optional
// local overlay into the shipped corpus.
//
// Server-only: imported from `+page.server.js`, never from a component. Under
// `npm run build` every page is prerendered, so this runs once and the deployed
// site is static HTML.
//
// Design surface is `src/lib/tokens.css` and the components. This file is not.

import fs from 'node:fs';
import path from 'node:path';
import { marked } from 'marked';
import { SHIPPED, SITE, GROUPS, projectSources } from './sources.js';
import { filterCards, filterMatrix } from './filters.js';

// --- frontmatter -----------------------------------------------------------
// The corpus writes a fixed, flat block: `tags: [a, b]`, `scope:`, `verdict:`,
// `intent:`, `project:`. One key per line, values never wrap. A full YAML parser
// would be a dependency for five keys.

function parseFrontmatter(raw) {
	const m = /^---\n([\s\S]*?)\n---\n?/.exec(raw);
	if (!m) return { meta: {}, body: raw };

	const meta = {};
	for (const line of m[1].split('\n')) {
		const sep = line.indexOf(':');
		if (sep === -1) continue;
		const key = line.slice(0, sep).trim();
		const value = line.slice(sep + 1).trim();
		meta[key] = /^\[.*\]$/.test(value)
			? value
					.slice(1, -1)
					.split(',')
					.map((t) => t.trim())
					.filter(Boolean)
			: value;
	}
	return { meta, body: raw.slice(m[0].length) };
}

// --- markdown --------------------------------------------------------------

marked.setOptions({ gfm: true, breaks: false });

// The reference tables are wide by nature: one row per input, one column per
// outcome. Each gets its own scroll container so a phone scrolls the table and
// not the page. Done on the rendered string rather than through a renderer
// override, which changes shape between marked majors.
function wrapTables(html) {
	return html
		.replace(/<table>/g, '<div class="scroll-x" tabindex="0"><table>')
		.replace(/<\/table>/g, '</table></div>');
}

// The filter matrix is the one table on the site whose columns are a contract:
// `probes/check_corpus.py` fails a field-type card whose **Filter** table is not
// headed | operator | value | matches |. Marking it here lets the stylesheet give
// the first two columns a floor, because `matches` is prose and on `date_time` it
// runs 155 characters against a 17-character operator, taking the width with it.
function markMatrix(html) {
	return html.replace(
		/<table>\s*<thead>\s*<tr>\s*<th>operator<\/th>\s*<th>value<\/th>\s*<th>matches<\/th>/g,
		'<table class="matrix"><thead><tr><th>operator</th><th>value</th><th>matches</th>'
	);
}

// The page renders its own <h1> from the entry name, so drop the body's.
function stripLeadingH1(body) {
	return body.replace(/^\s*#\s+.*\n+/, '');
}

// wrapTables first: it matches a bare `<table>`, so marking the matrix before it
// runs leaves that one table outside its own scroll container, and a table that
// outgrows the column then widens the page instead of scrolling inside it.
function render(body) {
	return markMatrix(wrapTables(marked.parse(stripLeadingH1(body))));
}

// --- reading ---------------------------------------------------------------

// An endpoint card ends in a list of backticked corpus paths. They are pulled
// out and rendered as real links beside the ones the `endpoints:` join produces,
// so the card body never holds a second, differently-shaped link list.
function splitLinks(body) {
	const at = body.indexOf('**Links**');
	if (at === -1) return { body, links: [] };
	return {
		body: body.slice(0, at),
		links: [...body.slice(at).matchAll(/^-\s+`([^`]+)`\s*$/gm)].map((m) => m[1])
	};
}

function readGroup(source, group) {
	const dir = path.join(source.root, group.dir);
	if (!fs.existsSync(dir)) return [];

	return fs
		.readdirSync(dir)
		.filter((f) => f.endsWith('.md') && f !== 'README.md')
		.sort()
		.map((file) => {
			const slug = file.replace(/\.md$/, '');
			const { meta, body } = parseFrontmatter(fs.readFileSync(path.join(dir, file), 'utf8'));
			const split = group.id === 'endpoints' ? splitLinks(body) : { body, links: [] };
			return {
				slug,
				group: group.id,
				level: source.level,
				project: source.project,
				projectName: meta.project ?? '',
				scope: meta.scope ?? '',
				// What a person calls this. `CustomEntity19` is what a client
				// addresses; `Lenses` is what someone recognises. Absent on every
				// shipped card, which is why the slug is still the fallback.
				// An endpoint card is titled by the call, which is its identity. The
				// slug under it is a filename and nothing addresses it.
				title: meta.title ?? meta.endpoint ?? '',
				endpoint: meta.endpoint ?? '',
				// `verdict` on a finding, `intent` on a recipe. One line either way.
				verdict: meta.verdict ?? meta.intent ?? '',
				tags: Array.isArray(meta.tags) ? meta.tags : [],
				// The phase of a session a finding bites in, and the calls it
				// covers. Both are retrieval keys rather than content: /findings
				// groups by the first, /endpoints is built out of the second.
				phase: meta.phase ?? '',
				endpoints: Array.isArray(meta.endpoints) ? meta.endpoints : [],
				name: displayName(slug, group.id),
				// With the number, for a page title and a heading. The list shows
				// the number in its own column, so it uses `name` and `number`.
				fullName: [numberOf(slug), displayName(slug, group.id)].filter(Boolean).join(' '),
				number: numberOf(slug),
				href: `${group.base}/${slug}`,
				html: render(split.body),
				cardLinks: split.links,
				// The markdown as written. /filters reads the operator vocabulary
				// and the value matrix back out of it. Stripped before anything
				// reaches a page, so it never doubles a payload.
				raw: body
			};
		})
		.filter((entry) => {
			// The scope filter is the whole public/local boundary. A shipped entry
			// that measures one site (005, 007) is not published; an overlay entry
			// that forgot its scope is not silently treated as general.
			if (entry.scope !== source.scope) {
				warn(source, group, entry.slug, `needs \`scope: ${source.scope}\`, found \`${entry.scope || 'nothing'}\``);
				return false;
			}
			// The same key `probes/check_corpus.py` requires, for the same reason:
			// a project measurement that does not name its project cannot be read.
			if (source.level === 'project' && !entry.projectName) {
				warn(source, group, entry.slug, 'needs a `project:` key naming which project it was measured on');
				return false;
			}
			return true;
		});
}

function warn(source, group, slug, reason) {
	if (source.id === SHIPPED.id) return;
	console.warn(`[corpus] skipped ${source.root}/${group.dir}/${slug}.md: ${reason}`);
}

function numberOf(slug) {
	const m = /^(\d+)_/.exec(slug);
	return m ? m[1] : null;
}

// `003_query` reads as `query` next to its own number. `multi_entity` and
// `PublishedFile` are the API's own literals, a `data_type` and a schema name,
// and are left exactly as the API spells them. Case included: the entity-type
// slug is the string the API answers to, so it is not lowercased for the URL.
function displayName(slug, groupId) {
	if (groupId === 'field_types' || groupId === 'entity_types') return slug;
	return slug.replace(/^\d+_/, '').replace(/_/g, ' ');
}


// --- subjects ---------------------------------------------------------------
// A subject is one thing the corpus documents: a group and a slug. It carries
// an API card, or local cards, or both. `009_status_lists` is all three at once
// on a site with two projects.
//
// The reading level decides how much of a subject renders, never where it
// renders. A subject the API says nothing about is still a row in the list it
// belongs to, and still has its own page under that list.

const GROUP_BY_ID = new Map(GROUPS.map((g) => [g.id, g]));

// The count key a group is filed under, so a route reads `counts.fieldTypes`
// rather than `counts.field_types`.
const COUNT_KEY = {
	findings: 'findings',
	field_types: 'fieldTypes',
	entity_types: 'entityTypes',
	recipes: 'recipes',
	endpoints: 'endpoints'
};

function subject(groupId, slug, api) {
	const group = GROUP_BY_ID.get(groupId);
	return {
		group: groupId,
		// The programmatic name, and the route. A display name can be changed in
		// the web interface tomorrow; this is what a filter and a URL are written
		// against, so identity never moves with it.
		slug,
		name: displayName(slug, groupId),
		number: numberOf(slug),
		fullName: [numberOf(slug), displayName(slug, groupId)].filter(Boolean).join(' '),
		href: `${group.base}/${slug}`,
		title: '',
		api,
		locals: []
	};
}

// A list a person scans is ordered by what they can see. An entity type's slug is
// `CustomEntity19` and its label is `Lenses`; `CustomEntity` sorts before `Cut`,
// so ordering by slug files every custom entity in the middle of the Cs under a
// name that is nowhere on the page. Only that group has a label distinct from its
// slug, and only that group is reordered: a finding and a recipe are numbered, and
// the number is the order. Endpoints are regrouped later, by family.
const SORT_BY_LABEL = new Set(['entity_types']);
const label = (s) => s.title || s.name || s.slug;

function sorter(groupId) {
	if (!SORT_BY_LABEL.has(groupId)) return (a, b) => a.slug.localeCompare(b.slug);
	// The slug breaks the tie, so two types sharing a display name keep a stable
	// order rather than swapping between builds.
	return (a, b) =>
		label(a).localeCompare(label(b), 'en', { sensitivity: 'base' }) ||
		a.slug.localeCompare(b.slug);
}

// --- the public API used by routes ------------------------------------------

let cache = null;

function build() {
	const sources = [SITE, ...projectSources()];

	const shipped = {};
	const overlay = {};
	for (const group of GROUPS) {
		shipped[group.id] = readGroup(SHIPPED, group);
		overlay[group.id] = sources.flatMap((source) => readGroup(source, group));
	}

	const local = GROUPS.flatMap((g) => overlay[g.id]);

	// A project with no readable file is not offered as a reading level, because
	// selecting it would show the reader nothing.
	const projects = projectSources()
		.map((source) => {
			const mine = local.filter((e) => e.project === source.project);
			return {
				id: source.project,
				label: mine.find((e) => e.projectName)?.projectName || source.project,
				count: mine.length
			};
		})
		.filter((p) => p.count > 0);

	// One label per project, so every mark and every section names it the same
	// way. With every project selected at once, this is what tells a reader
	// which of them a section was measured on.
	const labels = new Map(projects.map((p) => [p.id, p.label]));
	for (const entry of local) entry.projectLabel = labels.get(entry.project) ?? '';

	// Shipped and overlay entries merge by slug into one list per group. A slug
	// with no shipped card becomes a subject anyway: it is a measurement of the
	// same kind of thing and belongs in the same list, sorted into place by its
	// own number.
	const subjects = {};
	for (const group of GROUPS) {
		const bySlug = new Map();
		for (const e of shipped[group.id]) bySlug.set(e.slug, subject(group.id, e.slug, e));
		for (const e of overlay[group.id]) {
			let found = bySlug.get(e.slug);
			if (!found) bySlug.set(e.slug, (found = subject(group.id, e.slug, null)));
			found.locals.push(e);
		}
		// Whichever card names it wins, the API card first. A subject with no card
		// carrying the key keeps the name read off its slug.
		for (const s of bySlug.values()) {
			s.title = s.api?.title || s.locals.find((l) => l.title)?.title || '';
		}
		subjects[group.id] = [...bySlug.values()].sort(sorter(group.id));
	}

	const hasSite = local.some((e) => e.level === 'site');

	cache = {
		shipped,
		subjects,
		hasSite,
		projects,
		// Every conditional in the routes reads this one flag.
		hasOverlay: hasSite || projects.length > 0,
		counts: countsByLevel(subjects, { hasSite, projects })
	};
	return cache;
}

// One count per group per level the switch can offer, computed here because a
// page renders its counts on the client and must not carry the corpus to do it.
function countsByLevel(subjects, { hasSite, projects }) {
	const at = (show) => {
		const out = {};
		for (const group of GROUPS) {
			out[COUNT_KEY[group.id]] = subjects[group.id].filter(
				(s) => s.api || s.locals.some(show)
			).length;
		}
		return out;
	};

	const isSite = (l) => l.level === 'site';
	const counts = { api: at(() => false) };
	if (hasSite) counts.site = at(isSite);
	for (const p of projects) {
		counts[`project:${p.id}`] = at((l) => isSite(l) || l.project === p.id);
	}
	return counts;
}

function all() {
	// Cached for the build; rebuilt on every request in dev so the designer sees
	// corpus edits without restarting.
	if (cache && !import.meta.env?.DEV) return cache;
	return build();
}

// What a list row needs from one local card: which level it came from, which
// project, and the one-line verdict a subject with no API card is described by.
// The body stays behind, so an index costs nothing to draw.
function stub(entry) {
	return {
		level: entry.level,
		project: entry.project,
		projectLabel: entry.projectLabel,
		verdict: entry.verdict,
		tags: entry.tags
	};
}

// A list row: identity, whatever the API card says, and a stub per local card.
// The rendered bodies are the expensive part and are not needed to draw a list.
function summary(s) {
	return {
		group: s.group,
		slug: s.slug,
		name: s.name,
		number: s.number,
		fullName: s.fullName,
		title: s.title,
		heading: s.title || s.fullName,
		href: s.href,
		hasApi: Boolean(s.api),
		verdict: s.api?.verdict ?? '',
		tags: s.api?.tags ?? [],
		phase: s.api?.phase ?? '',
		endpoints: s.api?.endpoints ?? [],
		endpoint: s.api?.endpoint ?? '',
		locals: s.locals.map(stub)
	};
}

// One subject in full. `raw` is dropped from every card: /filters reads it, and
// nothing else should carry it into a page payload.
function detail(s) {
	return {
		group: s.group,
		slug: s.slug,
		name: s.name,
		number: s.number,
		fullName: s.fullName,
		title: s.title,
		heading: s.title || s.fullName,
		href: s.href,
		hasApi: Boolean(s.api),
		verdict: s.api?.verdict ?? '',
		tags: s.api?.tags ?? [],
		phase: s.api?.phase ?? '',
		endpoints: s.api?.endpoints ?? [],
		endpoint: s.api?.endpoint ?? '',
		cardLinks: s.api?.cardLinks ?? [],
		html: s.api?.html ?? '',
		locals: s.locals.map(({ raw, ...rest }) => rest)
	};
}

export function index() {
	const data = all();
	return {
		findings: data.subjects.findings.map(summary),
		fieldTypes: data.subjects.field_types.map(summary),
		entityTypes: data.subjects.entity_types.map(summary),
		recipes: data.subjects.recipes.map(summary),
		endpoints: endpointOrder(data.subjects.endpoints.map(summary)),
		hasSite: data.hasSite,
		projects: data.projects,
		hasOverlay: data.hasOverlay,
		counts: data.counts
	};
}

export function entry(groupId, slug) {
	const found = all().subjects[groupId]?.find((s) => s.slug === slug);
	return found ? detail(found) : null;
}

// The filter matrix, built from the field-type cards. Throws, with the file
// named, if a card records no operator vocabulary: see src/lib/content/filters.js.
// Shipped cards only: /filters publishes API behaviour and nothing else.
export function filterIndex() {
	return filterMatrix(all().shipped.field_types);
}

// The same cards, ungrouped, each with the value matrix its **Filter** section
// records. /filters renders one section per type from this.
export function filterTypes() {
	return filterCards(all().shipped.field_types);
}

// Every subject in a group, shipped or local-only, so each has a page. A public
// build has no local-only subject and prerenders the shipped set exactly.
export function slugs(groupId) {
	return all().subjects[groupId].map((s) => s.slug);
}


// --- the phase axis ---------------------------------------------------------
// Findings were numbered by when the probe ran, which is nothing a caller knows.
// `phase:` is the part of a session the finding bites in, and this is the order
// a client meets them, so the listing itself teaches the shape of a session.
// `probes/index.py` groups corpus/INDEX.md the same way and by the same names.

export const PHASES = [
	{ id: 'auth', title: 'Auth', note: 'getting a token, and what it is' },
	{ id: 'protocol', title: 'Protocol', note: 'headers, and what a status code is worth' },
	{ id: 'schema', title: 'Schema', note: 'what the site has, and adding to it' },
	{ id: 'read', title: 'Read', note: 'getting rows back' },
	{ id: 'filter', title: 'Filter', note: 'selecting the rows you want' },
	{ id: 'write', title: 'Write', note: 'creating and updating' },
	{ id: 'upload', title: 'Upload', note: 'getting bytes in and out' },
	{ id: 'observe', title: 'Observe', note: 'what changed' },
	{ id: 'render', title: 'Render', note: 'showing it to a person' }
];

// A finding with no phase, or one this list does not name, is still listed: it
// falls to the end under its own heading rather than dropping out of the page.
export function findingsByPhase(findings) {
	const named = new Set(PHASES.map((p) => p.id));
	const groups = PHASES.map((p) => ({ ...p, entries: findings.filter((f) => f.phase === p.id) }))
		.filter((g) => g.entries.length);
	const rest = findings.filter((f) => !named.has(f.phase));
	if (rest.length) groups.push({ id: 'unphased', title: 'Unphased', note: '', entries: rest });
	return groups;
}

// --- the endpoint axis ------------------------------------------------------
// An agent about to make a call holds the call. Every card is named by one, and
// every finding and recipe names the calls it covers in that same spelling, so
// the join here cannot half-match. `probes/check_corpus.py` rejects any other
// spelling, which is what keeps this from silently going empty.

// Endpoints are grouped by the resource they act on, in the order a client meets
// them, and the family is derived from the path rather than declared on the card.
// A hand-kept list was fine at 23 endpoints and wrong at 54: a card the list did
// not name fell off the end of it silently. `probes/index.py` holds the same rules
// for `corpus/INDEX.md`, so the site and the index group the same way.
export const FAMILIES = [
	'Session',
	'Site',
	'Schema',
	'Records',
	'Search',
	'Media',
	'Attention',
	'Webhooks',
	'Exports',
	'Other'
];

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
const SITE_PREFIXES = ['/spec.', '/preferences', '/license_info', '/schedule/', '/subscription_seat/'];
const ATTENTION = ['follow', 'activity_stream', 'thread_contents'];

const pathOf = (endpoint) => endpoint.slice(endpoint.indexOf(' ') + 1);

// Order matters here: a path can match more than one rule, and the first wins.
// `/entity/<type>/_search` is Search before it is Records.
export function family(endpoint) {
	const path = pathOf(endpoint);
	if (path === '/' || path.startsWith('/auth/')) return 'Session';
	if (SITE_PREFIXES.some((p) => path.startsWith(p))) return 'Site';
	if (path.startsWith('/schema')) return 'Schema';
	if (path.includes('_search') || path.includes('_summarize') || path.startsWith('/hierarchy/'))
		return 'Search';
	if (path.includes('_upload') || path.startsWith('<links.') || path.startsWith('/transcode/'))
		return 'Media';
	if (ATTENTION.some((k) => path.includes(k))) return 'Attention';
	if (path.startsWith('/webhook')) return 'Webhooks';
	if (path.startsWith('/exports/')) return 'Exports';
	if (path.startsWith('/entity')) return 'Records';
	return 'Other';
}

function endpointOrder(rows) {
	return [...rows].sort((a, b) => {
		const fa = FAMILIES.indexOf(family(a.endpoint)) - FAMILIES.indexOf(family(b.endpoint));
		if (fa !== 0) return fa;
		const pa = pathOf(a.endpoint);
		const pb = pathOf(b.endpoint);
		if (pa !== pb) return pa < pb ? -1 : 1;
		return METHODS.indexOf(a.endpoint.split(' ')[0]) - METHODS.indexOf(b.endpoint.split(' ')[0]);
	});
}

// A grouped copy of the ordered list, for the index page. The sidebar takes the
// flat one: adjacency already carries the grouping in a narrow column.
export function endpointsByFamily(rows) {
	return FAMILIES.map((id) => ({
		id,
		entries: rows.filter((e) => family(e.endpoint) === id)
	})).filter((g) => g.entries.length);
}

// One link list per card, from two sources that cannot be one.
//
// The card's own `**Links**` names what no join can derive: the sibling endpoint,
// the field-type card that governs the value. The `endpoints:` join names every
// finding and recipe that measured this call, and cannot drift because nothing
// maintains it by hand. Merged, de-duplicated, and grouped by where each lives,
// which is what tells a reader what kind of thing they are about to open.
//
// Names only. The one-liner is on the other side of the link, and repeating it
// here is the index a second time.
const LINK_GROUPS = [
	{ id: 'endpoints', label: 'Endpoints' },
	{ id: 'field_types', label: 'Field types' },
	{ id: 'entity_types', label: 'Entity types' },
	{ id: 'findings', label: 'Findings' },
	{ id: 'recipes', label: 'Recipes' }
];

export function linksFor(card) {
	const data = all();
	const paths = [
		...card.cardLinks,
		// `findings/007_fill_rates` measures one site and is not published, so a
		// card citing it resolves to nothing and is dropped rather than dead-linked.
		...[...data.shipped.findings, ...data.shipped.recipes]
			.filter((e) => e.endpoints.includes(card.endpoint))
			.map((e) => `${e.group}/${e.slug}`)
	];

	const seen = new Set();
	const out = LINK_GROUPS.map((g) => ({ ...g, items: [] }));
	for (const ref of paths) {
		if (seen.has(ref) || ref === `endpoints/${card.slug}`) continue;
		seen.add(ref);
		const slash = ref.indexOf('/');
		const groupId = ref.slice(0, slash);
		const slug = ref.slice(slash + 1);
		const bucket = out.find((g) => g.id === groupId);
		const found = data.subjects[groupId]?.find((s) => s.slug === slug);
		// A published card can only cite something published. A typo, or a citation
		// of a `scope: site` entry this build excludes, fails here rather than
		// rendering a link to a page that was never built.
		if (!bucket || !found) {
			throw new Error(
				`[corpus] endpoints/${card.slug}.md links to "${ref}", which is not a published ` +
					`entry. Fix the path, or drop the link if the target measures one site.`
			);
		}
		bucket.items.push({ name: found.title || found.fullName, href: found.href });
	}
	return out.filter((g) => g.items.length);
}

// Throws, naming the file, if an entry spells an endpoint no card is named by.
// That fails the build rather than rendering a section with nothing under it.
export function checkEndpoints() {
	const data = all();
	const known = new Set(data.shipped.endpoints.map((e) => e.endpoint));
	for (const card of [...data.shipped.findings, ...data.shipped.recipes]) {
		for (const e of card.endpoints) {
			if (!known.has(e)) {
				throw new Error(
					`[corpus] ${card.group}/${card.slug}.md names endpoint "${e}", which no card in ` +
						`corpus/endpoints/ is named by. Reuse the canonical spelling or add the card.`
				);
			}
		}
	}
	return data.shipped.endpoints.length;
}
