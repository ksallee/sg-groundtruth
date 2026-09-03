<script>
	import ScopeMark from './ScopeMark.svelte';

	// One section of an entry page: what the API does, what one site configures,
	// or what one project does. It starts with its badge and then its content,
	// with no box around it; the API section is drawn exactly like the others.
	// `id` is the anchor the switch at the top of the page scrolls to.
	let { level = 'api', project = '', id = '', badge = true, children } = $props();
</script>

<section class="scoped" data-scope={level} {id}>
	{#if badge}<ScopeMark {level} {project} />{/if}
	{@render children?.()}
</section>

<style>
	.scoped {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--gap-prose);
		justify-items: start;
	}

	.scoped > :global(*) {
		width: 100%;
	}

	.scoped > :global(.badge) {
		width: auto;
	}
</style>
