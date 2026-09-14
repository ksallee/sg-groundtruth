import { doorsByKind } from '$lib/content/doors.js';
import { entrySpread } from '$lib/content/markdown.js';
import { llmsTxt } from '$lib/content/agents.js';

export function load() {
	return { kinds: doorsByKind(), entries: entrySpread(), llmsBytes: llmsTxt().length };
}
