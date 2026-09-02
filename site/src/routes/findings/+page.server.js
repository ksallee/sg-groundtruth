import { index } from '$lib/content/corpus.js';

export function load() {
	const data = index();
	return { findings: data.findings, recipes: data.recipes, counts: data.counts };
}
