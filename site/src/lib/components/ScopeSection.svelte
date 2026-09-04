<script>
	import ScopeMark from './ScopeMark.svelte';

	// One section of an entry page: what the API does, what one site configures,
	// or what one project does. It starts with its badge and then its content,
	// with no box around it; the API section is drawn exactly like the others.
	// `id` is the anchor the switch scrolls to.
	let { level = 'api', project = '', id = '', children } = $props();
</script>

<section class="scoped" data-scope={level} {id}>
	<div class="pin"><ScopeMark {level} {project} /></div>
	{@render children?.()}
</section>

<style>
	.scoped {
		display: grid;
		grid-template-columns: var(--col);
		gap: var(--gap-prose);
	}

	.scoped[id] {
		scroll-margin-top: var(--space-4);
	}

	/* The badge sits at the head of its section, pins at --pin-top while the
	   content scrolls under it, and hands over to the next section's badge when
	   that arrives. The strip below it fades the passing content out: page
	   colour for --pin-fade-start below the badge, then nothing over --pin-fade.
	   The strip is also the gap to the section's first block, so nothing moves
	   when it pins. Every length is a token in tokens.css. */
	.pin {
		position: sticky;
		top: var(--pin-top);
		z-index: 2;
		padding-top: var(--pin-pad);
		padding-bottom: calc(var(--pin-fade-start) + var(--pin-fade));
		margin-top: calc(-1 * var(--pin-pad));
		margin-bottom: calc(-1 * var(--gap-prose));
		background: linear-gradient(
			to bottom,
			var(--ground) 0,
			var(--ground) calc(100% - var(--pin-fade)),
			transparent 100%
		);
	}

	/* Under the phone's bar rather than behind it. */
	@media (max-width: 63.99rem) {
		.pin {
			top: calc(3.5rem + var(--pin-top));
		}

		.scoped[id] {
			scroll-margin-top: calc(3.5rem + var(--space-4));
		}
	}
</style>
