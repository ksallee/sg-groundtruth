---
tags: [field-type, summary, schema, fill-rate, inspector, filter, trap]
scope: api
verdict: A summary field is a live server-side rollup - never null, refused on write even where editable=true, and unfilterable and unsortable, so re-run the query /schema exposes to select on it.
---

# summary

**Data type** `summary`: a per-row rollup defined in the schema, distinct from the `_summarize`
endpoint (probe 020), which aggregates rows named at call time into one number for the whole query.
Probed on stock `Shot.open_notes_count`, `Version.open_notes_count` (`editable=false`) and
`Project.sg_latest_version` (`editable=true`). All 114 entity types scanned, one
`/schema/<Type>/fields` each (33s, probe 002): 42 summary fields on 41 types.

| field | types | `editable` | aggregate |
|---|---|---|---|
| `open_notes_count` | 38 | `false` | `record_count` |
| `sg_latest_version` | 2 (Asset, Project) | `true` | `single_record` |
| `sg_query` | 1 (Asset) | `true` | `single_record` |
| `sg_test_results` | 1 (CustomEntity01) | `true` | `record_count` |

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
five keys; `default_value` has no recorded value, and the other four define the rollup:

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
  {"logical_operator": "or", "conditions": [
    {"path": "sg_status_list", "relation": "is", "values": ["opn"]},
    {"path": "sg_status_list", "relation": "is", "values": ["ip"]},
    {"path": "sg_status_list", "relation": "is", "values": ["rdy"]}]}]}}
```

`{"id": 0, "valid": "parent_entity_token"}` stands for the row being read. Substitute the row id and
the query reproduces the number: Shot 862 reads 13, and on `POST /entity/notes/_search`

```
[["note_links", "is", {"type": "Shot", "id": 862}],
 ["sg_status_list", "in", ["opn", "ip", "rdy"]]]      -> 13 rows
```

`Project.sg_latest_version` queries `entity_type: "Version"` filtered `project is <Current Project>`.
A client can explain and re-derive every summary field on the site from `/schema` alone.

**Read**

| call | reads |
|---|---|
| `GET /entity/shots?fields=code,open_notes_count` | `{"attributes": {"code": "sh010", "open_notes_count": 13}, "relationships": {}, "id": 862}`. A `record_count` rollup is a plain integer in `attributes`, never `relationships`, and `GET /entity/shots/862` with no `?fields` returns it among the 77 attributes |
| `fields ["code", "entity.Shot.open_notes_count"]` on a Version | `{"code": "sh010_comp_v001", "entity.Shot.open_notes_count": 13}`. A dotted path through a link reads the linked row's count, unlike a dotted path through a multi_entity field (probe 016) |
| every `single_record` field, every row: `Asset.sg_latest_version` on `charA`, which has a Version linking to it, and `Project.sg_latest_version` on all 22 projects | `null` |

The populated `single_record` shape is unobserved here: do not assume a `{data, links}` entity link.

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
| a `record_count` field with nothing to count | `0`, not null; a Version created with no Notes has `open_notes_count: 0` in the 201 body |

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
- **Fill rate is meaningless on this type.** A summary field is never null, so `open_notes_count` scans
  as 100% filled on every row while holding one constant: 100 Versions all read `0` (probe 007). Exclude
  `data_type == "summary"` from fill ranking; the `is_not None` probe 400s, as does `_summarize` grouping.
- Sort fails silently. `?sort=code` and `?sort=-code` return different orders, `?sort=open_notes_count`
  returns the unsorted order, and so does `?sort=definitely_not_a_field`: an unsortable field and a
  typo are indistinguishable at 200.
- `editable: true` describes the field-configuration form in the web interface, not the REST value, and
  the refusal cites the data type rather than the field. Three of the 42 summary fields on this site
  claim it, so a client building an update form from `editable` offers three that can never be saved.
- 38 of the 42 are `open_notes_count`, one per entity type, all counting Notes whose status is `opn`,
  `ip` or `rdy`. That set is the site's definition of "open", readable from `properties.query` and site
  configuration rather than an API constant: read it instead of hardcoding the three codes.
