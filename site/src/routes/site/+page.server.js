import { index, localEntries } from '$lib/content/corpus.js';
import { OVERLAY_DIR } from '$lib/site.js';

// This route exists in both states. With an overlay it inventories everything
// the overlay holds, at every level, whatever reading level is in force. Without
// one it states the contract, so a person who cloned the repository lands on
// instructions rather than an empty page. The navigation links here only when an
// overlay was found.
export function load() {
	const data = index();
	const shipped = [...data.findings, ...data.fieldTypes, ...data.entityTypes, ...data.recipes];
	const locals = localEntries();

	const band = (level, id, label) => ({
		level,
		id,
		label,
		attached: shipped.filter((e) => e.locals.some((l) => l.level === level && l.project === id)),
		locals: locals.filter((e) => e.level === level && e.project === id)
	});

	const levels = [
		...(data.hasSite ? [band('site', null, 'This site')] : []),
		...data.projects.map((p) => band('project', p.id, p.label))
	];

	return { levels, hasOverlay: data.hasOverlay, overlayDir: OVERLAY_DIR };
}
