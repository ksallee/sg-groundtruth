// The filter matrix, derived from the field-type cards at build time.
//
// Every card records the operator vocabulary the API returns for its data type,
// or records that the type takes no operator at all. This file reads that back
// out of the markdown so the table on /filters cannot drift from the corpus.
// Nothing here edits the corpus, and nothing here is written by hand.
//
// THREE SHAPES IN THE SOURCE. A card quotes the API's own 400, and the API's
// wording reaches the corpus in whichever form the probe printed it:
//
//   1. `Valid relations: ["is", "is_not"]`         the pretty-printed error
//   2. `Valid relations: [\"is\", \"is_not\"]`     the raw JSON body, quotes
//                                                  still escaped
//   3. no list at all, and the 400 reads
//      `... data type cannot be used in a filter.` the type takes no operator
//
// A list may also wrap across lines inside a fence, so the match runs over the
// whole file rather than line by line.
//
// FAILURE IS LOUD. A card that matches none of the three throws, and the build
// stops naming the file. An unparseable card must never become a blank row: a
// reader cannot tell an empty cell from "this type has no operators", and the
// second is a real answer this table publishes for five types.

// `[^\]]*` crosses newlines, which is what lets a fenced list wrap.
const LIST = /Valid relations:\s*\[([^\]]*)\]/g;

// Both quote forms, so `"is"` and `\"is\"` yield the same token.
const TOKEN = /\\?"([a-z_]+)\\?"/g;

// The API's wording for a type that takes no operator. It is the answer, not a
// parse failure, and the five types that give it are a group on the page.
const UNFILTERABLE = /data type cannot be used in a filter/;

/**
 * Read one card's operator vocabulary out of its markdown body.
 *
 * @returns {{ operators: string[], filterable: boolean }}
 * @throws if the card records neither a vocabulary nor a refusal.
 */
export function relationsFrom(raw, slug) {
	const lists = [...raw.matchAll(LIST)].map((m) => [...m[1].matchAll(TOKEN)].map((t) => t[1]));

	if (lists.length) {
		// A bracket that yielded no token means the list is there and this file
		// cannot read it. That is a parse failure, not a type with no operators,
		// and the two must never render the same.
		if (lists.some((ops) => ops.length === 0)) {
			throw new Error(
				`[filters] ${slug}.md has a \`Valid relations\` list this build cannot read. ` +
					`Operators are matched as quoted lowercase words, plain or backslash-escaped. ` +
					`Widen the token pattern in src/lib/content/filters.js rather than editing the card.`
			);
		}

		// A card quotes its list more than once: in the 400, then again in a table
		// row. They have always agreed. If they ever stop, the card is describing
		// two vocabularies and this table cannot pick one, so it stops instead.
		const signatures = new Set(lists.map((ops) => ops.join(',')));
		if (signatures.size > 1) {
			throw new Error(
				`[filters] ${slug}.md quotes ${signatures.size} different \`Valid relations\` lists ` +
					`(${[...signatures].map((s) => `[${s}]`).join(' and ')}). ` +
					`One card records one data type's vocabulary; split the card or the table cannot be built.`
			);
		}
		return { operators: lists[0], filterable: true };
	}

	if (UNFILTERABLE.test(raw)) return { operators: [], filterable: false };

	throw new Error(
		`[filters] ${slug}.md records no filter vocabulary. A field-type card must either quote ` +
			`\`Valid relations: [...]\` (escaped quotes are fine, and the list may wrap) or quote the ` +
			`API's \`data type cannot be used in a filter\`. Found neither, so /filters cannot render ` +
			`${slug} and will not render it blank.`
	);
}

// FAMILIES. Matched on the vocabulary itself rather than on a list of type
// names, so a data type added to the corpus lands in the right family with no
// edit here. First match wins, so the order is the specific before the general:
// temporal before numeric (it also has `between`), text before containment (it
// also has `contains`).
//
// `note` is a fact the cards state; the counts on the page are derived.
const FAMILIES = [
	{
		id: 'text',
		title: 'Text',
		note: 'The only family with a substring vocabulary.',
		when: (ops) => ops.includes('starts_with')
	},
	{
		id: 'temporal',
		title: 'Temporal',
		note: 'There is no `not_between` and no `is_null`.',
		when: (ops) => ops.includes('in_calendar_day')
	},
	{
		id: 'numeric',
		title: 'Numeric',
		note: 'There is no `>=` and no `<=`. Bracket with `between`, or shift the bound by one.',
		when: (ops) => ops.includes('between')
	},
	{
		id: 'entity',
		title: 'Entity',
		note: 'Trades the substring operators for `name_*` and `type_is`.',
		when: (ops) => ops.includes('name_is') || ops.includes('type_is')
	},
	{
		id: 'containment',
		title: 'Containment',
		note: '`contains` tests containment of a whole structure, not of a substring.',
		when: (ops) => ops.includes('contains')
	},
	{
		id: 'set',
		title: 'List-like',
		note: 'Equality and set membership, on the stored code rather than the display name.',
		when: (ops) => ops.includes('in')
	},
	{
		id: 'presence',
		title: 'Presence',
		note: 'Two relations. Which values they accept is per type; the card says.',
		when: (ops) => ops.length > 0
	},
	{
		id: 'none',
		title: 'Not filterable',
		note: 'The 400 names no vocabulary, because there is none. Page the rows and compare in the client.',
		when: () => true
	}
];

function familyOf(row) {
	return FAMILIES.find((f) => (row.filterable ? f.id !== 'none' && f.when(row.operators) : f.id === 'none'));
}

/**
 * One row per field-type card, grouped by the vocabulary each returns.
 *
 * @param cards `{ slug, name, href, raw }`, straight from the corpus.
 */
export function filterMatrix(cards) {
	const rows = cards.map((card) => ({
		slug: card.slug,
		name: card.name,
		href: card.href,
		...relationsFrom(card.raw, card.slug)
	}));

	return FAMILIES.map((family) => {
		const members = rows.filter((row) => familyOf(row).id === family.id);
		const signatures = new Set(members.map((row) => row.operators.join(',')));
		return {
			id: family.id,
			title: family.title,
			note: family.note,
			rows: members,
			// True when every type in the family answers with the identical list,
			// which is the shape the page is there to make visible. Never true of
			// the unfilterable group: "the identical list of 0" is not a fact.
			shared: family.id !== 'none' && members.length > 1 && signatures.size === 1,
			size: members[0]?.operators.length ?? 0
		};
	}).filter((family) => family.rows.length > 0);
}
