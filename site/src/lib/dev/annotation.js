// The annotation toolbar, on the dev server only: click an element, write a
// note, copy every note as one prompt for an agent. It is a custom element,
// appended to the body by `createAnnotation`, so the Svelte page never knows it
// is there. Loaded from the layout behind `import.meta.env.DEV`, so nothing of
// it reaches a build.
import { createAnnotation } from 'agent-ui-annotation';

let instance = null;

export function mount() {
	if (instance) return instance;
	instance = createAnnotation({
		// The site has one appearance; `auto` would read the OS instead.
		theme: 'dark',
		outputLevel: 'standard',
		// Which page a note was written on. The selector alone does not say.
		onBeforeAnnotationCreate: () => ({ context: { route: window.location.pathname } })
	});
	return instance;
}
