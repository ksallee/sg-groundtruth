import { index } from '$lib/content/corpus.js';
import { OVERLAY } from '$lib/content/sources.js';
import path from 'node:path';

export function load() {
	const data = index();
	return {
		counts: data.counts,
		hasOverlay: data.hasOverlay,
		// The directory name is declared once, in sources.js. The page reads it
		// rather than repeating it, so renaming the overlay is a one-line change.
		overlayDir: path.basename(OVERLAY.root)
	};
}
