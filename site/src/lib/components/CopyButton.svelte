<script>
	// Copies `text` to the clipboard. An icon button with a tooltip: "Copy" while
	// resting, "Copied" with a ticked box after a click. Both go when the
	// pointer leaves, and the button is back to Copy for the next hover.
	//
	// The two icons are the SDS strokes `copy` and `check-square`, inlined so
	// they take the button's colour.
	let { text = '' } = $props();

	let copied = $state(false);

	async function copy() {
		await navigator.clipboard.writeText(text);
		copied = true;
	}

	const reset = () => (copied = false);
</script>

<button
	type="button"
	class="copy"
	class:copied
	aria-label={copied ? 'Copied' : 'Copy'}
	onclick={copy}
	onpointerleave={reset}
	onblur={reset}
>
	{#if copied}
		<svg viewBox="0 0 16 16" width="14" height="14" fill="none" aria-hidden="true">
			<g stroke="currentColor" stroke-width="1.23" stroke-linecap="round" stroke-linejoin="round">
				<rect x="1.49" y="1.49" width="13.01" height="13.01" rx="1.52" />
				<path d="M4.97 7.95L7.28 10.05L11.5 5.94" />
			</g>
		</svg>
	{:else}
		<svg viewBox="0 0 16 16" width="14" height="14" fill="none" aria-hidden="true">
			<g stroke="currentColor" stroke-width="1.23" stroke-linecap="round" stroke-linejoin="round">
				<path
					d="M5.51 1.47L13.55 1.47A1 1 0 0 1 14.55 2.47L14.55 10.51A1 1 0 0 1 13.55 11.51L5.51 11.51A1 1 0 0 1 4.51 10.51L4.51 2.47A1 1 0 0 1 5.51 1.47Z"
				/>
				<path d="M1.55 5.47L1.55 13.95A0.56 0.56 0 0 0 2.11 14.51L10.56 14.51" />
			</g>
		</svg>
	{/if}
	<span class="tip" aria-hidden="true">{copied ? 'Copied' : 'Copy'}</span>
</button>

<style>
	.copy {
		position: relative;
		display: grid;
		place-items: center;
		width: 1.75rem;
		height: 1.75rem;
		border: 0;
		border-radius: 6px;
		background: none;
		color: var(--ink-muted);
		transition:
			color var(--duration) ease,
			background var(--duration) ease,
			transform var(--duration-press) var(--ease-out);
	}

	.copy:hover,
	.copy:focus-visible {
		color: var(--ink);
		background: var(--ground-sunken);
	}

	.copy:active {
		transform: scale(0.94);
	}

	.copy.copied {
		color: var(--accent-project);
	}

	/* To the left of the button, so it is never clipped by the slab's edge. */
	.tip {
		position: absolute;
		right: calc(100% + var(--space-2));
		top: 50%;
		transform: translate(2px, -50%);
		padding: 0.15rem var(--space-2);
		border-radius: var(--radius-sm);
		background: #000;
		border: var(--border) solid color-mix(in srgb, var(--ink) 10%, transparent);
		color: #fff;
		font-size: 0.75rem;
		line-height: 1.5;
		letter-spacing: var(--tracking-body);
		white-space: nowrap;
		pointer-events: none;
		opacity: 0;
		transition:
			opacity 125ms var(--ease-out),
			transform 125ms var(--ease-out);
	}

	.copy:hover .tip,
	.copy:focus-visible .tip {
		opacity: 1;
		transform: translate(0, -50%);
	}
</style>
