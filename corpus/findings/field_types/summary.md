---
tags: [field-type, summary, schema, fill-rate, inspector, filter, trap]
scope: api
measured: first sample project read, one Version written in the sandbox project
summary: A count or aggregate the server computes from related rows.
verdict: A summary field is a live rollup: refused on write even where editable=true, unfilterable, unsortable, and null on every custom one here, so re-run the query /schema exposes to select on it.
---

# summary

**Data type** `summary`: a per-row rollup defined in the schema, distinct from the `_summarize`
endpoint (probe 020), which aggregates rows named at call time into one number for the whole query.
On the probed site, scanning all 114 entity types, one `/schema/<Type>/fields` each (33s, probe 002),
finds 42 summary fields on 41 types under four names, every one of them probed below.

| field | types | `editable` | aggregate | reads here | its own query counts |
|---|---|---|---|---|---|
| `open_notes_count` | 38 | `false` | `record_count` | `0` to 19 | the same number |
| `sg_latest_version` | 2 (Asset, Project) | `true` | `single_record` | `null`, every row | 0, except one Project holding Versions |
| `sg_query` | 1 (Asset) | `true` | `single_record` | `null`, every row | 0 |
| `sg_test_results` | 1 (CustomEntity01) | `true` | `record_count` | `null`, 100 of 100 rows | 70, 29, 11 |

| operation | result |
|---|---|
| read | the rollup value, under `attributes` |
| `PUT` and `POST` create, `editable=false` field | 400 `API update() Version.open_notes_count is read only.` and `API create() Version.open_notes_count is read only.` |
| `PUT`, `editable=true` field | 400 `API update() of data type 'summary' not supported in API` |
| filter | 400 `API read() Shot.open_notes_count's 'summary' data type cannot be used in a filter.` |
| `?sort=open_notes_count`, `?sort=-open_notes_count` | 200, row order unchanged |
| `_summarize` `grouping` | 400 `Grouping is not allowed for field Shot.open_notes_count.` |
| `_summarize` `summary_fields [{"field": "open_notes_count", "type": "sum"}]` | 200 `{"summaries": {}, "groups": []}`, field dropped without an error |

**The rollup definition is exposed.** `GET /schema/<Type>/fields/<field>` returns `properties` with
five keys. `default_value` is `{"value": null, "editable": false}` on all 42 of them and is not the
value of an unpopulated row; the other four define the rollup:

| key | holds |
|---|---|
| `summary_default` | the aggregate: `record_count` or `single_record` |
| `query` | `entity_type` of the rows aggregated, and the filter conditions |
| `summary_field` | the field aggregated: `id` for `record_count`, `code` for `Project.sg_latest_version` |
| `summary_value` | `null` for `record_count`; `{"column": "created_at", "direction": "desc", "detail_link": true}` for `Project.sg_latest_version` |

```json
"summary_default": "record_count",  "summary_field": "id",  "summary_value": null,
"query": {"entity_type": "Note", "filters": {"logical_operator": "and", "conditions": [
  {"path": "note_links", "relation": "is",
   "values": [{"id": 0, "name": "Current Entity", "type": "Entity", "valid": "parent_entity_token"}]},
  {"logical_operator": "or", "conditions": [... one per status: "opn", "ip", "rdy"]}]}}
```

`{"id": 0, "valid": "parent_entity_token"}` stands for the row being read. Rewrite each leaf condition
as a triple with the row in place of the token, keep the `logical_operator` groups, and send the tree
as `filters` under `Content-Type: application/vnd+shotgun.api3_hash+json`:

```
{"path": "note_links", "relation": "is", "values": [<the token>]}
  ->  ["note_links", "is", {"type": "Shot", "id": 862}]
```

Run that way, `Shot.open_notes_count` reproduces on three rows: 19, 18 and 18, against 19, 18 and 18.
It is the only summary field returning a number here, so that is the whole of the evidence that the
translation is right. `null` is not an empty rollup: `CustomEntity01.sg_test_results` is a
`record_count` reading `null` on 100 of 100 rows whose own query counts 70. No row here holds a
`single_record` value, so that aggregate is unproven, its populated shape included.

**Read**

| call | reads |
|---|---|
| `GET /entity/shots?fields=code,open_notes_count` | `{"attributes": {"code": "sh010", "open_notes_count": 13}, "relationships": {}, "id": 862}`. A `record_count` rollup is a plain integer in `attributes`, never `relationships`, and `GET /entity/shots/862` with no `?fields` returns it among the 77 attributes |
| `fields ["code", "entity.Shot.open_notes_count"]` on a Version | `{"code": "sh010_comp_v001", "entity.Shot.open_notes_count": 13}`. A dotted path through a link reads the linked row's count, unlike a dotted path through a multi_entity field (probe 016) |
| the four `sg_*` fields, every row: `Asset.sg_latest_version` on `charA`, which has a Version linking to it, `Asset.sg_query`, `CustomEntity01.sg_test_results` on 100 rows, and `Project.sg_latest_version` on all 22 projects | `null` |

The value is computed per read, with no lag. Each row below is the next request after the change:

| step | `open_notes_count` on a sandbox Version |
|---|---|
| before any Note | `0` |
| Note created with `sg_status_list: "opn"`, read 308ms later | `1` |
| same Note moved to `clsd` | `0` |
| Note deleted | `0` |

**Write** Refused; the whole request is rejected rather than accepted and discarded like
`cached_display_name` (probe 004). Re-reading after each attempt returned the value unchanged.

| field | sent | result |
|---|---|---|
| `Project.sg_latest_version` (`editable=true`) | `"zzprobe_summary"`, `42`, `{"type","id"}` | 400 on all three |
| `Version.open_notes_count` (`editable=false`), `PUT` and `POST` create | `3` | 400 |

**Clear** Not reachable.

| case | result |
|---|---|
| `PUT {"sg_latest_version": null}` | 400, the same string as any other write |
| a `record_count` field with nothing to count | `0` on `open_notes_count`: a Version created with no Notes has `open_notes_count: 0` in the 201 body. `sg_test_results` reads `null` with 70 rows to count |

**Filter** No operator works, and the 400 names no vocabulary: every other type answers a bogus
relation with its `Valid relations` list (probe 017). `source` for `definitely_not_an_operator`:

```
{"Shot.open_notes_count": " data type cannot be used in a filter. Value: {"path" =>
 "open_notes_count", "relation" => "definitely_not_an_operator", "values" => [nil]}"}
```

| attempt | result |
|---|---|
| `is 0`, `is_not null`, `greater_than 3`, `less_than 5`, `in [0,1]` | 400, identical title |
| `GET ?filter[open_notes_count]=3`, and `["entity.Shot.open_notes_count", "greater_than", 3]` through a link | 400, identical title |

Page the rows and compare in the client, or run `properties.query` against the target type and aggregate.

**Traps**
- **Fill rate is meaningless on this type.** `open_notes_count` is never null, so it scans as 100% filled
  while holding one value: 100 Versions all read `0` (probe 007). The other four read `null` on every row
  and scan as 0% filled while their queries match rows. Exclude `data_type == "summary"` from fill
  ranking; the `is_not None` probe 400s, as does `_summarize` grouping.
- Sort fails silently. `?sort=code` and `?sort=-code` return different orders, `?sort=open_notes_count`
  returns the unsorted order, and so does `?sort=definitely_not_a_field`: an unsortable field and a
  typo are indistinguishable at 200.
- `editable: true` describes the field-configuration form in the web interface, not the REST value, and
  the refusal cites the data type rather than the field. Three of the 42 summary fields on this site
  claim it, so a client building an update form from `editable` offers three that can never be saved.
- 38 of the 42 are `open_notes_count`, one per entity type, all counting Notes whose status is `opn`,
  `ip` or `rdy`. That set is the site's definition of "open", readable from `properties.query` and site
  configuration rather than an API constant: read it instead of hardcoding the three codes.
