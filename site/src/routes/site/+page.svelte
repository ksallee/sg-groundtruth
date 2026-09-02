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
			Measurements of one Flow PT installation, read from <code>{data.overlayDir}/</code>. They
			describe a configuration, not the API, and do not transfer to another site.
		</p>
	</header>

	{#if data.hasOverlay}
		{#if data.attached.length}
			<section>
				<h2>Attached to a published entry</h2>
				<p>
					These local measurements render at the bottom of the shipped card they extend, rather than
					on this page.
				</p>
				<EntryList entries={data.attached} showTags={false} />
			</section>
		{/if}

		{#each data.locals as local (local.anchor)}
			<LocalBand title={local.name}>
				<div id={local.anchor} class="local-entry">
					<p class="verdict">{local.verdict}</p>
					<Prose html={local.html} tone="site" />
				</div>
			</LocalBand>
		{/each}
	{:else}
		<!-- The public build is this branch. Nothing links here from the navigation
		     in this state, so no visitor reaches an empty section. -->
		<section class="empty">
			<h2>No overlay found</h2>
			<p>
				This build read no <code>{data.overlayDir}/</code> directory, so it shows the shipped corpus
				only. To document your own site, generate markdown into that directory and rebuild.
				<a href="/use#overlay">The overlay contract</a> gives the filenames and the frontmatter.
			</p>
			<p>
				The directory is gitignored. It is never committed and never reaches a public deployment.
			</p>
		</section>
	{/if}
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

	.empty {
		border: var(--border) dashed var(--rule-strong);
		border-radius: var(--radius);
		padding: var(--space-5);
	}
</style>
