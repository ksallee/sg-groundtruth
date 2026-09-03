import { sveltekit } from '@sveltejs/kit/vite';

// Which overlay directory the build reads, substituted at build time so it reaches the client as well
// as the server. A default lives here rather than in a .env file, so a fresh clone builds with no
// setup: an absent variable is the normal case, not a broken one.
//
// `corpus.local` is the gitignored overlay a reader builds for their own site. The public deploy sets
// PUBLIC_OVERLAY_SOURCE=corpus.example in vercel.json. See docs/example-overlay.md.
const overlaySource = process.env.PUBLIC_OVERLAY_SOURCE || 'corpus.local';

export default {
	plugins: [sveltekit()],
	define: { __OVERLAY_SOURCE__: JSON.stringify(overlaySource) }
};
