import { filterIndex, index } from '$lib/content/corpus.js';

// Every number on this page is read off the corpus. `unfilterable` is the size
// of the "Not filterable" family, so a data type that gains or loses a
// vocabulary changes the sentence without an edit here.
export function load() {
	const families = filterIndex();
	const none = families.find((f) => f.id === 'none');
	return {
		counts: index().counts,
		filters: {
			types: families.reduce((n, f) => n + f.rows.length, 0),
			families: families.length,
			unfilterable: none ? none.rows.length : 0
		}
	};
}
