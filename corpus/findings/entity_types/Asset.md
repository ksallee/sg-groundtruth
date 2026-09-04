---
tags: [list-field]
scope: api
measured: first sample project read, sandbox project written
summary: A thing that appears in shots, such as a character, a prop or an environment.
verdict: Only project is required to create an Asset; omit code and the server writes "New Asset <id>", and two assets in one project may share a code, so key on id and never on code.
---

# Asset

**Type** Schema name `Asset`, addressed at `/api/v1/entity/assets`. The slug is neither case nor plural
sensitive: `/entity/asset` and `/entity/Asset` return the same rows, and only an unknown name is refused.

```
GET /entity/assets   -> 200      GET /entity/Asset    -> 200
GET /entity/asset    -> 200      GET /entity/assetss  -> 404 "Entity type 'assetss' does not exist."
```

Project-scoped. `Asset.project` is an editable `entity` field, `valid_types: ["Project"]`. An unfiltered
`_search` returns assets from every project on the site, so send the project filter on every read:

```
{"filters": [["project", "is", {"type": "Project", "id": <pid>}]], "fields": ["code"]}
```

**Identity** `code`, display name `Asset Name`, `data_type: text`. It is the only field flagged
`mandatory`, and no Asset field is flagged `unique`. Nothing enforces uniqueness at either scope: two
assets created in one project with the same `code` both returned 201. `cached_display_name` mirrors
`code` and is not separate identity.

**Create** `POST /entity/assets`, `Content-Type: application/json`. The schema's `mandatory` flags are not
the create contract (probe 012), and Asset inverts them: the one flagged field is optional and the
unflagged one is required.

| body sent | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `{"code": "charA"}` | 400 `API create() missing 'project' attribute: {"code" => "charA"}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` auto-filled `"New Asset 10025"` |
| `{"project": {...}, "code": "charA"}` | 201, `code` as sent |
| the same `{project, code}` a second time | 201, a second asset with the same `code` |

The 201 echoes the server's defaults, so read them off the response: `code`, `cached_display_name`,
`created_at`, `updated_at`, `open_notes_count: 0` and `sg_status_list` from its `default_value`.

**Links** Every link is written and read as described in `field_types/entity` (a `{type, id}` hash under
`relationships`) and `field_types/multi_entity` (a bare list replaces, `multi_entity_update_mode` adds).
The standard ones:

| field | type | valid_types | editable |
|---|---|---|---|
| `project` | entity | `['Project']` | yes |
| `task_template` | entity | `['TaskTemplate']` | yes |
| `created_by`, `updated_by` | entity | `['HumanUser', 'ApiUser']` | no |
| `image_source_entity` | entity | every entity type on the site | no |
| `tasks` | multi_entity | `['Task']` | yes |
| `shots` | multi_entity | `['Shot']` | yes |
| `sequences` | multi_entity | `['Sequence']` | yes |
| `episodes`, `scenes`, `levels` | multi_entity | `['Episode']`, `['Scene']`, `['Level']` | yes |
| `parents`, `assets` | multi_entity | `['Asset']` | yes |
| `notes` | multi_entity | `['Note']` | yes |
| `open_notes` | multi_entity | `['Note']` | no |
| `sg_versions` | multi_entity | `['Version']` | yes |
| `sg_published_files` | multi_entity | `['PublishedFile']` | yes |
| `tags` | multi_entity | `['Tag']` | yes |
| `addressings_cc` | multi_entity | `['Group', 'HumanUser']` | yes |

Shot and Sequence link in both directions, as `Asset.shots` / `Shot.assets` and `Asset.sequences` /
`Sequence.assets`, all four `multi_entity` and editable. They are one relation seen from two ends, not two
stores: a `PUT /entity/assets/<id>` setting `shots` was immediately matched by
`[["assets", "is", {"type": "Asset", "id": <id>}]]` on `/entity/shots/_search`. Write either side.
`parents` and `assets` are the same arrangement pointing back at Asset, which nests a build.

Which links hold anything is site configuration: on the probed site `shots` and `tasks` were populated on
all 100 assets sampled in one project, `sg_published_files` on none. Measure before assuming a convention.

**Category** `sg_asset_type` is a `list` field, single-valued, a bare string under `attributes`. Its
`valid_values` is the authoritative set for a dropdown; the vocabulary is site configuration, identical
at site and project scope:

```
GET /schema/Asset/fields/sg_asset_type    -> properties.valid_values.value
```

A write outside `valid_values` 400s and names the whole legal set, case included. On the probed site,
`'Character'` was legal and `'character'` was not:

```
Update failed for [Asset.sg_asset_type]: 'character' is not a valid list value.
Valid list values: 'Character', 'Environment', 'Prop', ... .
```

An invalid filter value returns 0 rows with no error, and a filter is case-insensitive where a write is
not (`field_types/list`). Never round-trip a filter value into an update.

**Status** `sg_status_list`, a `status_list`, holding a raw code and never a label. Read a project's usable
set as `valid_values` minus `hidden_values`, which the API does not enforce on writes
(`field_types/status_list`); the vocabulary and both lists are site configuration.

```
GET /schema/Asset/fields/sg_status_list?project_id=<pid>
  -> properties.valid_values.value, .hidden_values.value, .display_values.value
```

`default_value` is applied when the key is omitted on create, so an unset status is unobservable: a
freshly created Asset already reads a status nobody chose.

**Traps**
- `code` is not unique and not required. A client keying an asset by name silently merges or duplicates
  rows. Match on `id`, and treat a `code` lookup as a query that can return more than one row.
- `POST` with `project` alone succeeds, so a request that dropped its payload creates a real asset named
  `New Asset <id>` rather than failing. Send `code` explicitly and check what came back.
- The 400 for a missing project is `code: 103` with `source: {}` and `detail: null`. The message is in
  `title`; a client reading `detail` sees nothing.
- Reading `attributes` alone shows no links at all: `project`, `shots`, `sequences` and `tasks` are all
  under `relationships` (probe 004).
