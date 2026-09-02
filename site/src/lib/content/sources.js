// THE SEAM between the two content sources. Everything about where content comes
// from, and what is allowed to be published from each source, is decided here and
// nowhere else. Routes never touch the filesystem.
//
// SHIPPED  ../corpus          committed, public, `scope: api` only.
//                             How the Flow PT REST API behaves anywhere.
// OVERLAY  ../corpus.local    gitignored, generated per site, `scope: site` only.
//                             How one Flow PT site is configured. Never deploys,
//                             because it is never committed.
//
// The overlay is optional. An absent or empty `corpus.local/` is the normal case:
// every page below renders complete without it, and nothing links to a section
// that is not there.
//
// OVERLAY CONTRACT (see site/README.md for the long version)
//
//   corpus.local/findings/<nnn>_<slug>.md          a measurement of one site
//   corpus.local/findings/field_types/<type>.md    keyed to a data_type name
//   corpus.local/recipes/<nnn>_<slug>.md           a call made against one site
//
//   Frontmatter, same shape as the shipped corpus:
//     ---
//     tags: [version, status]
//     scope: site
//     verdict: One line. What a reader of this site should do.
//     ---
//     # <heading>
//
//   `scope: site` is mandatory in the overlay and is rejected in the shipped
//   corpus, so a local measurement can never be published by mistake and a
//   general finding can never be filed as site-specific.
//
//   A file whose slug matches a shipped entry is rendered on that entry's page,
//   under its own labelled heading. A file with no shipped counterpart is listed
//   on /site as a local-only entry. Nothing else has to be registered.

import fs from 'node:fs';
import path from 'node:path';

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

export const SHIPPED = {
	id: 'shipped',
	root: path.join(repoRoot, 'corpus'),
	// A shipped entry is published only if it claims to generalise.
	scope: 'api',
	label: 'Flow PT REST API',
	note: 'Behaviour that holds on any Flow PT site.'
};

export const OVERLAY = {
	id: 'overlay',
	root: path.join(repoRoot, 'corpus.local'),
	// An overlay entry is a measurement of one site and is labelled as such.
	scope: 'site',
	label: 'This site',
	note: 'Measured on the site this build was pointed at. It does not generalise.'
};

// Both sources use the same three groups and the same directory layout.
export const GROUPS = [
	{ id: 'findings', dir: 'findings', base: '/findings', title: 'Findings' },
	{ id: 'field_types', dir: 'findings/field_types', base: '/field-types', title: 'Field types' },
	{ id: 'recipes', dir: 'recipes', base: '/recipes', title: 'Recipes' }
];
