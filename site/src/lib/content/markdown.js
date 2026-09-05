// The machine door. Every corpus page has a markdown twin at the same URL with
// `.md` appended, and a twin is the shipped file byte for byte, frontmatter
// included: `scope`, `phase`, `tags` and `endpoints` are the retrieval keys, so
// a body without them is less than the repository holds.
//
// Verbatim also means unmerged. The rendered page can carry the overlay; the
// twin is `corpus/<group>/<slug>.md` and nothing else, so what an agent fetches
// from the site and what it would read out of the clone are the same bytes.
//
// Server-only, and prerendered like every page: a twin is a file in build/.

import fs from 'node:fs';
import path from 'node:path';
import { SHIPPED, GROUPS } from './sources.js';

// The URL segment a group renders under, without the leading slash. `/findings`
// is the route, `findings` is what a `[section]` param holds.
const segmentOf = (group) => group.base.replace(/^\//, '');

// Every group, keyed both ways a route needs it. GROUPS is the only place the
// directory of a group is written down; a second copy is what put a dead
// `corpus/findings/get_root.md` behind every endpoint card's source link.
export const SECTIONS = GROUPS.map((g) => ({
	segment: segmentOf(g),
	group: g.id,
	dir: g.dir,
	base: g.base,
	title: g.title
}));

const BY_SEGMENT = new Map(SECTIONS.map((s) => [s.segment, s]));
const BY_GROUP = new Map(SECTIONS.map((s) => [s.group, s]));

export const section = (segment) => BY_SEGMENT.get(segment) ?? null;

// Repo-relative, so it is also the path in a `git clone` and on GitHub.
export function sourcePath(groupId, slug) {
	const found = BY_GROUP.get(groupId);
	return found ? `corpus/${found.dir}/${slug}.md` : '';
}

// The twin's URL. One rule, applied everywhere: the page URL plus `.md`.
export function twinHref(groupId, slug) {
	const found = BY_GROUP.get(groupId);
	return found ? `${found.base}/${slug}.md` : '';
}

// Null rather than a throw: the route turns it into the 404 a wrong slug earns.
// A local-only subject has a page and no shipped file, so this is a real answer
// and not only a typo.
export function readEntry(groupId, slug) {
	const found = BY_GROUP.get(groupId);
	if (!found) return null;
	const file = path.join(SHIPPED.root, found.dir, `${slug}.md`);
	return fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : null;
}
