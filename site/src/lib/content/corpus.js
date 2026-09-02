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
import { SHIPPED, OVERLAY, GROUPS } from './sources.js';

// --- frontmatter -----------------------------------------------------------
// The corpus writes a fixed, flat block: `tags: [a, b]`, `scope:`, `verdict:`,
// `intent:`. One key per line, values never wrap. A full YAML parser would be a
// dependency for three keys.

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
				origin: source.id,
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
				html: render(body)
			};
		})
		.filter((entry) => {
			// The scope filter is the whole public/local boundary. A shipped entry
			// that measures one site (005, 007) is not published; an overlay entry
			// that forgot `scope: site` is not silently treated as general.
			if (entry.scope === source.scope) return true;
			if (source.id === OVERLAY.id) {
				console.warn(
					`[corpus] skipped ${source.root}/${group.dir}/${entry.slug}.md: ` +
						`overlay files need \`scope: site\`, found \`${entry.scope || 'nothing'}\``
				);
			}
			return false;
		});
}

function numberOf(slug) {
	const m = /^(\d+)_/.exec(slug);
	return m ? m[1] : null;
}

// `003_query` reads as `query` next to its own number. `multi_entity` is the
// API's own `data_type` literal and is left exactly as the API spells it.
function displayName(slug, groupId) {
	if (groupId === 'field_types') return slug;
	return slug.replace(/^\d+_/, '').replace(/_/g, ' ');
}

// --- the public API used by routes ------------------------------------------

let cache = null;

function build() {
	const shipped = {};
	const overlay = {};
	for (const group of GROUPS) {
		shipped[group.id] = readGroup(SHIPPED, group);
		overlay[group.id] = readGroup(OVERLAY, group);
	}

	// Attach each overlay entry to its shipped counterpart by slug. What is left
	// over has no counterpart and is rendered in full on /site, so the overlay
	// never needs a route of its own.
	const localOnly = [];
	for (const group of GROUPS) {
		const bySlug = new Map(shipped[group.id].map((e) => [e.slug, e]));
		for (const local of overlay[group.id]) {
			const target = bySlug.get(local.slug);
			if (target) {
				target.local = local;
			} else {
				local.anchor = `${local.group}-${local.slug}`;
				local.href = `/site#${local.anchor}`;
				localOnly.push(local);
			}
		}
	}

	const overlayCount = GROUPS.reduce((n, g) => n + overlay[g.id].length, 0);

	cache = {
		shipped,
		localOnly,
		// Every conditional in the routes reads this one flag.
		hasOverlay: overlayCount > 0,
		counts: {
			findings: shipped.findings.length,
			fieldTypes: shipped.field_types.length,
			recipes: shipped.recipes.length,
			overlay: overlayCount
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

// A list entry is everything except the rendered body, which is the expensive
// part and is not needed to draw an index.
function summary(entry) {
	const { html, local, ...rest } = entry;
	return { ...rest, hasLocal: Boolean(local) };
}

export function index() {
	const data = all();
	return {
		findings: data.shipped.findings.map(summary),
		fieldTypes: data.shipped.field_types.map(summary),
		recipes: data.shipped.recipes.map(summary),
		localOnly: data.localOnly.map(summary),
		hasOverlay: data.hasOverlay,
		counts: data.counts
	};
}

export function entry(groupId, slug) {
	const found = all().shipped[groupId]?.find((e) => e.slug === slug);
	if (!found) return null;
	return { ...found, hasLocal: Boolean(found.local) };
}

// Overlay entries with no shipped counterpart, bodies included. They render in
// full on /site rather than getting a route each.
export function localEntries() {
	return all().localOnly;
}

export function slugs(groupId) {
	return all().shipped[groupId].map((e) => e.slug);
}
