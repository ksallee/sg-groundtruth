import { index } from '$lib/content/corpus.js';

export function load() {
	return { entries: index().reports };
}
