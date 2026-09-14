// The middle tier, over HTTP. `probes/index.py` generates `corpus/doors/`: one
// file per thing a caller already holds, carrying a line per entry and that
// entry's rules copied whole. A clone reads them off disk. This serves the same
// bytes at `/doors/<name>.md` and renders them at `/doors/<name>`, so an agent
// that fetches reads the three tiers an agent that clones reads.
//
// A door carries no frontmatter, so nothing here parses any. The heading is the
// first line, the blurb is the paragraph under it, and the rest is the door.
//
// Server-only, like the rest of `content/`, and prerendered: a door is a file
// in `build/`.

import fs from 'node:fs';
import path from 'node:path';
import { SHIPPED } from './sources.js';
import { FAMILIES, METHODS, PHASES, family, renderMarkdown } from './corpus.js';

const DIR = path.join(SHIPPED.root, 'doors');

export const DOORS_BASE = '/doors';
export const doorHref = (name) => `${DOORS_BASE}/${name}`;
export const doorTwinHref = (name) => `${DOORS_BASE}/${name}.md`;
export const doorSource = (name) => `corpus/doors/${name}.md`;

// What a door is a way in to, in the order the map lists them. A door whose name
// this does not recognise is still listed, under `other`, rather than dropping
// off a page an agent is told to read.
export const KINDS = [
	{
		id: 'findings',
		title: 'Findings',
		note: 'one per phase of a session, in the order a client meets them'
	},
	{ id: 'field_types', title: 'Field types', note: 'one row per data type' },
	{ id: 'entity_types', title: 'Entity types', note: 'one row per standard entity type' },
	{ id: 'recipes', title: 'Recipes', note: 'addressed by the task' },
	{
		id: 'endpoints',
		title: 'Endpoints',
		note: 'one per family of calls, split by method where a family outgrows what an agent should read to answer one call'
	},
	{ id: 'reports', title: 'Reports', note: 'behaviour that should change, and the re-probe queue' },
	{ id: 'tags', title: 'Tags', note: 'every entry under each tag' },
	{ id: 'other', title: 'Other', note: '' }
];

const KIND_INDEX = new Map(KINDS.map((k, i) => [k.id, i]));

// An endpoint door is titled by its family, by its family and method where the
// family was split, or by the call itself where a method was split again. The
// title is what says which, so the rank is read off it and never off the name:
// a per-call door is named by the slugified call, which no longer carries the
// family it belongs to.
const FAMILY_TITLE = /^Endpoints\s+—\s+(.+)$/;
const CALL_TITLE = /^`(.+)`$/;

function endpointPlace(name, title) {
	const call = CALL_TITLE.exec(title);
	if (call) {
		const endpoint = call[1];
		const fam = family(endpoint);
		return { family: fam, rank: [FAMILIES.indexOf(fam), METHODS.indexOf(endpoint.split(' ')[0]), endpoint] };
	}
	const titled = FAMILY_TITLE.exec(title);
	if (titled) {
		const [fam, method = ''] = titled[1].split(',').map((s) => s.trim());
		return { family: fam, rank: [FAMILIES.indexOf(fam), method ? METHODS.indexOf(method) : -1, ''] };
	}
	return { family: '', rank: [FAMILIES.length, 0, name] };
}

const NAMED = new Set(['field_types', 'entity_types', 'recipes', 'reports', 'tags']);

function place(name, title) {
	if (name === 'unphased') return { kind: 'findings', phase: '', family: '', rank: [PHASES.length] };
	if (name.startsWith('findings-')) {
		const phase = name.slice('findings-'.length);
		const at = PHASES.findIndex((p) => p.id === phase);
		return { kind: 'findings', phase, family: '', rank: [at === -1 ? PHASES.length : at] };
	}
	if (name.startsWith('endpoints-')) {
		const { family: fam, rank } = endpointPlace(name, title);
		return { kind: 'endpoints', phase: '', family: fam, rank };
	}
	if (NAMED.has(name)) return { kind: name, phase: '', family: '', rank: [0] };
	return { kind: 'other', phase: '', family: '', rank: [0] };
}

const byRank = (a, b) => {
	const ka = KIND_INDEX.get(a.kind) ?? KINDS.length;
	const kb = KIND_INDEX.get(b.kind) ?? KINDS.length;
	if (ka !== kb) return ka - kb;
	for (let i = 0; i < Math.max(a.rank.length, b.rank.length); i++) {
		const x = a.rank[i] ?? 0;
		const y = b.rank[i] ?? 0;
		if (x !== y) return x < y ? -1 : 1;
	}
	return a.name.localeCompare(b.name);
};

// The first paragraph under the heading, and everything after it. The page sets
// the blurb as its lede, so rendering it again in the body would say it twice.
function split(raw) {
	const lines = raw.split('\n');
	const head = /^#\s+(.*)$/.exec(lines[0] ?? '');
	let at = head ? 1 : 0;
	while (at < lines.length && lines[at].trim() === '') at++;
	const from = at;
	while (at < lines.length && lines[at].trim() !== '') at++;
	return {
		title: head ? head[1].trim() : '',
		blurb: lines.slice(from, at).join(' ').trim(),
		body: lines.slice(at).join('\n').trim()
	};
}

// A door that lists entries heads each with `##`; reports and tags are one
// bullet each instead. Whichever it is, this is how many things are on the file.
function countOf(raw) {
	const headings = raw.match(/^## /gm);
	return headings ? headings.length : (raw.match(/^- /gm) ?? []).length;
}

let cache = null;

function load() {
	if (!fs.existsSync(DIR)) {
		// Loud, because a missing doors/ renders as a site that merely looks thin:
		// the map names a door per way in, and every one of them would 404.
		throw new Error(
			`[doors] no ${DIR}. The doors are generated and committed; run \`python probes/index.py\`.`
		);
	}
	const rows = fs
		.readdirSync(DIR)
		.filter((f) => f.endsWith('.md') && f !== 'README.md')
		.map((file) => {
			const name = file.replace(/\.md$/, '');
			const raw = fs.readFileSync(path.join(DIR, file), 'utf8');
			const { title, blurb, body } = split(raw);
			return {
				name,
				// The call a per-call door is named by is set in mono on the page,
				// exactly as the API spells it.
				literal: CALL_TITLE.test(title),
				title: title.replace(/^`(.+)`$/, '$1') || name,
				// The blurb is markdown like the rest of the door, so it is rendered
				// for the page and flattened for the `<meta>` description, which
				// takes text and would print the asterisks.
				blurb: blurb.replace(/\*\*/g, '').replace(/`/g, ''),
				blurbHtml: renderMarkdown(blurb),
				count: countOf(raw),
				bytes: Buffer.byteLength(raw),
				href: doorHref(name),
				md: doorTwinHref(name),
				source: doorSource(name),
				raw,
				body,
				...place(name, title)
			};
		})
		.sort(byRank);
	cache = rows;
	return rows;
}

function all() {
	if (cache && !import.meta.env?.DEV) return cache;
	return load();
}

// A list row: everything but the bytes of the door itself, which are the
// expensive part and are not needed to draw a list.
const summary = ({ raw, body, rank, ...rest }) => rest;

export const doors = () => all().map(summary);

export const doorNames = () => all().map((d) => d.name);

// Grouped the way the map groups them, for the page that lists them.
export function doorsByKind() {
	const rows = all();
	return KINDS.map((k) => ({ ...k, doors: rows.filter((d) => d.kind === k.id).map(summary) })).filter(
		(k) => k.doors.length
	);
}

// Null rather than a throw: the route turns it into the 404 a wrong name earns.
export function readDoor(name) {
	const found = all().find((d) => d.name === name);
	return found ? found.raw : null;
}

export function door(name) {
	const found = all().find((d) => d.name === name);
	return found ? { ...summary(found), html: renderMarkdown(found.body) } : null;
}
