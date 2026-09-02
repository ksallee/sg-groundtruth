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

// The page renders its own <h1> from the entry name, so drop the body's.
function stripLeadingH1(body) {
	return body.replace(/^\s*#\s+.*\n+/, '');
}

function render(body) {
	return wrapTables(marked.parse(stripLeadingH1(body)));
}

// --- reading ---------------------------------------------------------------

function readGroup(source, group) {
	const dir = path.join(source.root, group.dir);
	if (!fs.existsSync(dir)) return [];

	return fs
		.readdirSync(dir)
		.filter((f) => f.endsWith('.md'))
		.sort()
		.map((file) => {
			const slug = file.replace(/\.md$/, '');
			const { meta, body } = parseFrontmatter(fs.readFileSync(path.join(dir, file), 'utf8'));
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
				title: meta.title ?? '',
				// `verdict` on a finding, `intent` on a recipe. One line either way.
				verdict: meta.verdict ?? meta.intent ?? '',
				tags: Array.isArray(meta.tags) ? meta.tags : [],
				name: displayName(slug, group.id),
				// With the number, for a page title and a heading. The list shows
				// the number in its own column, so it uses `name` and `number`.
				fullName: [numberOf(slug), displayName(slug, group.id)].filter(Boolean).join(' '),
				number: numberOf(slug),
				href: `${group.base}/${slug}`,
				html: render(body),
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
	recipes: 'recipes'
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
		subjects[group.id] = [...bySlug.values()].sort((a, b) => a.slug.localeCompare(b.slug));
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
// `project:*` is every project at once.
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
	if (projects.length) counts['project:*'] = at(() => true);
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
