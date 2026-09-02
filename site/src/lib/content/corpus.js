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

function anchorSafe(s) {
	return s.replace(/[^A-Za-z0-9_-]+/g, '-');
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

	// One label per project, so every band and flag names it the same way.
	const labels = new Map(projects.map((p) => [p.id, p.label]));
	for (const entry of local) entry.projectLabel = labels.get(entry.project) ?? '';

	// Attach each overlay entry to its shipped counterpart by slug. What is left
	// over has no counterpart and renders in full on /site, so the overlay never
	// needs a route of its own.
	const localOnly = [];
	for (const group of GROUPS) {
		const bySlug = new Map(shipped[group.id].map((e) => [e.slug, e]));
		for (const entry of overlay[group.id]) {
			const target = bySlug.get(entry.slug);
			if (target) {
				(target.locals ??= []).push(entry);
			} else {
				entry.anchor = anchorSafe(`${entry.level}-${entry.project ?? ''}-${entry.group}-${entry.slug}`);
				entry.href = `/site#${entry.anchor}`;
				localOnly.push(entry);
			}
		}
	}

	const hasSite = local.some((e) => e.level === 'site');

	cache = {
		shipped,
		localOnly,
		hasSite,
		projects,
		// Every conditional in the routes reads this one flag.
		hasOverlay: hasSite || projects.length > 0,
		counts: {
			findings: shipped.findings.length,
			fieldTypes: shipped.field_types.length,
			entityTypes: shipped.entity_types.length,
			recipes: shipped.recipes.length,
			overlay: local.length
		}
	};
	return cache;
}

function all() {
	// Cached for the build; rebuilt on every request in dev so the designer sees
	// corpus edits without restarting.
	if (cache && !import.meta.env?.DEV) return cache;
	return build();
}

// What a reading level needs to decide whether a local entry is shown. The
// bodies stay behind, so an index costs nothing to draw.
function stub(entry) {
	return { level: entry.level, project: entry.project, projectLabel: entry.projectLabel };
}

// A list entry is everything except the rendered body, which is the expensive
// part and is not needed to draw an index.
function summary(entry) {
	const { html, raw, locals, ...rest } = entry;
	return { ...rest, locals: (locals ?? []).map(stub) };
}

export function index() {
	const data = all();
	return {
		findings: data.shipped.findings.map(summary),
		fieldTypes: data.shipped.field_types.map(summary),
		entityTypes: data.shipped.entity_types.map(summary),
		recipes: data.shipped.recipes.map(summary),
		localOnly: data.localOnly.map(summary),
		hasSite: data.hasSite,
		projects: data.projects,
		hasOverlay: data.hasOverlay,
		counts: data.counts
	};
}

export function entry(groupId, slug) {
	const found = all().shipped[groupId]?.find((e) => e.slug === slug);
	if (!found) return null;
	const { raw, ...rest } = found;
	return { ...rest, locals: found.locals ?? [] };
}

// The filter matrix, built from the field-type cards. Throws, with the file
// named, if a card records no operator vocabulary: see src/lib/content/filters.js.
export function filterIndex() {
	return filterMatrix(all().shipped.field_types);
}

// The same cards, ungrouped, each with the value matrix its **Filter** section
// records. /filters renders one section per type from this.
export function filterTypes() {
	return filterCards(all().shipped.field_types);
}

// Overlay entries with no shipped counterpart, bodies included. They render in
// full on /site rather than getting a route each.
export function localEntries() {
	return all().localOnly.map(({ raw, ...rest }) => rest);
}

export function slugs(groupId) {
	return all().shipped[groupId].map((e) => e.slug);
}
