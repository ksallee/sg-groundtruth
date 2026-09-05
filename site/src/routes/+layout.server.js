import { index } from '$lib/content/corpus.js';

// The sidebar lists every subject, so the layout carries a slim copy of each
// index: identity, and what the overlay holds about it. Never a verdict or a
// body, which are what make the full index expensive.
const slim = (e) => ({
	slug: e.slug,
	name: e.name,
	title: e.title,
	number: e.number,
	href: e.href,
	hasApi: e.hasApi,
	locals: e.locals.map((l) => ({ level: l.level, project: l.project }))
});

export function load() {
	const { hasOverlay, hasSite, projects, counts, fieldTypes, entityTypes, recipes, reports, findings, endpoints } =
		index();
	return {
		hasOverlay,
		hasSite,
		projects,
		counts,
		nav: {
			fieldTypes: fieldTypes.map(slim),
			entityTypes: entityTypes.map(slim),
			endpoints: endpoints.map(slim),
			recipes: recipes.map(slim),
			reports: reports.map(slim),
			findings: findings.map(slim)
		}
	};
}
