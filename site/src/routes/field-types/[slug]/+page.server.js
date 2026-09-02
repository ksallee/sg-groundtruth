import { error } from '@sveltejs/kit';
import { entry, slugs } from '$lib/content/corpus.js';

export function entries() {
	return slugs('field_types').map((slug) => ({ slug }));
}

export function load({ params }) {
	const found = entry('field_types', params.slug);
	if (!found) error(404, `No field type ${params.slug}`);
	return { entry: found };
}
