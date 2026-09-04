import { checkEndpoints, endpointsByFamily, index } from '$lib/content/corpus.js';

// `checkEndpoints` throws, naming the file, if a finding or recipe spells an
// endpoint no card is named by. Called for the throw, not the count: a broken
// join should fail the build rather than render a page that quietly lists less.
export function load() {
	checkEndpoints();
	const data = index();
	return { families: endpointsByFamily(data.endpoints), counts: data.counts };
}
