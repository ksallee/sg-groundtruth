import { error } from '@sveltejs/kit';
import { door, doorNames } from '$lib/content/doors.js';

export const entries = () => doorNames().map((name) => ({ name }));

export function load({ params }) {
	const found = door(params.name);
	if (!found) error(404, `No door ${params.name}`);
	return { door: found };
}
