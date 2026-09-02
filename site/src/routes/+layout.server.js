import { index } from '$lib/content/corpus.js';

// The nav needs to know whether a local overlay exists. Loaded once for every
// page rather than per route.
export function load() {
	const { hasOverlay, counts } = index();
	return { hasOverlay, counts };
}
