// The reading level: one global choice, applied to every page, remembered
// across navigation and reloads.
//
// It is depth on the page a reader is already on, not a destination and not a
// filter. `site` adds what one Flow Production Tracking site configures on top
// of the API content. `project` adds one project, or every project at once, on
// top of both. Nothing is removed as the level rises; entries and sections are
// added.
//
// A public build has no overlay, so `api` is the only level it can hold and the
// switch is never drawn.

const KEY = 'sg-groundtruth.reading-level';

// The union of every project the overlay holds. A project id can never be this,
// because a directory named `*` is not one a filesystem hands back here.
export const ALL = '*';

// Exported as an object and mutated, never reassigned, which is what lets a
// component read it reactively.
export const reading = $state({ level: 'api', project: null });

// localStorage throws in some privacy modes and returns nothing on a first
// visit. Both land on `api`, which is what a reader gets with no overlay.
function stored() {
	try {
		return localStorage.getItem(KEY) ?? '';
	} catch {
		return '';
	}
}

function remember(value) {
	try {
		localStorage.setItem(KEY, value);
	} catch {
		// Nothing to do. The choice holds for this session and is lost on reload.
	}
}

let restored = false;

// `hasSite` and `projects` describe the overlay this build read. A remembered
// level the current build cannot show falls back to `api` rather than leaving
// the switch pointing at nothing. Read once: after that the choice on screen is
// the truth, and a failed write must not revert it on the next navigation.
export function restore({ hasSite = false, projects = [] } = {}) {
	if (restored) return;
	restored = true;
	const value = stored();
	if (value === 'site' && hasSite) {
		reading.level = 'site';
		reading.project = null;
		return;
	}
	const id = value.startsWith('project:') ? value.slice('project:'.length) : '';
	const known = id === ALL ? projects.length > 0 : projects.some((p) => p.id === id);
	if (id && known) {
		reading.level = 'project';
		reading.project = id;
		return;
	}
	reading.level = 'api';
	reading.project = null;
}

export function choose(level, project = null) {
	reading.level = level;
	reading.project = level === 'project' ? project : null;
	remember(level === 'project' ? `project:${project}` : level);
}

// One rule, read by every place that renders overlay content.
export function shows(local) {
	if (local.level === 'site') return reading.level === 'site' || reading.level === 'project';
	if (local.level === 'project') {
		if (reading.level !== 'project') return false;
		return reading.project === ALL || local.project === reading.project;
	}
	return true;
}

export function visible(locals = []) {
	return locals.filter(shows);
}

// True when more than one kind of information can be on a page. At `api` there
// is only one, so no page draws a mark or a legend and a public build looks
// complete rather than annotated.
export function mixed() {
	return reading.level !== 'api';
}

// The key a per-level count is filed under. `corpus.js` builds one entry per
// level the overlay can show, so a count never has to be recomputed in a
// component from data the page did not load.
export function levelKey() {
	return reading.level === 'project' ? `project:${reading.project}` : reading.level;
}

export function countsAt(counts) {
	return counts[levelKey()] ?? counts.api;
}
