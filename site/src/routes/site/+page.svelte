<script>
	import EntryList from '$lib/components/EntryList.svelte';
	import LocalBand from '$lib/components/LocalBand.svelte';
	import Prose from '$lib/components/Prose.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>This site: local measurements</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="page">
	<header>
		<h1>This site</h1>
		<p class="lede">
			Measurements read from <code>{data.overlayDir}/</code>. They describe one Flow Production
			Tracking installation, and one project inside it, rather than the API. They do not transfer to
			another site.
		</p>
		{#if data.hasOverlay}
			<p class="note">
				This page inventories everything the overlay holds, at every level. The switch in the header
				decides which of it renders on the rest of the site.
			</p>
		{/if}
	</header>

	{#each data.levels as band (band.level + band.id)}
		<section>
			<h2>{band.label}</h2>

			{#if band.attached.length}
				<p>
					These measurements render beside the shipped card they extend, on that entry's own page.
				</p>
				<EntryList entries={band.attached} showTags={false} />
			{/if}

			{#each band.locals as local (local.anchor)}
				<LocalBand level={local.level} project={local.projectLabel} title={local.name}>
					<div id={local.anchor} class="local-entry">
						<p class="verdict" class:project={local.level === 'project'}>{local.verdict}</p>
						<Prose html={local.html} tone={local.level} />
					</div>
				</LocalBand>
			{/each}
		</section>
	{:else}
		<!-- The public build is this branch. Nothing links here from the navigation
		     in this state, so no visitor reaches an empty section. -->
		<section class="empty">
			<h2>No overlay found</h2>
			<p>
				This build read no <code>{data.overlayDir}/</code> directory, so it shows the shipped corpus
				only, and the reading level switch is not drawn. To document your own site, generate markdown
				into that directory and rebuild.
				<a href="/use#overlay">The overlay contract</a> gives the filenames and the frontmatter.
			</p>
			<p>
				The directory is gitignored. It is never committed and never reaches a public deployment.
			</p>
		</section>
	{/each}
</div>

<style>
	.page {
		max-width: var(--wide);
		margin-inline: auto;
		padding: var(--space-6) var(--gutter) var(--space-7);
		display: grid;
		gap: var(--space-5);
	}

	header {
		display: grid;
		gap: var(--space-3);
		max-width: var(--measure);
	}

	h1 {
		font-size: var(--text-xl);
	}

	h2 {
		font-size: var(--text-lg);
	}

	section {
		display: grid;
		gap: var(--space-3);
	}

	p {
		color: var(--ink-muted);
		max-width: var(--measure);
	}

	.note {
		font-size: var(--text-sm);
		border-left: 3px solid var(--rule-strong);
		padding-left: var(--space-4);
	}

	.local-entry {
		display: grid;
		gap: var(--space-4);
		scroll-margin-top: var(--space-8);
	}

	.verdict {
		color: var(--ink);
		border-left: 3px solid var(--accent-local);
		padding-left: var(--space-4);
	}

	.verdict.project {
		border-left-color: var(--accent-project);
	}

	.empty {
		border: var(--border) dashed var(--rule-strong);
		border-radius: var(--radius);
		padding: var(--space-5);
	}
</style>
