import { index } from '$lib/content/corpus.js';
import { OVERLAY_DIR } from '$lib/site.js';

export function load() {
	const data = index();
	return {
		counts: data.counts,
		hasOverlay: data.hasOverlay,
		// The directory name is declared once, in $lib/site.js. The page reads it
		// rather than repeating it, so renaming the overlay is a one-line change.
		overlayDir: OVERLAY_DIR
	};
}
