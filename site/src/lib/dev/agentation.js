// The Agentation feedback toolbar, on the dev server only. It is a React
// component, so it gets a React root of its own in a host element appended to
// the body; the Svelte page never knows it is there. Loaded from the layout
// behind `import.meta.env.DEV`, so nothing of it reaches a build.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { Agentation } from 'agentation';

export function mount() {
	if (document.getElementById('agentation-host')) return;
	const host = document.createElement('div');
	host.id = 'agentation-host';
	document.body.appendChild(host);
	createRoot(host).render(React.createElement(Agentation));
}
