import { error } from '@sveltejs/kit';
import { entry, slugs } from '$lib/content/corpus.js';

// Slugs are schema names, so the URL is /entity-types/PublishedFile and not a
// lowercased spelling of it. That is the string the API answers to.
export function entries() {
	return slugs('entity_types').map((slug) => ({ slug }));
}

export function load({ params }) {
	const found = entry('entity_types', params.slug);
	if (!found) error(404, `No entity type ${params.slug}`);
	return { entry: found };
}
