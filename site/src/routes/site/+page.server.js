import path from 'node:path';
import { index, localEntries } from '$lib/content/corpus.js';
import { OVERLAY } from '$lib/content/sources.js';

// This route exists in both states. With an overlay it renders the local
// entries. Without one it states the contract, so a person who cloned the repo
// lands on instructions rather than an empty page. The public navigation links
// here only when an overlay was found.
export function load() {
	const data = index();
	return {
		// Rendered in full, so overlay content needs no route of its own.
		locals: localEntries(),
		attached: [
			...data.findings.filter((e) => e.hasLocal),
			...data.fieldTypes.filter((e) => e.hasLocal),
			...data.recipes.filter((e) => e.hasLocal)
		],
		hasOverlay: data.hasOverlay,
		overlayDir: path.basename(OVERLAY.root)
	};
}
