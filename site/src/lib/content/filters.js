// Everything /filters renders, derived from the field-type cards at build time.
//
// Two readings of the same markdown. The first is the operator vocabulary the
// API returns for a data type, or the fact that the type takes no operator at
// all. The second is the card's `**Filter**` matrix, which is the value to send
// with each operator and what it matches. Neither can drift from the corpus,
// because neither is written by hand and nothing here edits a card.
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
// parse failure, and the types that give it are a group on the page.
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
	// The comparison answers "which operators", the sections below it answer
	// "what to send". Dropping the matrix here keeps one copy of it in the page
	// data rather than two.
	const rows = filterCards(cards).map(({ rows: _matrix, extra: _extra, ...row }) => row);

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

// --- the value matrix ------------------------------------------------------
//
// The operator list alone does not tell a caller what to send: `in_last` takes
// `[7, "DAY"]` and not `7`. Every filterable card holds a `**Filter**` matrix
// whose first three columns are `operator | value | matches`, a shape
// `probes/check_corpus.py` enforces, and this reads it back out.
//
// EXTRA COLUMNS ARE DROPPED. `date` adds `measured`, `image` adds `code`, `uuid`
// adds two row counts. Each means something different, so rendering them side by
// side under one heading would put four kinds of number in one column. The page
// names them and links to the card.
//
// A matrix holds more rows than the vocabulary has operators: one row per value
// shape, plus rows for operators the API refuses, whose `matches` is the 400. Both
// are what a caller needs, so every row is rendered and none is folded away.

const FILTER_SECTION = /^\*\*Filter\*\*([\s\S]*?)(?=^\*\*|$(?![\s\S]))/m;
// A separator holds at least one dash, which is what keeps a data row of empty
// cells (`uuid` has several) from being read as a header underline.
const SEPARATOR = /^\|[\s\-:|]*-[\s\-:|]*\|$/;
const HEADS = ['operator', 'value', 'matches'];
// Deliberate in the corpus: the operator is in the API's own list and the card
// never exercised it. It renders as a gap, never as a blank.
const NOT_MEASURED = /^not measured$/i;
const CODE = /`([^`]+)`/g;

function cells(line) {
	return line
		.trim()
		.replace(/^\|/, '')
		.replace(/\|$/, '')
		.split('|')
		.map((c) => c.trim());
}

function matrixFrom(raw, slug) {
	const section = FILTER_SECTION.exec(raw);
	if (!section) return null;

	const lines = section[0].split('\n');
	for (let i = 0; i + 1 < lines.length; i++) {
		if (!lines[i].trim().startsWith('|') || !SEPARATOR.test(lines[i + 1].trim())) continue;
		const heads = cells(lines[i]);
		if (HEADS.some((head, n) => (heads[n] ?? '').toLowerCase() !== head)) continue;

		const rows = [];
		for (let j = i + 2; j < lines.length && lines[j].trim().startsWith('|'); j++) {
			const cs = cells(lines[j]);
			if (cs.length < 3) {
				throw new Error(
					`[filters] ${slug}.md has a **Filter** row with ${cs.length} cells where the matrix ` +
						`declares ${heads.length}: ${lines[j].trim()}. Three cells are the contract, so this ` +
						`row cannot be read and will not be rendered half-empty.`
				);
			}
			const [operator, value, matches] = cs;
			rows.push({
				operator,
				value,
				matches,
				gap: NOT_MEASURED.test(value) || NOT_MEASURED.test(matches)
			});
		}
		return { rows, extra: heads.slice(3) };
	}
	return null;
}

/**
 * One card, its vocabulary and its value matrix.
 *
 * @throws if a card names operators but records no matrix, or if the matrix
 *   never exercises an operator the API listed. Either would publish a page
 *   that silently knows less than the corpus does.
 */
function readCard(card) {
	const { operators, filterable } = relationsFrom(card.raw, card.slug);
	const base = { slug: card.slug, name: card.name, href: card.href, operators, filterable };

	// The five types the API refuses to filter enumerate nothing and so have no
	// matrix. "No relation is accepted" is the answer, and it is already rendered.
	if (!filterable) return { ...base, rows: [], extra: [] };

	const matrix = matrixFrom(card.raw, card.slug);
	if (!matrix) {
		throw new Error(
			`[filters] ${card.slug}.md lists ${operators.length} operators and holds no readable ` +
				`**Filter** matrix. The first three columns must head \`| operator | value | matches |\`, ` +
				`which is what \`probes/check_corpus.py\` enforces. Without it /filters can name the ` +
				`operators and not the values, which is the half a caller needs.`
		);
	}

	const exercised = new Set(matrix.rows.flatMap((row) => [...row.operator.matchAll(CODE)].map((m) => m[1])));
	const missing = operators.filter((op) => !exercised.has(op));
	if (missing.length) {
		throw new Error(
			`[filters] ${card.slug}.md names ${operators.length} operators and its **Filter** matrix ` +
				`exercises ${operators.length - missing.length}. Missing: ${missing.map((op) => `\`${op}\``).join(', ')}. ` +
				`Give each one a row, marked \`not measured\` in both \`value\` and \`matches\` if it was ` +
				`never sent. A page that drops an operator is worse than no page.`
		);
	}

	return { ...base, ...matrix };
}

/** Every field-type card, in corpus order, with its full matrix. */
export function filterCards(cards) {
	return cards.map(readCard);
}
