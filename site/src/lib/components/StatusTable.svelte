<script>
	// One status, drawn one way, everywhere. A status is four things a reader
	// needs at once: the icon, the label a person sees, the code the API stores,
	// and the colour. Splitting them across pages is how a picker ends up
	// showing a code nobody recognises, or a colour with no name.
	//
	// The same component draws the statuses section on /reference, the usable
	// set on an entity type, and the per-project subtraction in 009_status_lists,
	// so the three cannot drift.
	//
	// Icons resolve down a ladder, because only some are reachable:
	//   image_map  stock. A cell in the site's sprite, fetched at build time.
	//   image      custom upload. Carries its own bytes as a data: URI.
	//   html       custom text badge. There is no image, only a label.
	//   none       no credentials at build time, or a code the site never sent.
	// The last rung is the normal case for a clone with no site configured, so
	// the table stays correct and merely quieter.
	import icons from '$lib/content/status-icons.json';

	let { codes = [], hidden = [], caption = '' } = $props();

	const rows = $derived(
		[...codes.map((c) => ({ code: c, hidden: false })), ...hidden.map((c) => ({ code: c, hidden: true }))].map(
			(r) => ({ ...r, s: icons.statuses?.[r.code] ?? null })
		)
	);
	const cell = (s) => (s?.kind === 'image_map' && s.key ? (icons.cells?.[s.key] ?? null) : null);
</script>

<table class="statuses">
	{#if caption}<caption>{caption}</caption>{/if}
	<tbody>
		{#each rows as r (r.code)}
			<tr class:hidden={r.hidden}>
				<td class="icon">
					{#if cell(r.s) && icons.sprite}
						{@const c = cell(r.s)}
						<span class="chip"
							><i
								style="width:{c.w}px;height:{c.h}px;background-position:{c.x}px {c.y}px"
							></i></span
						>
					{:else if r.s?.data}
						<span class="chip"><img src={r.s.data} alt="" width="16" height="16" /></span>
					{:else if r.s?.html}
						<span class="chip text">{r.s.html}</span>
					{:else}
						<span class="chip empty"></span>
					{/if}
				</td>
				<td class="name">
					{r.s?.name ?? r.code}
					<code>{r.code}</code>
					{#if r.hidden}<span class="flag">hidden here</span>{/if}
				</td>
				<td class="colour">
					{#if r.s?.bg}
						<span class="swatch" style="background:rgb({r.s.bg})"></span>
						<span class="rgb">{r.s.bg}</span>
					{:else}
						<span class="rgb none">no colour</span>
					{/if}
				</td>
			</tr>
		{/each}
	</tbody>
</table>

<style>
	.statuses {
		border-collapse: collapse;
		width: 100%;
		font-size: var(--text-sm);
	}

	caption {
		text-align: left;
		color: var(--ink-muted);
		font-size: var(--text-xs);
		padding-bottom: var(--space-2);
	}

	td {
		padding: var(--space-1) var(--space-3) var(--space-1) 0;
		border-bottom: 1px solid var(--rule);
		vertical-align: middle;
	}

	.icon {
		width: 1.75rem;
		padding-right: var(--space-2);
	}

	/* Fixed light in both themes: see --icon-chip. */
	.chip {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.375rem;
		height: 1.375rem;
		background: var(--icon-chip);
		border-radius: var(--radius-sm);
	}

	.chip i {
		display: block;
		background-image: url(/status-sprite.png);
		background-repeat: no-repeat;
	}

	.chip img {
		display: block;
	}

	.chip.text {
		width: auto;
		padding-inline: var(--space-2);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: oklch(0.3 0 0);
	}

	.chip.empty {
		background: transparent;
		box-shadow: inset 0 0 0 1px var(--rule);
	}

	.name {
		width: 100%;
	}

	.name code {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.flag {
		margin-inline-start: var(--space-2);
		font-size: var(--text-xs);
		color: var(--accent-project);
	}

	tr.hidden .name,
	tr.hidden .colour {
		opacity: 0.55;
	}

	.colour {
		white-space: nowrap;
	}

	.swatch {
		display: inline-block;
		width: 1.625rem;
		height: 0.8125rem;
		border-radius: var(--radius-sm);
		box-shadow: inset 0 0 0 1px var(--icon-chip-rule);
		vertical-align: -1px;
	}

	.rgb {
		margin-inline-start: var(--space-2);
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		color: var(--ink-muted);
	}

	.rgb.none {
		margin-inline-start: 0;
		font-style: italic;
	}
</style>
