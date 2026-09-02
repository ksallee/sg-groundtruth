---
tags: [entity-type, shot, create, entity-field, multi-entity, status, pivot-column, trap]
scope: api
verdict: Shot is addressed at /entity/shots and needs only project on create: code is flagged mandatory yet optional, and an omitted code becomes the server-invented "New Shot <id>".
---

# Shot

**Type** Schema name `Shot`, REST slug `shots`: `GET /entity/shots`, `POST /entity/shots`,
`POST /entity/shots/_search`, `PUT|DELETE /entity/shots/<id>`. Project-scoped as a structure, since the
type has an editable `project` field of data type `entity` with `valid_types ['Project']` and create is
refused without it. The endpoint is not scoped: an unfiltered `_search` returns rows from every project
the script can see, so every read needs a project filter of its own.

| call | result |
|---|---|
| `GET /entity/shots` | 200, rows of `"type": "Shot"` |
| `GET /entity/shot`, `/entity/Shot`, `/entity/Shots` | 200, the same rows; the slug is matched loosely |
| `GET /entity/shotz` | 404 `Entity type 'shotz' does not exist.` |
| `links.self` on any row | `/api/v1/entity/shots/<id>`, always the plural lowercase form |
| `_search` with no filter | rows from several projects at once; 7 distinct on one 500-row page here |
| `["project", "is", {"type": "Project", "id": N}]` | that project only |
| `GET ?filter[project.Project.id]=N` | the same rows as the `_search` filter |

**Identity** `code`, data type `text`, display name `Shot Code`, `mandatory: true`, `unique: false`.
`name` and `content` are absent from `/schema/Shot/fields`, and `?fields=name` answers 200 with the key
absent from `attributes` rather than an error, the silent drop of probe 004. `cached_display_name`
mirrors `code`. Nothing about `code` is unique: two creates with the same code in one project both
return 201, so uniqueness is a client's job. The empty string is the one refused value, on create and on
update alike: 400 code 104 `Cannot set identifier field to empty. (Shot)`.

**Create** `POST /entity/shots` with `Content-Type: application/json`. The schema's `mandatory` flags
invert the real contract, as probe 012 found on Version: `project` is flagged `mandatory: false` and is
the only requirement, `code` is flagged `mandatory: true` and is optional.

| body sent | result |
|---|---|
| `{}` | 400 code 103 `API create() missing 'project' attribute: {}` |
| `{"code": "sh010_0010"}` | 400 code 103 `API create() missing 'project' attribute: {"code" => "sh010_0010"}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` server-set to `New Shot <id>` |
| `{"project": {"type": "Project", "id": N}, "code": "sh010_0010"}` | 201 |
| the identical body a second time | 201, a second Shot with the same `code` |
| `{"project": {...}, "code": ""}` | 400 code 104 `Create failed for [Shot]: Cannot set identifier field to empty. (Shot)` |
| `{"project": N, "code": "sh010_0010"}` | 400 code 103 `API create() Shot.project expected [Hash,\n ActiveSupport::HashWithIndifferentAccess,\n ActionDispatch::Http::Parameters,\n ActionDispatch::Http::ParamsHashWithIndifferentAccess,\n NilClass] data type(s) but got Integer: N` |
| `{"project": {...}, "code": ..., "sg_status_list": "ip", "description": ...}` | 201, both stored as sent |

A create with `project` alone fills `code`, `sg_status_list` from its `default_value`, `created_at` and
`updated_at`, and returns all 24 link fields under `relationships` with empty data. `created_by` is null
for a script user.

**Links** Every link reads under `relationships`, never `attributes`; see `field_types/entity` for the
`{type, id}` hash and `field_types/multi_entity` for the `multi_entity_update_mode` wrapper. The stock
shape of the type is a parent link out, a child set in:

| field | type | `valid_types` | what a client uses it for |
|---|---|---|---|
| `project` | entity | `['Project']` | required on create, and the filter on every read |
| `sg_sequence` | entity | `['Sequence']` | the parent; reads back `{id, name, type}` with the name resolved |
| `parent_shots`, `shots` | multi_entity | `['Shot']` | the reverse pair of a shot-to-shot hierarchy |
| `assets` | multi_entity | `['Asset']` | what appears in the shot |
| `tasks` | multi_entity | `['Task']` | readable, but a Task is linked from `Task.entity` |
| `sg_versions` | multi_entity | `['Version']` | readable, but a Version is linked from `Version.entity` |
| `notes`, `open_notes` | multi_entity | `['Note']` | `open_notes` is read only |
| `sg_published_files` | multi_entity | `['PublishedFile']` | publishes, also linked from the child side |
| `task_template` | entity | `['TaskTemplate']` | applied on create to generate Tasks |
| `created_by`, `updated_by` | entity | `['HumanUser', 'ApiUser']` | read only |
| `image_source_entity` | entity | every site type | read only |

Versions and Tasks attach from their own side, so query the child and filter on the parent:
`["entity", "is", {"type": "Shot", "id": N}]` against `/entity/versions/_search` or
`/entity/tasks/_search`. On the probed site, over one 500-row page, 500 of 500 Tasks and 99 of 100
Versions pointed `entity` at a Shot (probe 005), while `Shot.sg_versions` held data on 50 of 200 shots.
`valid_types` does not bind here either: `sg_sequence` lists `['Sequence']` and accepted
`{"type": "Shot", "id": <a Shot>}` at 200, reading it back as a Shot.

**Status** `sg_status_list`, data type `status_list`, editable, with a `default_value` applied when the
key is omitted on create. Read the set a project may use with
`GET /schema/Shot/fields/sg_status_list?project_id=N` and subtract `hidden_values` from `valid_values`
(probe 009); REST enforces `valid_values` only, so a project-hidden code writes and reads back fine
(`field_types/status_list`). The vocabulary is site configuration, never a constant. On the probed site
Shot has a second one, `sg_latest_vendor_status`, so discover status fields by
`data_type == "status_list"` rather than assuming there is one.

**Traps**
- The mandatory flags invert. Omit `code` and the row is created as `New Shot <id>`, which reads as a
  real shot in any picker and is findable only by that string. Always send `code`.
- Nothing enforces uniqueness: `unique` is false and a repeated create returns 201, so a re-run of an
  ingest doubles the rows. Search `["code", "is", ...]` plus the project filter before creating.
- The slug is not the scope. `/entity/shots` unfiltered reaches every project, and the singular and
  capitalised spellings resolve to the same collection, so a typo'd slug fails loudly while a missing
  project filter does not.
- `step_<n>` passes every schema visibility test and reads null on every row, and a write answers 400
  `API update() Shot.step_0 is read only.` (`field_types/pivot_column`). For the same rollup, query Task
  filtered on `entity` and `step`.
