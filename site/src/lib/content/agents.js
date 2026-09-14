// What a client that fetches rather than reads is given: an index it can start
// from, a sitemap, and robots. The twins themselves are `markdown.js`.
//
// The rendered page costs eleven bytes of markup per byte of finding, and the
// only markdown door used to be a GitHub blob link, which is another HTML page
// a client has to know how to rewrite. These routes are the door.

import { error, text } from '@sveltejs/kit';
import { index, slugs, findingsByPhase, endpointsByFamily } from './corpus.js';
import { SECTIONS, section, readEntry, twinHref } from './markdown.js';
import { doors, doorTwinHref } from './doors.js';
import { ORIGIN, REPO } from '$lib/site.js';

const abs = (href) => `${ORIGIN}${href}`;
const link = (label, href) => `[${label}](${abs(href)})`;

// A row a client can act on: what it is, where the bytes are, and the one line
// the entry ends in. Coverage rides along, because an entry that reads like the
// rest while resting on a call nobody completed is the one that costs a reader.
function row(e) {
	const note =
		e.coverage === 'untested'
			? ` (not tested: ${e.unmeasured})`
			: e.coverage === 'partial'
				? ` (partly measured: ${e.unmeasured})`
				: '';
	return `- [${e.heading}](${abs(twinHref(e.group, e.slug))}): ${e.verdict}${note}`;
}

const published = (rows) => rows.filter((e) => e.hasApi);

// `index()` keys its lists in camelCase and a route segment is hyphenated, so
// the two are joined here. Throws rather than returning nothing: a group added
// to GROUPS and forgotten here would otherwise render an empty section that
// reads as a group with nothing in it.
function group(segment) {
	const found = SECTIONS.find((s) => s.segment === segment);
	const data = index();
	const byKey = {
		findings: data.findings,
		'field-types': data.fieldTypes,
		'entity-types': data.entityTypes,
		recipes: data.recipes,
		reports: data.reports,
		endpoints: data.endpoints
	};
	if (!found || !byKey[segment]) throw new Error(`[agents] no group behind /${segment}`);
	return { section: found, rows: published(byKey[segment]) };
}

// Findings and endpoints are grouped on their pages, and the grouping is the
// content: phase is the order a client meets a finding, family is the resource
// a call acts on. A flat list of 54 endpoints teaches neither. Every other group
// renders as one list, in the order its page renders it.
function grouped(segment, rows) {
	if (segment === 'findings') return findingsByPhase(rows);
	if (segment === 'endpoints')
		return endpointsByFamily(rows).map((f) => ({ title: f.id, note: '', entries: f.entries }));
	return [{ title: '', note: '', entries: rows }];
}

// --- the section twins ------------------------------------------------------

// The twin of a listing page. Findings keep the phase grouping the page draws,
// because the order is the shape of a session and a flat list of 30 numbers is
// not. Every other group is one list, in the order its page renders it.
export function sectionIndex(segment) {
	const { section, rows } = group(segment);
	const lines = [`# ${section.title}`, ''];

	for (const part of grouped(segment, rows)) {
		if (part.title) lines.push(`## ${part.title}`, '');
		if (part.note) lines.push(part.note, '');
		lines.push(...part.entries.map(row), '');
	}

	// A client that fetched one section has the names and the verdicts. The rules
	// behind them are on the doors for that same group, so the section names them
	// rather than leaving the reader to go back to the map for it.
	const rules = doors().filter((d) => d.kind === section.group);
	if (rules.length) {
		lines.push(`The rules these entries teach, copied whole: ${rules.map(doorLink).join(', ')}.`, '');
	}

	lines.push(
		`Append \`.md\` to any entry URL for the file that page was built from.`,
		`The rendered pages are at ${abs(section.base)}.`,
		''
	);
	return lines.join('\n');
}

// --- llms.txt ---------------------------------------------------------------
//
// The map, over HTTP. `probes/index.py` writes the same map to `corpus/INDEX.md`
// for an agent with a clone, and the protocol here is in its words: an agent
// handed either one is told to do the same thing. What changes is that every
// name is a URL, because a client that fetches cannot open a path.
//
// It is the map and not the corpus again. One line per entry with its verdict
// was 44 KB, which is the index a second time over HTTP, and the verdicts now
// have a tier of their own: the doors.

const BLURB =
	'> Recorded behaviour of the Flow Production Tracking REST API. Every entry is what a live site ' +
	'answered when a probe asked it. The official REST documentation is incomplete and in places wrong.';

const doorLink = (d) => link(`doors/${d.name}.md`, doorTwinHref(d.name));

// The mark a door puts on an entry whose calls were not all made and answered.
const mark = (e) => (e.coverage && e.coverage !== 'measured' ? ` **[${e.coverage}]**` : '');

// Every entry is named the way the doors name it, which is its slug, so a name
// read off the map matches the heading it is under on the door. An endpoint card
// is named by its call: that is the card's identity and the only thing a caller
// holds.
const name = (e) => (e.group === 'endpoints' ? `\`${e.endpoint}\`` : e.slug);
const entryLink = (e) => link(name(e), twinHref(e.group, e.slug)) + mark(e);
const names = (rows) => rows.map(entryLink).join(', ');

export function llmsTxt() {
	const data = index();
	const open = doors();
	const cited = new Set();
	const byName = (n) => {
		const found = open.find((d) => d.name === n);
		if (found) cited.add(found.name);
		return found;
	};
	const ofKind = (kind, test = () => true) =>
		open.filter((d) => d.kind === kind && test(d)).map((d) => (cited.add(d.name), d));

	const findings = published(data.findings);
	const recipes = published(data.recipes);
	const cards = published(data.endpoints);

	const lines = ['# SG Ground Truth', '', BLURB, ''];

	lines.push(
		'Read this first. It names every entry and says which door to open. A group door carries one ' +
			'line per entry and that entry\'s rules, copied whole.',
		'',
		'| you know | open |',
		'|---|---|',
		'| the call | its family under **Endpoints** |'
	);
	for (const [holds, door] of [
		['the entity type', 'entity_types'],
		['the `data_type`', 'field_types'],
		['the task', 'recipes']
	]) {
		const found = byName(door);
		if (found) lines.push(`| ${holds} | ${doorLink(found)} |`);
	}
	lines.push(
		'| the phase of a session | its phase under **Findings** |',
		'',
		'An endpoint door holds the edge cases that live on the call and the verdict of every entry ' +
			'that measured it, each naming the group door its rules are on. Read the verdicts, open that ' +
			'door for the rules, the entry for a transcript, a sample or a table. A 2xx that did nothing ' +
			'is under **Silent on this call**. Measured against `/api/v1`.',
		'',
		'Every URL here is the markdown its page was built from. Drop the `.md` for the rendered page. ' +
			'On an entry the frontmatter is the retrieval key, and it is why the twins carry it: `scope` ' +
			'(`api` is the only one published here, and is true of any Flow PT site), `phase`, ' +
			'`endpoints`, `tags`, `verdict`, and `coverage`, which is absent on an entry fully measured.',
		''
	);

	lines.push('## Findings', '');
	for (const phase of findingsByPhase(findings)) {
		const door = byName(`findings-${phase.id}`) ?? byName('unphased');
		lines.push(`**${phase.id}**${door ? ` ${doorLink(door)}` : ''}`, '', names(phase.entries), '');
	}

	for (const [title, rows, door] of [
		['Field types', published(data.fieldTypes), 'field_types'],
		['Entity types', published(data.entityTypes), 'entity_types']
	]) {
		const found = byName(door);
		lines.push(`## ${title}`, '', ...(found ? [doorLink(found), ''] : []), names(rows), '');
	}

	const recipeDoor = byName('recipes');
	lines.push(
		'## Recipes',
		'',
		...(recipeDoor ? [doorLink(recipeDoor), ''] : []),
		...recipes.map((e) => `- ${entryLink(e)}: ${e.verdict}`),
		''
	);

	// The count is what makes a card with nothing behind it the queue rather than
	// an omission, and it is read off the join, never written down.
	const measured = new Set([...findings, ...recipes].flatMap((e) => e.endpoints));
	const covered = cards.filter((c) => measured.has(c.endpoint)).length;
	lines.push(
		'## Endpoints',
		'',
		`One card per call, ${covered} of ${cards.length} with an entry behind them; a card with none ` +
			'is the queue.',
		''
	);
	for (const fam of endpointsByFamily(cards)) {
		const famDoors = ofKind('endpoints', (d) => d.family === fam.id);
		lines.push(
			`**${fam.id}**${famDoors.length ? ` ${famDoors.map(doorLink).join(', ')}` : ''}`,
			'',
			...fam.entries.map((e) => `- ${entryLink(e)}`),
			''
		);
	}

	const reportDoor = byName('reports');
	const reports = published(data.reports);
	if (reports.length) {
		lines.push('## Reports', '', ...(reportDoor ? [doorLink(reportDoor), ''] : []), names(reports), '');
	}

	const tagDoor = byName('tags');
	const tags = [
		...new Set(
			[findings, published(data.fieldTypes), published(data.entityTypes), recipes, cards, reports]
				.flat()
				.flatMap((e) => e.tags)
		)
	].sort();
	lines.push(
		'## Tags',
		'',
		...(tagDoor ? [`${doorLink(tagDoor)} holds the entries under each.`, ''] : []),
		tags.join(' '),
		''
	);

	lines.push(
		'## Elsewhere',
		'',
		`- ${link('Every door', '/doors')}: what each one holds, and how large it is`,
		`- ${link('How it works', '/how-it-works')}: how the corpus is produced, and what the three scopes mean`,
		`- ${link('Filters', '/filters')}: the operator vocabulary, one section per \`data_type\`. HTML only; each field-type twin carries its own filter matrix.`,
		`- [The repository](${REPO}): the probes that produced every entry, and \`python -m sg_groundtruth.mcp\`, which serves this corpus to an agent over MCP`,
		''
	);

	// A door nothing above names is a door an agent reading this file cannot
	// reach. It is generated and committed, so this fails the build rather than
	// publishing a map with a hole in it.
	const missed = open.filter((d) => !cited.has(d.name)).map((d) => d.name);
	if (missed.length) {
		throw new Error(
			`[agents] llms.txt names no URL for ${missed.join(', ')}. Every door in corpus/doors/ ` +
				`has to be reachable from the map.`
		);
	}

	return lines.join('\n');
}

// --- crawling ---------------------------------------------------------------

// Every rendered page. The twins are deliberately absent: a sitemap addresses a
// reader, llms.txt addresses a client, and listing both spellings of one page
// asks a crawler to fetch it twice.
function pages() {
	const data = index();
	const entries = [
		...data.findings,
		...data.fieldTypes,
		...data.entityTypes,
		...data.recipes,
		...data.endpoints
	];
	return [
		'/',
		'/how-it-works',
		'/filters',
		'/doors',
		...doors().map((d) => d.href),
		...SECTIONS.map((s) => s.base),
		...published(entries).map((e) => e.href)
	];
}

export function sitemap() {
	const urls = pages()
		.map((href) => `\t<url><loc>${abs(href)}</loc></url>`)
		.join('\n');
	return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

export function robots() {
	return `User-agent: *
Allow: /

Sitemap: ${ORIGIN}/sitemap.xml
`;
}


// --- the routes -------------------------------------------------------------

// A twin is served as markdown, not as a download: a client fetching it wants to
// read it, and a browser following the link from an entry page should show it.
const served = (body) =>
	text(body, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });

// One route file per group, one line each, because the alternative is a root
// `[section]/[slug].md` that a static `findings/[slug]` outranks, and the `.md`
// request then reaches the HTML page as a slug ending in `.md`.
export function twin(segment) {
	const found = section(segment);
	return {
		prerender: true,
		// Shipped entries only. A local-only subject has a page and no file, so
		// listing it here would fail the build on a 404 the route is right to give.
		entries: () =>
			slugs(found.group)
				.filter((slug) => readEntry(found.group, slug) !== null)
				.map((slug) => ({ slug })),
		GET: ({ params }) => {
			const raw = readEntry(found.group, params.slug);
			if (raw === null) error(404, `No ${segment} ${params.slug}`);
			return served(raw);
		}
	};
}

export function sectionTwin() {
	return {
		prerender: true,
		// The five sections and nothing else, so `sectionIndex` throwing on an
		// unknown segment is a build failure rather than a route a client reaches.
		entries: () => SECTIONS.map((s) => ({ section: s.segment })),
		GET: ({ params }) => served(sectionIndex(params.section))
	};
}
