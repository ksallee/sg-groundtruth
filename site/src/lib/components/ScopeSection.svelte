<script>
	import ScopeMark from './ScopeMark.svelte';

	// One section of an entry page: what the API does, what one site configures,
	// or what one project does. It starts with its badge and then its content,
	// with no box around it; the API section is drawn exactly like the others.
	// `id` is the anchor the switch scrolls to. `pinned` is true while the reader
	// is inside this section; the badge is drawn only then.
	let { level = 'api', project = '', id = '', badge = true, pinned = false, children } = $props();
</script>

<section class="scoped" data-scope={level} {id}>
	{#if badge}
		<div class="pin" class:on={pinned}><ScopeMark {level} {project} /></div>
	{/if}
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

	/* The badge appears at the top of the viewport once the reader is inside
	   the section, stays there while the content scrolls under it, and hands
	   over to the next section's badge when that arrives. Until then the strip
	   holds its place unseen, so nothing moves. The strip fades the passing
	   content out: page colour at the badge, nothing --pin-fade below. It is
	   also the gap to the section's first block. No transition: it is there or
	   it is not. */
	.pin {
		visibility: hidden;
		position: sticky;
		top: 0;
		z-index: 2;
		padding-top: var(--space-3);
		padding-bottom: var(--pin-fade);
		margin-top: calc(-1 * var(--space-3));
		margin-bottom: calc(-1 * var(--gap-prose));
		background: linear-gradient(
			to bottom,
			var(--ground) 0,
			var(--ground) calc(100% - var(--pin-fade)),
			transparent 100%
		);
	}

	.pin.on {
		visibility: visible;
	}

	/* Under the phone's bar rather than behind it. */
	@media (max-width: 63.99rem) {
		.pin {
			top: 3.5rem;
		}

		.scoped[id] {
			scroll-margin-top: calc(3.5rem + var(--space-4));
		}
	}
</style>
