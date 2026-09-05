import { text } from '@sveltejs/kit';
import { robots } from '$lib/content/agents.js';

export const prerender = true;

export const GET = () => text(robots());
