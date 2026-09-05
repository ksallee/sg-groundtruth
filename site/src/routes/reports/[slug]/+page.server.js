import { error } from '@sveltejs/kit';
import { entry, slugs } from '$lib/content/corpus.js';

export function entries() {
	return slugs('reports').map((slug) => ({ slug }));
}

export function load({ params }) {
	const found = entry('reports', params.slug);
	if (!found) error(404, `No report ${params.slug}`);
	return { entry: found };
}
