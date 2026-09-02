import { index } from '$lib/content/corpus.js';

// The cited examples at the foot of the page. Each states a behaviour and cites
// the entry that measured it. Slugs are resolved against the corpus at build
// time, so an example whose entry has been renamed drops out instead of
// dead-linking.
const EXAMPLES = [
	{
		group: 'findings',
		slug: '017_filter_operators',
		claim: 'An unknown filter operator returns 400 naming every legal relation.',
		body: 'Measured on all 21 reachable data types: every one 400s, and 16 of them enumerate the field\'s whole legal vocabulary in the error. The other five take no operator at all and say so. A filter typo can never pass as "no filter".',
		code: 'Valid relations: ["is", "is_not", "greater_than", "less_than",\n "in_last", "not_in_last", "in_next", "not_in_next",\n "in_calendar_week", "in_calendar_month", "in_calendar_day",\n "in_calendar_year", "between", "in", "not_in"]'
	},
	{
		group: 'findings',
		slug: '003_query',
		claim: 'An unknown ?fields name is dropped at 200.',
		body: 'The opposite of the filter path. A misspelled field is removed from the response and the request succeeds, so the row comes back missing a key rather than reporting an error.',
		code: 'GET /entity/versions?fields=sg_not_a_field\n-> 200, n=1'
	},
	{
		group: 'field_types',
		slug: 'serializable',
		claim: 'A write can be accepted at 200 and discarded.',
		body: 'Task.splits takes a well-formed array of hashes, answers 200, and stores null. A client that trusts the status code records a value that is not there.',
		code: 'PUT [{"start_date": "2026-01-01", "duration": 480}]\n-> 200      reads back: null'
	},
	{
		group: 'field_types',
		slug: 'status_list',
		claim: 'hidden_values is not enforced on write.',
		body: 'REST accepts a status the project hides from its own UI, and reads it back. Only valid_values is enforced, so every client must subtract hidden_values itself.',
		code: 'usable = [v for v in valid_values if v not in hidden_values]'
	}
];

export function load() {
	const data = index();
	const bySlug = new Map(
		[...data.findings, ...data.fieldTypes, ...data.entityTypes, ...data.recipes].map((e) => [
			e.group + '/' + e.slug,
			e
		])
	);

	const examples = EXAMPLES.map((ex) => {
		const found = bySlug.get(ex.group + '/' + ex.slug);
		return found ? { ...ex, href: found.href, cite: found.name } : null;
	}).filter(Boolean);

	return { findings: data.findings, recipes: data.recipes, counts: data.counts, examples };
}
