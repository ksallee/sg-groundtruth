import { filterIndex, index } from '$lib/content/corpus.js';

// The table is derived from the field-type cards, so it cannot drift from them.
// `filterIndex` throws if a card records no operator vocabulary, which fails the
// build and names the file rather than rendering a blank row.
export function load() {
	return { families: filterIndex(), counts: index().counts };
}
