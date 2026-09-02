import { index } from '$lib/content/corpus.js';

export function load() {
	const data = index();
	return { entries: data.recipes, counts: data.counts };
}
