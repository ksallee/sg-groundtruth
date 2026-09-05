import { text } from '@sveltejs/kit';
import { llmsTxt } from '$lib/content/agents.js';

export const prerender = true;

export const GET = () => text(llmsTxt());
