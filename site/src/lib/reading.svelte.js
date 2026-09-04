// The reading level: the deepest the build can show, always.
//
// `site` adds what one Flow Production Tracking site configures on top of the
// API content. `project` adds one project on top of both, one at a time: with
// several in the overlay the foot of the sidebar picks which, and every section,
// dot and count reads that choice. A public build has no overlay and shows the
// API alone.

// Exported as an object and mutated, never reassigned, which is what lets a
// component read it reactively.
export const reading = $state({ level: 'api', project: null });

let restored = false;

// `hasSite` and `projects` describe the overlay this build read.
export function restore({ hasSite = false, projects = [] } = {}) {
	if (restored) return;
	restored = true;
	if (projects.length) {
		reading.level = 'project';
		reading.project = projects[0].id;
	} else if (hasSite) {
		reading.level = 'site';
		reading.project = null;
	} else {
		reading.level = 'api';
		reading.project = null;
	}
}

// One rule, read by every place that renders overlay content.
export function shows(local) {
	if (local.level === 'site') return reading.level === 'site' || reading.level === 'project';
	if (local.level === 'project') {
		if (reading.level !== 'project') return false;
		return local.project === reading.project;
	}
	return true;
}

export function visible(locals = []) {
	return locals.filter(shows);
}

// True when more than one kind of information can be on a page.
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
