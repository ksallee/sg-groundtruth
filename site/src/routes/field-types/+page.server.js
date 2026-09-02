import { index } from '$lib/content/corpus.js';

export function load() {
	const data = index();
	return { entries: data.fieldTypes, counts: data.counts };
}
