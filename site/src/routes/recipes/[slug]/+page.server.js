import { error } from '@sveltejs/kit';
import { entry, slugs } from '$lib/content/corpus.js';

export function entries() {
	return slugs('recipes').map((slug) => ({ slug }));
}

export function load({ params }) {
	const found = entry('recipes', params.slug);
	if (!found) error(404, `No recipe ${params.slug}`);
	return { entry: found };
}
