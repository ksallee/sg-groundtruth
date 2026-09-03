// The annotation feedback toolbar, on the dev server only: click an element,
// write a note, copy every note as one prompt for an agent. It is a custom
// element and appends itself to the body, so the Svelte page never knows it is
// there. Loaded from the layout behind `import.meta.env.DEV`, so nothing of it
// reaches a build.
//
// `dark` rather than `auto`: the site renders dark whatever the OS is set to,
// and a light toolbar over it is unreadable.
import { createAnnotation } from 'agent-ui-annotation/vanilla';

export function mount() {
	if (document.querySelector('agent-ui-annotation')) return;
	createAnnotation({ theme: 'dark' });
}
