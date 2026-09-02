---
tags: [entity-type, published-file, create, path, storage, entity-field, multi-entity, dependency, status, trap]
scope: api
verdict: Only `project` is required to create a PublishedFile, and nothing is unique: the same name, version_number and path publish twice at 201, so read the last version before writing the next.
---

# PublishedFile

**Type** Schema name `PublishedFile`, REST slug `published_files`, project-scoped: every row holds a
`project` entity link and a create without one is refused.

A two-word type name is matched on word boundaries, not letter by letter. Underscore or capital splits
the words; run them together and the type does not exist:

```
GET /entity/published_files -> 200     GET /entity/publishedfiles -> 404
GET /entity/published_file  -> 200     GET /entity/publish_files  -> 404
GET /entity/PublishedFile   -> 200      title:  "Not Found"
GET /entity/PublishedFiles  -> 200      detail: "Entity type 'publishedfiles' does not exist."
GET /entity/publishedFile   -> 200
GET /entity/Published_File  -> 200
```

Project scoping is a filter, not a path segment. `filters: []` returns rows from every project at once
(183 rows across 2 project ids on the probed site); narrow with `filter[project.Project.id]=<id>` on a
`GET`, or `["project", "is", {"type": "Project", "id": N}]`.

**Identity** Two text fields, and neither is unique.

| field | display name | data_type | mandatory | holds |
|---|---|---|---|---|
| `code` | Published File Name | text | yes | the versioned filename of one publish |
| `name` | Name | text | no | the publish stream those versions belong to |
| `version_number` | Version Number | number | no | the client's revision counter |
| `path_cache` | Path Cache | text | no | a copy of the path, written by the publishing client |

`cached_display_name` mirrors `code`. On the probed site, of 183 rows `code` equalled `name` on 8 and
`version_number` was set on 182: one stream read `code` `charA.v003.ma`, `name` `charA.ma`, number 3.

**Create** `POST /entity/published_files`, `Content-Type: application/json`.

| body | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `{"code": "charA.v001.ma"}` | 400 `API create() missing 'project' attribute: {"code" => "charA.v001.ma"}` |
| `{"name": "charA"}` | 400, the same message with the body echoed |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` generated `"New Published File <id>"`, `name` and `version_number` null |
| `{project, code, name, version_number}` | 201, all four as sent |
| the identical body a second time | 201, a second row |
| the same `name` with `version_number` 2 | 201 |

`/schema/PublishedFile/fields` flags `code` mandatory and `project` not; the server requires the opposite
of both, the same inversion Asset and Version show (probe 012). The 201 fills `code`,
`cached_display_name`, `created_at`, `updated_at`, `sg_status_list` from its `default_value`, and on the
probed site two of the site's own checkboxes at `false`.

**Version numbering is a client convention, not a constraint.** No field is flagged `unique` and no
combination is enforced at any scope: the identical `{project, code, name, version_number}` body posted
twice returned two 201s, and so did the identical `path.local_path`. Query for the highest
`version_number` on a `name` before publishing the next one; there is no conflict error to catch.

**Path** The field the type exists for. Read shape, `link_type` `local`: ten keys and no `url`
(`field_types/url`), the LocalStorage join already done, so a client never reassembles a root (probe 021).

```
{ "link_type": "local", "name": "charA.v003.ma", "content_type": "application/mathematica",
  "local_storage": {"type": "LocalStorage", "id": 3, "name": "primary"},
  "relative_path":   "demo_show/assets/charA/RIG/publish/maya/charA.v003.ma",
  "local_path_mac":  "/mnt/projects/demo_show/assets/charA/RIG/publish/maya/charA.v003.ma",
  "local_path_windows": null, "local_path_linux": null,
  "type": "Attachment", "id": 646 }
```

Writing one, on create or on `PUT`:

| `path` sent | result |
|---|---|
| `"/mnt/projects/demo_show/charA.v001.ma"` | 400 `API create() PublishedFile.path expected [Hash, ... NilClass] data type(s) but got String:` and the path echoed |
| `{"local_path": "/mnt/projects/demo_show/charA.v001.ma"}` | 201, `link_type` `local`; the server splits the root off and fills `local_storage`, `relative_path` and the three `local_path_*` |
| `{"relative_path": "demo_show/charA.v001.ma", "local_storage": {"type": "LocalStorage", "id": N}}` | 201, the same read shape |
| `{"url": "file:///…", "name": "charA.v001.ma"}` | 201, `link_type` `web`, six keys, no local paths |
| the same `local_path` a second time | 201, a second row |

`{"local_path": …}` is resolved against the site's LocalStorage rows, so read those first and send a path
under one of the roots: `GET /entity/local_storages?fields=code,mac_path,windows_path,linux_path`. Each
accepted write mints an Attachment that outlives the PublishedFile; delete it by the `id` inside `path`.

**Links**

| field | data_type | `valid_types` |
|---|---|---|
| `project` | entity | `Project`. Required on create |
| `entity` | entity | `Asset`, `Level`, `Shot`, `Sequence`, `Delivery`, `Launch`, plus the site's enabled CustomEntity slots (probe 008) |
| `task` | entity | `Task` |
| `version` | entity | `Version`. The reverse of `Version.published_files` |
| `published_file_type` | entity | `PublishedFileType` |
| `path_cache_storage` | entity | `LocalStorage` |
| `created_by`, `updated_by` | entity | `HumanUser`, `ApiUser`. Not editable |
| `image_source_entity` | entity | every entity type the site exposes. Not editable |
| `upstream_published_files`, `downstream_published_files` | multi_entity | `PublishedFile`. The dependency graph, written from either end |
| `tags` | multi_entity | `Tag` |

Write shapes and dotted reads: `field_types/entity`, `field_types/multi_entity`. Which links a site fills
is a measurement: probe 021 found `Version.published_files` set on 2 of 53 Versions on the probed site.
`published_file_type` is an entity link, not a list field, and `PublishedFileType` is site-wide (its
schema has no `project` field). Resolve a name to an id once and cache it:

```
GET /entity/published_file_types?fields=code,short_name    -> 8 rows on the probed site
```

**Status** `sg_status_list`, data_type `status_list`, holding a raw code and never a label, with a
`default_value` applied on create. A project's usable set is `valid_values` minus `hidden_values`, read
with `project_id` (probe 009); both lists are site configuration. On the probed site `valid_values` is
`['wtg', 'ip', 'cmpt']` and the sample project hides none. Write and filter: `field_types/status_list`.

**Traps**
- `path_cache` stays `null` after a REST create even when `path` resolved to a local storage, while
  `path_cache_storage` is set from that resolution. A filter on `path_cache` misses every row published
  through the REST API and matches only what a publishing client wrote by hand.
- A `local` path has no `url` key, so `value["url"]` raises on exactly the shape a publish uses. Read
  `link_type` first (`field_types/url`).
- There is no `notes` or `open_notes` field. A comment about a publish lives on its `version` or its
  `task`, never on the PublishedFile.
- Not editable on the probed site: `id`, `created_at`, `created_by`, `updated_at`, `updated_by`,
  `image_blur_hash`, `image_source_entity`. Everything else, `path_cache` included, takes a write.
