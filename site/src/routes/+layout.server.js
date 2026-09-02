import { index } from '$lib/content/corpus.js';

// The nav and the reading level switch need to know what the overlay holds.
// Loaded once for every page rather than per route.
export function load() {
	const { hasOverlay, hasSite, projects, counts } = index();
	return { hasOverlay, hasSite, projects, counts };
}
