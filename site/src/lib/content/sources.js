// THE SEAM between the content sources. Everything about where content comes
// from, and what is allowed to be published from each source, is decided here
// and nowhere else. Routes never touch the filesystem.
//
// Three levels of truth, and the probes are what proved they are distinct.
// Probe 009 is the clearest case: `valid_values` is byte-identical at every
// scope and only `hidden_values` varies by project, so "which statuses can I
// use" has no site-level answer.
//
//   api      ../corpus                      committed, public, `scope: api`.
//                                           True of any Flow PT site.
//   site     ../corpus.local/site           gitignored, `scope: site`.
//                                           True of one Flow PT site.
//   project  ../corpus.local/projects/<id>  gitignored, `scope: project`.
//                                           True of one project inside it.
//
// The overlay is optional and an absent `corpus.local/` is the normal case.
// Every page renders complete without it, the reading-level switch is not
// drawn, and nothing links to a section that is not there.
//
// OVERLAY CONTRACT (see site/README.md for the long version)
//
//   corpus.local/site/findings/<nnn>_<slug>.md
//   corpus.local/site/findings/field_types/<type>.md
//   corpus.local/site/findings/entity_types/<Type>.md
//   corpus.local/site/recipes/<nnn>_<slug>.md
//   corpus.local/projects/<id>/findings/<nnn>_<slug>.md
//   corpus.local/projects/<id>/findings/field_types/<type>.md
//   corpus.local/projects/<id>/findings/entity_types/<Type>.md
//   corpus.local/projects/<id>/recipes/<nnn>_<slug>.md
//
//   Frontmatter, same shape as the shipped corpus:
//     ---
//     tags: [version, status]
//     scope: site
//     verdict: One line. What a reader of this site should do.
//     ---
//     # <heading>
//
//   A `scope: project` file also carries `project: <name>`, naming which
//   project it was measured on. `probes/check_corpus.py` enforces both.
//
//   The scope a file declares has to match the directory it sits in, so a
//   local measurement can never be published by mistake and a project number
//   can never be filed as true of the whole site.
//
//   A file whose slug matches a shipped entry renders on that entry's page,
//   below the shipped card. A file with no shipped counterpart is a row in the
//   same list, and gets the same page, with no API card on it. The overlay is
//   depth on the pages a reader is already on; it has no destination of its
//   own. Nothing has to be registered.

import fs from 'node:fs';
import path from 'node:path';
import { OVERLAY_DIR } from '$lib/site.js';

// Found by walking up from the working directory looking for `corpus/`, so the
// build works from `site/` and from the repository root alike.
//
// `import.meta.url` is deliberately not used: Vite rewrites it to the bundled
// chunk's location during `vite build`, which resolves to a directory that
// holds no corpus and yields an empty site with no error.
function findRepoRoot() {
	let dir = process.cwd();
	for (let up = 0; up < 6; up++) {
		if (fs.existsSync(path.join(dir, 'corpus', 'INDEX.md'))) return dir;
		const parent = path.dirname(dir);
		if (parent === dir) break;
		dir = parent;
	}
	// Loud, because an empty corpus renders as a site that merely looks thin.
	throw new Error(
		`[corpus] no corpus/INDEX.md found above ${process.cwd()}. ` +
			`Run the site from inside the sg-groundtruth repository.`
	);
}

const repoRoot = findRepoRoot();

const overlayRoot = path.join(repoRoot, OVERLAY_DIR);

export const SHIPPED = {
	id: 'api',
	level: 'api',
	project: null,
	root: path.join(repoRoot, 'corpus'),
	// A shipped entry is published only if it claims to generalise.
	scope: 'api',
	label: 'Flow PT REST API'
};

export const SITE = {
	id: 'site',
	level: 'site',
	project: null,
	root: path.join(overlayRoot, 'site'),
	scope: 'site',
	label: 'This site'
};

// One source per directory under corpus.local/projects/. The directory name is
// the id; the display name comes from the `project:` key its files carry.
export function projectSources() {
	const dir = path.join(overlayRoot, 'projects');
	if (!fs.existsSync(dir)) return [];
	return fs
		.readdirSync(dir, { withFileTypes: true })
		.filter((d) => d.isDirectory())
		.map((d) => d.name)
		.sort()
		.map((id) => ({
			id: `project:${id}`,
			level: 'project',
			project: id,
			root: path.join(dir, id),
			scope: 'project',
			label: id
		}));
}

// Both sources use the same groups and the same directory layout. A group is
// the only thing a route needs to exist; adding one here gives the overlay the
// matching directory for free.
//
// `entity_types` slugs are schema names (`Version`, `PublishedFile`) and keep
// their capitalisation in the URL, because that is the string the API answers
// to. Every other group is lowercase.
export const GROUPS = [
	{ id: 'findings', dir: 'findings', base: '/findings', title: 'Findings' },
	{ id: 'field_types', dir: 'findings/field_types', base: '/field-types', title: 'Field types' },
	{
		id: 'entity_types',
		dir: 'findings/entity_types',
		base: '/entity-types',
		title: 'Entity types'
	},
	{ id: 'recipes', dir: 'recipes', base: '/recipes', title: 'Recipes' }
];
