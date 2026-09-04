import { error } from '@sveltejs/kit';
import { entry, linksFor, slugs } from '$lib/content/corpus.js';

export function entries() {
	return slugs('endpoints').map((slug) => ({ slug }));
}

export function load({ params }) {
	const found = entry('endpoints', params.slug);
	if (!found) error(404, `No endpoint card ${params.slug}`);
	// The card's own citations, merged with every finding and recipe whose
	// `endpoints:` names this call. `linksFor` throws on a link to something this
	// build does not publish, so a dead link fails the build.
	return { entry: found, links: linksFor(found) };
}
