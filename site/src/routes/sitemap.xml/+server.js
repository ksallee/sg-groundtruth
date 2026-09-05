import { sitemap } from '$lib/content/agents.js';

export const prerender = true;

export const GET = () =>
	new Response(sitemap(), { headers: { 'content-type': 'application/xml; charset=utf-8' } });
