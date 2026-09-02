import { index } from '$lib/content/corpus.js';

export function load() {
	return { counts: index().counts };
}
