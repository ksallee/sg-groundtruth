import { index } from '$lib/content/corpus.js';
import { mcpToolNames } from '$lib/content/mcp.js';
import { indexBytes } from '$lib/content/markdown.js';
import { llmsTxt } from '$lib/content/agents.js';
import { OVERLAY_DIR } from '$lib/site.js';

export function load() {
	const data = index();
	return {
		counts: data.counts,
		mcpTools: mcpToolNames().length,
		indexBytes: indexBytes(),
		llmsBytes: llmsTxt().length,
		hasOverlay: data.hasOverlay,
		// The directory name is declared once, in $lib/site.js. The page reads it
		// rather than repeating it, so renaming the overlay is a one-line change.
		overlayDir: OVERLAY_DIR
	};
}
