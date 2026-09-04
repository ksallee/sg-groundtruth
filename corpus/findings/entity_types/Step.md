---
tags: [task, filter, query, silent, step]
scope: api
measured: site-wide plus the first sample project; read only
summary: A pipeline step, shared by every project on the site.
verdict: Step is site-wide with no project field, partitioned only by entity_type; list the Steps for a Shot with entity_type is "Shot", and treat neither code nor short_name as unique.
---

# Step

**Type** Schema name `Step`, REST path slug `steps`. Site-wide: 13 fields, none of them `project`, and no
project scope on the endpoint. Every project on the site reads the same Steps.

| path | result |
|---|---|
| `GET /entity/steps` | 200 |
| `GET /entity/step`, `GET /entity/Step` | 200, the same rows; `links.self` normalises to `/api/v1/entity/steps/<id>` |
| `GET /entity/pipeline_steps` | 404 `Entity type 'pipeline_steps' does not exist.` |
| `GET /entity/steps/1` | 404 code 104 `Step: 1 not found`; ids are not dense, so read them from the listing |

| project scope attempted | result |
|---|---|
| `_search` `[["project", "is", {"type": "Project", "id": N}]]` | 400 code 103 `API read() Step.project doesn't exist.` |
| `GET ?filter[project]=N` | 400, same title, `source` `{"Step.project": " does not exist. ..."}` |
| `GET ?project_id=N` | 200, accepted and ignored: the same row count as the unscoped call |

`entity_type` is the only partition. It is the `entity_type` data type (`field_types/entity_type`): a bare
schema name under `attributes`, `Shot` and never the slug `shots`, read-only after create, case-sensitive on
filter. On the probed site 35 Steps split three ways.

| `entity_type` | Steps | `short_name` unique within it | `code` unique within it |
|---|---|---|---|
| `Asset` | 13 | yes | no |
| `Shot` | 12 | yes | no |
| `Level` | 10 | yes | yes |

Listing the Steps a client may offer for one entity type, in the order the web UI shows them:

```
POST /entity/steps/_search   Content-Type: application/vnd+shotgun.api3_array+json
{"filters": [["entity_type", "is", "Shot"]],
 "fields": ["code", "short_name", "list_order", "color"], "sort": ["list_order"]}
```

**Identity** `code` is what a human reads, `short_name` is what a pipeline keys on. Neither is unique, and
the schema says so: `unique: false` on both.

| field | distinct of 35 | repeated |
|---|---|---|
| `code` | 25 | 6 values |
| `short_name` | 28 | 5 values |
| `cached_display_name` | 1 | `null` on all 35 rows |

Duplicates are cross-type: one Step for `Asset` and one for `Shot` under the same `code`. Key on `id`, or on
the pair (`entity_type`, `short_name`). On the probed site the repeated codes are `Animation`,
`Character FX`, `FX`, `Layout`, `Lighting` and `Model`, and the repeated short names `ANM`, `CFX`, `FX`,
`MDL` and `layout`. `layout` is lower case where every other short name is upper case, so a client that
upper-cases before filtering returns 0 rows for it.

**Create** Not attempted. A Step is shared by every project, so one created here would appear in every
project's Task pipeline and add a `step_<n>` pivot column to its entity type
(`field_types/pivot_column`); deleting the row does not free the column name. What the schema declares,
unverified against the server, which requires a different set (probe 012):

| field | schema |
|---|---|
| `code`, `short_name` | `mandatory: true` |
| `entity_type` | `mandatory: false`, `editable: false`; a `PUT` returns 400 `API update() Step.entity_type is editable on create only.` |

**Links**

| field | data type | `valid_types` | editable |
|---|---|---|---|
| `department` | `entity` | `['Department']` | yes |
| `created_by`, `updated_by` | `entity` | `['HumanUser', 'ApiUser']` | no |

Two fields anywhere in the 114 types of `/schema` name `Step` specifically. Step itself has no reverse field
to Task, so the direction is Task to Step, one Step per Task.

| field | data type | `valid_types` |
|---|---|---|
| `Task.step` | `entity` | `['Step']` |
| `Department.steps` | `multi_entity` | `['Step']` |

51 further fields (`EventLogEntry.entity`, and `image_source_entity` on 50 types) list `Step` among 114
`valid_types`. Those are generic any-entity links, not Step links; see `field_types/entity`.

Resolve a Task's Step with a dotted path in the same call (probe 003), never a second fetch:

```
POST /entity/tasks/_search   fields: content, step.Step.code, step.Step.short_name,
                                     step.Step.entity_type, step.Step.color, step.Step.id
{"content": "Art", "step.Step.code": "Art", "step.Step.short_name": "ART",
 "step.Step.entity_type": "Asset", "step.Step.color": "253,94,99", "step.Step.id": 13}
```

**Status** None. Step has no `status_list` and no `list` field. `list_order` (`number`, editable) is the
display order, and nulls sort last in both directions: on the probed site the 12 `Shot` Steps sort
`[1, 2, 3, 4, 5, 6, 7, 8, 9, null, null, null]` ascending and `[9, 8, 7, 6, 5, 4, 3, 2, 1, null, null,
null]` descending.

**Traps**
- `entity_type` groups Steps; it does not constrain `Task.step`. On the probed site 6 Tasks hold a Step
  declared for another type: 4 `Level` Steps and 2 `Shot` Steps on Asset Tasks. Check the pair yourself
  before trusting a Step to describe the entity it is attached to.
- `["entity", "type_is_not", "Shot"]` also matches a Task whose `entity` is null. Of 205 apparent
  cross-type Tasks on the probed site, 199 have no `entity` at all. Add `["entity", "is_not", null]`.
- `cached_display_name` is null on every Step on the probed site, though it is `editable: true` and reads
  as an ordinary `text` field. Display `code`.
- `Task.step` takes a `{type, id}` hash. A bare id returns 400 `API summarize() Task.step expected [Hash,
  ActiveSupport::HashWithIndifferentAccess, ... NilClass] data type(s) but got Integer: 2` (probe 012).
