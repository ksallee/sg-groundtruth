// The reading level: one global choice, applied to every page, remembered
// across navigation and reloads.
//
// It is additive, not a filter. `site` adds what one Flow PT site configures on
// top of the API content; `project` adds one project on top of both. The API
// content is on the page at every level.
//
// A public build has no overlay, so `api` is the only level it can hold and the
// switch is never drawn.

const KEY = 'sg-groundtruth.reading-level';

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
	if (id && projects.some((p) => p.id === id)) {
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
		return reading.level === 'project' && local.project === reading.project;
	}
	return true;
}

export function visible(locals = []) {
	return locals.filter(shows);
}
