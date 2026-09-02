import { filterIndex, filterTypes } from '$lib/content/corpus.js';

// Both halves are derived from the field-type cards, so neither can drift from
// them. `filterIndex` throws if a card records no operator vocabulary;
// `filterTypes` throws if it records one and no value matrix, or if the matrix
// never exercises an operator the API listed. Either fails the build and names
// the file rather than rendering a blank row.
export function load() {
	return { families: filterIndex(), types: filterTypes() };
}
