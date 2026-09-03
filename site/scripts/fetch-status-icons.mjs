// Build-time only. Fetches the statuses a site offers, their colours, and the stock icon sprite,
// and writes them where the build can read them. Nothing here is committed: both outputs are
// gitignored, so the repository ships no Autodesk artwork and a fresh clone builds without it.
//
// Credentials are optional and their absence is the normal case, exactly like corpus.local/.
// Without them this writes an empty payload and StatusTable falls back to colour and code.
//
// Runs in node on Vercel, where the Python probes never execute. The sprite discovery mirrors
// probe 010: the stock icons are not in the API, so the rule is read from the site's own
// stylesheet and never hardcoded.
import fs from 'node:fs/promises';
import path from 'node:path';

const OUT_JSON = path.resolve('src/lib/content/status-icons.json');
const OUT_PNG = path.resolve('static/status-sprite.png');
const CSS_PATH = '/dist/production/stylesheets/login.css';

const site = (process.env.FPT_API_SITE_URL || '').replace(/\/$/, '');
const name = process.env.FPT_API_SCRIPT_NAME;
const key = process.env.FPT_API_API_KEY;

async function empty(why) {
	await fs.mkdir(path.dirname(OUT_JSON), { recursive: true });
	await fs.writeFile(OUT_JSON, JSON.stringify({ available: false, why, statuses: {}, cells: {} }, null, '\t'));
	console.log(`[status-icons] ${why} — table degrades to colour and code`);
}

if (!site || !name || !key) {
	await empty('no FPT credentials in the environment');
	process.exit(0);
}

try {
	const auth = await fetch(`${site}/api/v1/auth/access_token`, {
		method: 'POST',
		headers: { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' },
		body: new URLSearchParams({ grant_type: 'client_credentials', client_id: name, client_secret: key })
	});
	if (!auth.ok) throw new Error(`auth ${auth.status}`);
	const token = (await auth.json()).access_token;
	const api = (p) => fetch(`${site}/api/v1${p}`, {
		headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' }
	}).then((r) => r.json());

	// `url` reads as an empty string unless image_data is asked for in the same call (probe 038).
	const ICON = ['display_type', 'image_map_key', 'html', 'url', 'image_data'];
	const rows = await fetch(`${site}/api/v1/entity/statuses/_search`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			Accept: 'application/json',
			'Content-Type': 'application/vnd+shotgun.api3_array+json'
		},
		body: JSON.stringify({
			filters: [],
			fields: ['code', 'name', 'bg_color', ...ICON.map((f) => `icon.Icon.${f}`)],
			page: { size: 200 }
		})
	}).then((r) => r.json());

	const statuses = {};
	const wanted = new Set();
	for (const s of rows.data ?? []) {
		const a = s.attributes ?? {};
		const dt = a['icon.Icon.display_type'];
		const mk = a['icon.Icon.image_map_key'];
		if (dt === 'image_map' && mk) wanted.add(mk);
		statuses[a.code] = {
			code: a.code,
			name: a.name,
			bg: a.bg_color ?? null,
			kind: dt ?? null,
			key: mk ?? null,
			// A custom icon carries its own bytes, so it needs no sprite and no second request.
			data: dt === 'image' ? (a['icon.Icon.url'] || '').replace(/\s+/g, '') : null,
			html: dt === 'html' ? a['icon.Icon.html'] : null
		};
	}

	// The sprite and its offsets live in the web app's stylesheet, not the API. Both answer
	// unauthenticated, and the path is deployment-versioned, so it is matched, never assumed.
	const css = await fetch(`${site}${CSS_PATH}`).then((r) => (r.ok ? r.text() : ''));
	const cells = {};
	for (const k of wanted) {
		const m = new RegExp(`div\\.${k}\\s*\\{([^{}]*)\\}`).exec(css);
		if (!m) continue;
		const b = m[1].replace(/\s+/g, ' ');
		const w = /width:\s*(\d+)px/.exec(b);
		const h = /height:\s*(\d+)px/.exec(b);
		const o = /sg_icon_image_map\.png[^)]*\)\s*(-?\d+)px\s+(-?\d+)px/.exec(b);
		if (w && h && o) cells[k] = { w: +w[1], h: +h[1], x: +o[1], y: +o[2] };
	}

	const href = /url\(([^)]*sg_icon_image_map[^)]*)\)/.exec(css)?.[1]?.replace(/['"]/g, '');
	let sprite = false;
	if (href) {
		const png = await fetch(href.startsWith('/') ? `${site}${href}` : href);
		if (png.ok) {
			await fs.mkdir(path.dirname(OUT_PNG), { recursive: true });
			await fs.writeFile(OUT_PNG, Buffer.from(await png.arrayBuffer()));
			sprite = true;
		}
	}

	// Which codes each entity type offers. `valid_values` is byte-identical at every scope and only
	// `hidden_values` varies by project (probe 009), so the usable set is the subtraction and it is
	// the only part that needs a project. One single-field schema call per type: reading every field
	// of every type is the expensive mistake finding 002 names.
	const types = (await fs.readdir(path.resolve('../corpus/findings/entity_types')).catch(() => []))
		.filter((f) => f.endsWith('.md'))
		.map((f) => f.replace(/\.md$/, ''));
	const project = process.env.FPT_SITE_PROJECT || '';
	const entityTypes = {};
	for (const t of types) {
		const q = project ? `?project_id=${encodeURIComponent(project)}` : '';
		const r = await api(`/schema/${t}/fields/sg_status_list${q}`);
		const props = r?.data?.properties;
		if (!props?.valid_values) continue;
		const valid = props.valid_values.value ?? [];
		const hid = props.hidden_values?.value ?? [];
		entityTypes[t] = {
			valid,
			hidden: project ? hid : [],
			usable: project ? valid.filter((v) => !hid.includes(v)) : valid,
			default: props.default_value?.value ?? null
		};
	}

	await fs.mkdir(path.dirname(OUT_JSON), { recursive: true });
	await fs.writeFile(
		OUT_JSON,
		JSON.stringify({ available: true, sprite, project: project || null, statuses, cells, entityTypes }, null, '\t')
	);
	console.log(
		`[status-icons] ${Object.keys(statuses).length} statuses, ${Object.keys(cells).length} sprite cells, ` +
			`${Object.keys(entityTypes).length} entity types${project ? ` scoped to project ${project}` : ' (site scope)'}, ` +
			`sprite ${sprite ? 'fetched' : 'missing'}`
	);
} catch (e) {
	// A build must never fail because the site is unreachable.
	await empty(`live fetch failed (${e.message})`);
}
