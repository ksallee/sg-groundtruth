// What a client that fetches rather than reads is given: an index it can start
// from, a sitemap, and robots. The twins themselves are `markdown.js`.
//
// The rendered page costs eleven bytes of markup per byte of finding, and the
// only markdown door used to be a GitHub blob link, which is another HTML page
// a client has to know how to rewrite. These routes are the door.

import { error, text } from '@sveltejs/kit';
import { index, slugs, findingsByPhase, endpointsByFamily } from './corpus.js';
import { SECTIONS, section, readEntry, twinHref } from './markdown.js';
import { ORIGIN, REPO } from '$lib/site.js';

const abs = (href) => `${ORIGIN}${href}`;

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

	lines.push(
		`Append \`.md\` to any entry URL for the file that page was built from.`,
		`The rendered pages are at ${abs(section.base)}.`,
		''
	);
	return lines.join('\n');
}

// --- llms.txt ---------------------------------------------------------------

const PREAMBLE = `> Recorded behaviour of the Flow Production Tracking REST API. Every entry is what a live \
site answered when a probe asked it. The official REST documentation is incomplete and in places wrong.

Append \`.md\` to any entry or section URL for the markdown that page was built from, frontmatter \
included. ${ORIGIN}/findings/026_result_order.md is the file behind \
${ORIGIN}/findings/026_result_order.

The frontmatter is the retrieval key, and it is why the twins carry it:

| key | what it selects |
|---|---|
| \`scope\` | \`api\` is the only scope published here. It is true of any Flow PT site. A measurement of one site or one project stays in the repository. |
| \`phase\` | the part of a session a finding bites in: auth, protocol, schema, read, filter, write, upload, observe, render |
| \`endpoints\` | the calls the entry was measured against, spelled as the card that owns them is named |
| \`tags\` | the subject. \`silent\`, \`destructive\` and \`trap\` name the kind of failure instead. |
| \`verdict\` | the one line the entry ends in |
| \`coverage\` | absent means measured. \`partial\` and \`untested\` come with an \`unmeasured\` line. |

Four ways in, one per thing a caller already knows.

| you know | start at |
|---|---|
| the call you are about to make | ${ORIGIN}/endpoints.md |
| the entity type | ${ORIGIN}/entity-types.md |
| the field's \`data_type\` | ${ORIGIN}/field-types.md |
| the task | ${ORIGIN}/recipes.md |

Findings are what the API does, and they are grouped by phase rather than by number: \
${ORIGIN}/findings.md`;

export function llmsTxt() {
	const lines = ['# SG Ground Truth', '', PREAMBLE, ''];

	for (const section of SECTIONS) {
		const { rows } = group(section.segment);
		if (!rows.length) continue;
		lines.push(`## ${section.title}`, '', ...rows.map(row), '');
	}

	lines.push(
		'## Elsewhere',
		'',
		`- [How it works](${ORIGIN}/how-it-works): how the corpus is produced, and what the three scopes mean`,
		`- [Filters](${ORIGIN}/filters): the operator vocabulary, one section per \`data_type\`. HTML only; each field-type twin carries its own filter matrix.`,
		`- [The repository](${REPO}): the probes that produced every entry, and \`python -m sg_groundtruth.mcp\`, which serves this corpus to an agent over MCP`,
		''
	);
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
