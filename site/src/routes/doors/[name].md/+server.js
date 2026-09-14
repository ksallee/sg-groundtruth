import { error, text } from '@sveltejs/kit';
import { doorNames, readDoor } from '$lib/content/doors.js';

// The door itself, byte for byte, the way an entry twin is its shipped file.
// Frontmatter-free because a door carries none: it is generated, and what it
// selects on is the name.
export const prerender = true;

export const entries = () => doorNames().map((name) => ({ name }));

export const GET = ({ params }) => {
	const raw = readDoor(params.name);
	if (raw === null) error(404, `No door ${params.name}`);
	return text(raw, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
