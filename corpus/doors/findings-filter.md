# Findings — filter: selecting the rows you want

How the API behaves in this part of a session. Each rule is the entry's own **Teaches**, copied whole.

## 016_dotted_multi_entity

A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.

- **Trap.** The read failure is silent and indistinguishable from "no data": the key is not in `attributes`, the same quiet drop a bogus `?fields` name gets (probe 004). Single-entity paths like `sg_sequence.Sequence.code` come back fine, so the difference is the field's `data_type`, not the syntax.

- The filters are evaluated, not ignored: every negative control returns 0, and two hops (`assets.Asset.sg_asset_type`) resolve. On the probed site the positives return partial counts, 284 of 300.

- Filter through multi-entity freely. To read those values, query the child entity separately (`/entity/tasks` filtered by the parent) rather than asking for them inline.

- Corrects probe 005: `page[size]` is not capped at 100. On the probed site 150 returned 150 rows and 500 returned all 300.

`corpus/findings/016_dotted_multi_entity.md`

## 017_filter_operators

is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work, on text fields and through dotted paths; an unknown operator 400s on all 21 data types, naming the valid list on 16.

- An unknown operator 400s on every data type: 21 of 21 reachable read-only. `source` names the field's whole legal vocabulary on 16 of them. The other five, `calculated`, `password`, `serializable`, `summary` and `url`, answer `data type cannot be used in a filter.` and enumerate nothing, because they take no operator at all.

- A bogus `?fields` name is the opposite, dropped at HTTP 200 (probe 004), so a filter typo can never masquerade as "no filter".

- **A write can be accepted at 200 and silently discarded.** `cached_display_name` takes a write and drops it (`field_types/text.md`), `Task.splits` stores `null` for any well-formed payload (`field_types/serializable.md`), and the `multi_entity` update modes spelled in the query string return 200 and replace the whole list (`field_types/multi_entity.md`).

- An invalid operator, by contrast, 400s on all 21 data types tried.

- Every negative control returns 0 rather than the baseline, so these operators are applied, not ignored.

- `in` takes a plain list for scalars, but on an entity field it needs full `{type, id}` hashes: `[{id: N}]` 400s with `invalid/missing entity hash string 'type'` and bare ints 400 with `expected [Hash, ...] but got Integer`.

- `contains` through a dotted path (`entity.Shot.code`) makes server-side type-ahead over names one call, with no client-side scan.

`corpus/findings/017_filter_operators.md`

## 020_summarize

_summarize needs the same vendor Content-Type as _search, and one `grouping` call returns a field's distinct-value count and its empty count. At ~300ms a field, rank a shortlist, never scan.

- The `_summarize` endpoint aggregates rows named at call time; the `summary` data type is a per-row rollup defined in the schema (field_types/summary). Same word, different mechanism.

- `grouping` by a field returns one group per distinct value, with empties under a `''` group, so one call gives both cardinality and the empty count. A fill-rate scan gives neither: it calls `code` and `flagged` both 100% (probe 007), while `grouping` returns one group per row for `code` (an identifier) and exactly one group for `flagged` (no information).

- No cap showed below 1009 groups: on the probed site an unfiltered `Version.code` grouping returns 1009 groups over 1057 rows in 425ms, and one project's 300 distinct Shot codes return 300 groups.

- At ~300ms a call, and up to 1.5s on an entity field, scanning every Version field costs many multiples of one paged fetch of 100 rows (306ms on the probed site). Fetch one page for the broad fill-rate pass, then `_summarize` only the shortlist to rank it by cardinality.

- A checkbox cannot be filtered `is_not None`: 400 `API summarize() Version.flagged expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil`. Take fill rate on a checkbox from `grouping`, not from a filter.

- `application/json` is 415 `Unsupported Content-Type 'application/json'`; send the same vendor Content-Type as `_search` (probe 004).

- A bogus `type` 400s `Request Parameters invalid.` and `source.summary_fields` names the whole set, indexed by position in the list: `type must be one of: record_count, count, sum, maximum, minimum, average, earliest, latest, percentage, status_percentage, status_percentage_as_float, status_list, checked, unchecked`. Ask the endpoint rather than guessing (probe 017).

**One summary type per field per call.** `summaries` is an object keyed by field name, so a second entry
for the same field overwrites the first at 200, with nothing in the response to say so. The last entry wins.
On the probed site, over 100 versions:

| `summary_fields` | `summaries` |
|---|---|
| `id count` | `{"id": 100}` |
| `id maximum` | `{"id": 25568}` |
| `id count` + `id maximum` | `{"id": 25568}` |
| `id maximum` + `id count` | `{"id": 100}` |
| `id count` + `id count` | `{"id": 100}` |
| `id count` + `id minimum` + `id maximum` | `{"id": 25568}` |
| `id count` + `frame_count sum` | `{"id": 100, "frame_count": 0}` |

Two types over one field costs two calls. Two different fields in one call return both.

**A group's label and its value are not interchangeable.** `group_value` is what the grouping was
computed on; `group_name` is the server's render of it for display:

| grouping field | `group_name` | `group_value` |
|---|---|---|
| `user`, an entity field | `"<user>"` | `{"type": "HumanUser", "id": 385, "name": "<user>", "valid": "valid"}` |
| `sg_task`, an entity field, no value set | `""` | `null` |
| `sg_status_list`, a list field | `"na"` | `"na"` |
| `workload`, a calculated field | `"1.25 days"` | `"600.000000"` (field_types/calculated) |

Key on `group_value`, display `group_name`. On an entity grouping `group_value` is the full reference
object, so `group_value.id` identifies the group and survives a rename; `group_name` is the display name
and is not unique. On the probed site a `user` grouping over 100 versions returned 7 groups under 6
distinct `group_name`, two HumanUsers of different id sharing one display name. A client keyed on
`group_name` merges those two people into one row.

`corpus/findings/020_summarize.md`

## 030_complex_filters

api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.

**Boolean logic needs `api3_hash`.** The two vendor Content-Types are not interchangeable, and a client
that wants anything but a conjunction needs both, or `api3_hash` throughout. `api3_hash` also expresses
a plain `and`, so one Content-Type covers every case.

| Content-Type | `filters` accepted | boolean logic |
|---|---|---|
| `api3_array` | `[[field, op, value]]`, and only that | `and` of the list, implicit; no other spelling |
| `api3_hash` | `{"logical_operator", "conditions"}`, conditions being triples or further groups | `and` and `or`, nested |

Four spellings of a boolean under `api3_array` all 400: a nested list, a group object inside the list,
an operator string as the first element, and a fourth element on a triple. `["id","is",862,"or"]` is
`400 Invalid condition`, so the shape is fixed at three elements.

- **Top-level `or` works.** It is the whole `filters` value, not something that has to sit inside an
  `and`. `or` over two conditions disjoint on `id` returns both rows and `and` over the same two returns
  0, so the operator is applied rather than defaulted.

- `and` and `or` are the whole vocabulary, lowercase. `AND`, `OR`, `Or`, `not`, `xor`, `nand` and `""`
  are each `400 Invalid logical operator: <what you sent>`. There is no negation operator; use the
  negative relations (`is_not`, `not_contains`, `not_in`) from probe 017 on the leaf.

- Both keys are required and neither is inferred: a group without `logical_operator` is
  `400 Missing logical operator`, one without `conditions` is `400 Missing conditions parameter`.
  `"conditions": []` is 200 and matches every row, so an empty group is not a no-match, it is no filter.

- **Depth stops at 265 groups, loudly.** 266 is `500 {"title": "Shotgun Server Error", "source": null}`,
  repeatably, with no `source` to read. Nothing is silently truncated below that: the control, an
  `and` of two disjoint conditions at the innermost level, returns 0 at every depth from 1 to 265,
  where a dropped inner group would return the full page.

- The limit is depth, not payload: one flat `or` group of 5000 conditions at 90090 bytes is 200.

- **A query-string `filter[]` on `POST _search` is read by nothing.** `?filter[id]=863` alongside a body
  filter selecting row 862 returns row 862; `?filter[project.Project.id]=<p1>` alongside a body filter
  selecting a row in another project returns that other row.

- A misspelled `?filter[zzz_not_a_field]=1` is 200, where the same name in a body filter is 400 (probe 004). The same parameter on the `GET`
  listing endpoint filters correctly, so the two endpoints take their filters in different places and
  a client moving from `GET` to `_search` must move the filter into the body.

- **The `{path, relation, values}` object runs nowhere over REST.** It is rejected as a condition inside
  a group, as the whole `filters` value, under both Content-Types, and on `_summarize` as well as
  `_search`.

- It is the web interface's storage format only (probe 023) and the rollup definition format
  (`field_types/summary`), so converting a saved page's filters into a query is a translation, never a
  pass-through: rewrite each leaf `{"path": p, "relation": r, "values": v}` as a triple and keep the
  `logical_operator` groups as they stand.

- The group's own extra keys are tolerated: `filter_name`,
  `filter_id` and an unknown key alongside triple conditions are all 200. The leaf's are not, so drop
  them rather than appending; `active` and `top_level_project_filter` both appear (`recipes/003`).

- `v[0]` is right only where the relation takes a scalar. `in_last` and `in_next` take the whole list,
  and passing the first element alone is 400 `expects a 2-element array: [4]` (`recipes/003`), so the
  translator branches on the relation rather than flattening every leaf the same way.

- One group holds mixed operators and mixes leaf conditions with sub-groups as siblings, which is what
  the stored page trees do. `and [["project","is",<p1>], {"or": [id is 862, id is 863]}]` returns 2 and
  the same with an inner `and` returns 0.

- Dotted paths work inside a nested group, and an error inside one is reported as at the top level: a bogus operator 400s with the field's `Valid relations` list,
  a bogus field with `API read() Shot.sg_not_a_field doesn't exist.`

`corpus/findings/030_complex_filters.md`

## 046_search_without_a_path

`/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.

- **The vendor content type is not the API's rule, it is the endpoint's.** Half the POST endpoints
  demand it and `/hierarchy/*` refuses it. A client with one POST helper meets 415 on whichever half it
  was not written against. Both 415s name their legal set, so the error is enough to fix it.

- `search_criteria` must be a hash keyed exactly `entity`. `size must be 1` is counting recognised
  keys, so any other single key reads as a size problem and the real cause is never named. Two other
  shapes and a list were tried; only `{"entity": {"type", "id"}}` answers 200.

- `_text_search` returns a flattened row with no `fields` parameter: `name`, `status`, and a `links`
  pair of bare strings that cannot be followed. Re-read by `links.self` for anything else.

- `entity_types` maps a schema name to that type's own filter array, so one call can be scoped
  differently per type. Nothing else in the API keys a filter by the type it applies to.

- `_expand` returns one level. `children` names the next paths and `has_children` says which are worth
  a call, so walking a project costs one call per node.

- `_search` answers `incremental_path`, the breadcrumb to the row, and it runs through a field name
  (`sg_sequence`), so the tree follows the site's navigation configuration rather than a fixed shape.

`corpus/findings/046_search_without_a_path.md`

## 053_text_search_matching

`page.size` caps at 25 and defaults to 25 with no `links`, so page with `page.number`. Every word must match a case-insensitive substring of the name or of the linked row's name. **[partial]**

not measured: Only `description` and a linked row's name were tried as fields beyond the name, and the tie-break between equal-length names was not reached. The probe's limit, not the site's.

| sent as `page` | answered |
|---|---|
| absent, `{}`, `{"number": 2}` | 200, 25 rows |
| `{"size": 25}`, `{"size": "25"}` | 200, 25 rows |
| `{"size": 26}` and up | 400 code 103, `{"page": {"size": ["size must be less than 25"]}}` |
| `{"size": 0}` and below | 400 code 103, `{"page": {"size": ["size must be greater than 0"]}}` |
| `{"number": 0}` | 400 code 103, `{"page": {"number": ["number must be greater than 0"]}}` |

- 25 is the cap and the default, and the message is off by one: `size must be less than 25` is what
  `{"size": 26}` answers, while `{"size": 25}` answers 200 with 25 rows. `page.size` is the only
  reason a caller sends `page` at all here, and neither bound is the 500 the spec documents.

- The response has no `links` key, so nothing in it says whether there is more. Page with
  `page.number`, which starts at 1 and answers disjoint ids, and stop when `data` is empty. This is
  the opposite of the paginated reads, where `links.next` is emitted forever (probe 006).

- `sort` is accepted and ignored. Four values, one of them a field that does not exist, all answered
  200 with the rows in the order no `sort` gives.

| text | matched |
|---|---|
| `qat`, `QAT`, `Qat`, `qAt` | the same rows: case is ignored |
| `020`, `h01`, `at` | anywhere inside the name, not a prefix |
| `_qat_`, `053_qat`, `qat_0020` | underscore is part of the string, not a word separator |
| `qat 0020`, `0020 qat` | the rows holding both, whichever order they are sent in |
| `qat kif`, `qat nomatch` | nothing: every word has to match |
| `q` | every row whose name holds a `q` |
| a word only in `description` | nothing |
| `qat` on a Version whose `entity` is a Shot named `..._qat_0020` | that Version |

- Every word must match, each as a case-insensitive substring, so a one-letter text is a legal query
  returning whatever fits in 25 rows. Send the longest distinguishing fragment, not a word.

- **A row matches on the name of the row it links to.** The pair under `attributes.links` is part of
  what is searched, so a Version whose `code` holds none of the text is returned because its `entity`
  is a Shot whose name does. Read `attributes.links` before deciding a row is a false positive.

- `description` is not searched, on Shot or on Asset, and neither is any other field measured here.
  A search over descriptions or note bodies is `POST /entity/<type>/_search` with `contains`.

- Rows come back shortest name first, across types, and the order does not change with the order the
  `entity_types` keys are given in. Three Shots created longest-name-first came back shortest first,
  so it is neither id nor creation order. A short generic name outranks a longer exact one, and with
  the cap at 25 the row a caller wants can be off the page: narrow with the per-type filter.

- On the probed site, one call over 14 types took 331-369 ms and the same words asked as one
  `contains` `_search` per type in sequence took 3811-3859 ms over four runs, about 270 ms a call.
  One call is worth it for a picker; a client that needs the full row still re-reads by `links.self`.

`corpus/findings/053_text_search_matching.md`

## 063_text_search_filter_shape

An `entity_types` value follows the request Content-Type: an array of triples under api3_array, a `logical_operator` group under api3_hash, which alone nests. The other shape is 400 code 103.

| `Content-Type` | the value of an `entity_types` key | no filter |
|---|---|---|
| `application/vnd+shotgun.api3_array+json` | `[[field, op, value]]` | `[]` |
| `application/vnd+shotgun.api3_hash+json` | `{"logical_operator": "and"\|"or", "conditions": [...]}` | `{"logical_operator": "and", "conditions": []}` |

- The per-type filter is parsed by whatever the request's vendor content type selects, the same split
  `filters` on `POST /entity/<type>/_search` is under (probe 004). A client that sends `[]` for "search
  everything" gets 400 code 103 `Query is not an Hash: []` the moment it switches to `api3_hash`, and
  there is no shape both content types accept.

- Under `api3_hash`, no filter is a group with an empty `conditions`.

- A `conditions` entry may itself be a group, so `or` and three levels of nesting both filter and both
  answer the rows their branches answer: `or` over two codes returns those two rows and nothing else.

- The array form has no `logical_operator` and takes basic condition arrays alone: a group as one
  element is 400 `Invalid filter. Expected array of basic condition arrays but received:`, and two
  triples in one array answer the rows the `and` of the same two answers.

- The shape is checked per key, so a map may not mix the two forms: the key whose value is the other
  shape decides the 400 and no rows come back for any type.

| the filter names | answer |
|---|---|
| a field the type lacks, at any depth | 400 `API _text_search() Shot.content doesn't exist.` |
| an operator the data type lacks | 400 naming every `Valid relations` for that type |
| a key no entity type is named by | 400 `entity_types must use valid entity names as keys` |
| `{}`, `null` or a string | 400 `entity_types must have an array or non-empty object as each key's value` |

- One bad key fails the whole call, so a picker over ten types that names one field wrong returns
  nothing rather than the nine types it got right. The error names the type and the field.

- `text` is unchanged by a filter being present: every word still has to match a case-insensitive
  substring of the name (probe 053), and the filter narrows what those words are matched against.
  A text matching nothing and a filter matching nothing both answer 200 with an empty `data`.

`corpus/findings/063_text_search_filter_shape.md`
