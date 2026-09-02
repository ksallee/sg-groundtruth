import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
export default {
	kit: {
		// Every page is prerendered to static HTML at build time. Nothing runs
		// on a server, and an LLM fetching a URL gets the full document.
		adapter: adapter({ fallback: null })
	}
};
