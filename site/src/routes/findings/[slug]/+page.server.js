import { error } from '@sveltejs/kit';
import { entry, slugs } from '$lib/content/corpus.js';

export function entries() {
	return slugs('findings').map((slug) => ({ slug }));
}

export function load({ params }) {
	const found = entry('findings', params.slug);
	if (!found) error(404, `No finding ${params.slug}`);
	return { entry: found };
}
