# Endpoints — Records, GET

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /entity/<type>`

Pages rows. An entity field is returned under `relationships` and never `attributes`, an unknown `fields` name is dropped at 200, and `links.next` is emitted on empty pages forever.

| you send | what happens |
|---|---|
| `fields=code,sg_not_a_field` | 200, and the key is absent from `attributes` |
| `page[number]=99999` | 200, `data: []`, and `links.next` points at page 100000 |
| `page[size]=5000` | 200, 5000 rows. No cap was reached; the 500 limit is folklore |
| `page[size]=0` | 400 |

- Stop paging when `data` is empty. `links.next` is never absent, so a loop waiting for it to disappear
  never ends.

- An entity link is under `relationships`, with the row's `name` alongside its `id`. Reading
  `attributes` alone makes every link look null.

**Measured by**

- `001_auth` (findings) — Send the token request as `application/x-www-form-urlencoded`: `application/json` is 400 Invalid JSON body. client_credentials returns a 600s bearer, so ignore the refresh_token and re-auth.  
  rules: `doors/findings-auth`
- `027_auth_permissions` (findings) — The token endpoint accepts password and session_token. Impersonation is the OAuth2 scope sudo_as_login:<login>, never a body field, and a lower level reads far fewer rows and as many fields.  
  rules: `doors/findings-auth`
- `004_array_vs_hash` (findings) — api3_array/api3_hash are a POST _search request Content-Type, not a GET Accept header: as Accept they 406, and entity fields are returned under relationships either way.  
  rules: `doors/findings-protocol`
- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `051_api_version` (findings) — /api/v1 and /api/v1.1 are the same API. Across 20 read-only calls the only difference is api_version in the root document and the prefix each echoes in its own links. Any other segment is 404.  
  rules: `doors/findings-protocol`
- `061_shipped_statuses` (findings) — Nothing in the schema marks a shipped Status. `system` is true on a minority of them; the stock set is `created_by is null`, plus `options[return_only]=retired` for the rows a site retired.  
  rules: `doors/findings-schema`
- `003_query` (findings) — A dotted ?fields path comes back flat under literal key "sg_task.Task.content" in attributes; an entity field is returned under relationships as {data, links}. Never read a row from attributes alone.  
  rules: `doors/findings-read`
- `005_link_usage` (findings) — On the sample project every Version links through `entity` (99% Shot, 1% Asset) and only 1% through `sg_task`, so measure link usage per site rather than hardcoding Task-linking.  
  rules: `doors/findings-read`
- `006_pagination` (findings) — links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.  
  rules: `doors/findings-read`
- `007_fill_rates` (findings) — On the sample project 30 of 71 Version fields are populated. Rank by fill rate, but drop checkbox, summary and computed fields first: False and 0 are not null and read as 100% filled.  
  rules: `doors/findings-read`
- `018_project_listing` (findings) — sg_status is not a liveness filter and is null on 15 of 22 projects; is_template, is_demo and archived are the discriminators, so pick the ones your list wants - is_demo hides the demo show.  
  rules: `doors/findings-read`
- `023_pages` (findings) — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.  
  rules: `doors/findings-read`
- `026_result_order` (findings) — Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.  
  rules: `doors/findings-read`
- `059_dotted_path_type_check` (findings) — The middle segment of a dotted path is checked against the field's valid_types in a projection and against the schema alone in a filter: the projection drops the key at 200, the filter 400s.  
  rules: `doors/findings-read`
- `016_dotted_multi_entity` (findings) — A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.  
  rules: `doors/findings-filter`
- `030_complex_filters` (findings) — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.  
  rules: `doors/findings-filter`
- `011_create_project` (findings) — A script user can create a Project with nothing but {"name": ...}, at 201, but the response echoes only 6 attributes, so read the project back if you need anything else.  
  rules: `doors/findings-write`
- `010_status_icons` (findings) — Status.icon is an entity link under relationships; display_type picks one of three renderings; url is empty unless image_data is asked for beside it; the stock sprite is in the site's own stylesheet.  
  rules: `doors/findings-render`
- `004_register_published_file` (recipes) — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform  
  rules: `doors/recipes`
- `003_sort_fails_silently` (reports) — A sort on an unknown or unsortable field answers 200 with the rows in default order, while the same field name in a filter answers 400 and names the reason.  
  rules: `doors/reports`
- `008_jsonb_filters_return_everything` (reports) — A filter on PageSetting.settings_json or EventLogEntry.audit_trail is accepted and ignored, so the unfiltered set comes back at 200 and is_null and is_not_null each return every row.  
  rules: `doors/reports`

**Silent on this call**

- `get_entity_type` — Pages rows. An entity field is returned under `relationships` and never `attributes`, an unknown `fields` name is dropped at 200, and `links.next` is emitted on empty pages forever.
- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `023_pages` — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.
- `026_result_order` — Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.
- `059_dotted_path_type_check` — The middle segment of a dotted path is checked against the field's valid_types in a projection and against the schema alone in a filter: the projection drops the key at 200, the filter 400s.
- `016_dotted_multi_entity` — A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.
- `030_complex_filters` — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.

`corpus/endpoints/get_entity_type.md`

## `GET /entity/<type>/<id>`

One row, and the only read where `fields` is honoured on a single record. A retired row is 404 here and 200 under `options[return_only]=retired`.

- The 404 for "never existed" and the 404 for "retired" are the same message with the same code. Only a
  second call with `options[return_only]=retired` tells them apart, and that distinction is the whole of
  what `DELETE` does.

- Code 104 here, against code 103 for a bad type name. 104 is "this row is not there", 103 is "your
  request is wrong".

- This is the only read where `fields` is honoured on a single record. Every write ignores it.

**Measured by**

- `060_entity_dict_name` (findings) — The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.  
  rules: `doors/findings-read`
- `088_project_template_defaults` (findings) — The per-entity-type default is readable at `Project.tracking_settings.default_task_template.<Type>`, a `{type, id, name, valid}` dict. `Project.task_templates` is a separate list, not the default.  
  rules: `doors/findings-read`
- `058_local_storage_roots` (findings) — One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.  
  rules: `doors/findings-write`
- `083_task_template_on_create` (findings) — A create with `task_template` makes the Tasks inside the same call, by `POST` and by `_batch`, copying every field set on the template tasks and their dependency types and offsets.  
  rules: `doors/findings-write`
- `085_task_dependency_types` (findings) — TaskDependency takes four `dependency_type` values, default `finish-to-start-next-day`; `offset_days` counts working days and snaps the dependent both ways. `shift_ratio` moved nothing.  
  rules: `doors/findings-write`
- `086_batch_tasks_with_dependencies` (findings) — Tasks and their dependencies take two `_batch` calls: create the Tasks, then create TaskDependency rows. `upstream_tasks` on a create links without rescheduling.  
  rules: `doors/findings-write`
- `089_task_delete_side_effects` (findings) — Deleting a Task retires its TaskDependency rows, unlinks both neighbours without bridging them, and nulls `Version.sg_task` and `PublishedFile.task`. Revive restores all of it.  
  rules: `doors/findings-write`
- `003_query_fields_and_pages` (recipes) — Resolve a query field's value, and run the rows a saved Page shows  
  rules: `doors/recipes`
- `005_propagate_status` (recipes) — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write  
  rules: `doors/recipes`
- `006_media_round_trip` (recipes) — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  rules: `doors/recipes`
- `007_build_and_reconcile_a_cut` (recipes) — Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there  
  rules: `doors/recipes`
- `009_multi_entity_safely` (recipes) — Add to and remove from a multi_entity field without destroying the links you did not mean to touch  
  rules: `doors/recipes`
- `013_publish_file_bytes` (recipes) — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under  
  rules: `doors/recipes`
- `015_apply_task_template_without_duplicates` (recipes) — Apply a task template to an entity that already has Tasks, without duplicating the ones it already holds  
  rules: `doors/recipes`

**Silent on this call**

- `058_local_storage_roots` — One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.
- `086_batch_tasks_with_dependencies` — Tasks and their dependencies take two `_batch` calls: create the Tasks, then create TaskDependency rows. `upstream_tasks` on a create links without rescheduling.
- `005_propagate_status` — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write
- `009_multi_entity_safely` — Add to and remove from a multi_entity field without destroying the links you did not mean to touch

`corpus/endpoints/get_entity_type_id.md`

## `GET /entity/<type>/<id>/<field>`

Reads one image or attachment field, and with `?alt` redirects to the bytes. Every other data type is a 400, so this is not a cheap single-field read.

| `<field>` | result |
|---|---|
| `image`, an `image` field | 200, `data` is a URL string |
| `sg_uploaded_movie`, a `url` field | 200, `data` is the attachment hash |
| `code`, `sg_status_list`, `id` | 400 `is not an image or attachment` |
| `entity`, `playlists` | 400, the same message. Use `relationships/<field>` |
| `entity.Shot.code` | 406, one byte |
| a name the type does not have | 404, code 103 |

- A dotted path 406s because the segment after the last dot is read as a format extension, not as a
  field. There is no single-field read for a dotted path.

- `Range` without `?alt` is ignored and the field hash comes back at 200. The header only reaches
  storage once the redirect is in play.

- Reading `image` here costs about the same as `GET /entity/<type>/<id>?fields=image`, because the
  presigned URL is most of both bodies.

- An empty field answers 200 with `"data": null`. Add `?alt` to the same call and it is a 404, worded
  differently per data type: `Field sg_uploaded_movie is empty.` for `url`, `File not found` for
  `image`. Read the field first if the difference between empty and missing matters.

**Measured by**

- `048_one_record_beyond_crud` (findings) — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.  
  rules: `doors/findings-read`

**Silent on this call**

- `048_one_record_beyond_crud` — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.

`corpus/endpoints/get_entity_type_id_field.md`

## `GET /entity/<type>/<id>/relationships/<related_field>`

The `entity` or `multi_entity` link list on its own, unpaged and unsorted. `page`, `fields` and `sort` are accepted and ignored, and every link is returned in one body.

| you send | result |
|---|---|
| `page[size]=2` on a 60-link field | 200, all 60 rows |
| `page[number]=2` | 200, the same 60 rows |
| `fields=code` | ignored, links stay `{id, name, type}` |
| `sort=code` | ignored, source order kept |
| an `image` field | 400 `is not a relationship field` |

- `data` is byte-identical to what `GET /entity/<type>/<id>?fields=<field>` returns under
  `relationships`, in the same order, minus the `links.related` pointer to the linked row.

- There is no `links.next` and no measured page cap. The whole link list is in the one response.

- The saving is small: on the probed site 120 bytes against 353 for a single link, and 3048 against
  3231 for 60. Call it when the link list is the entire request, not to trim a read you are making
  anyway.

- `options[return_only]=retired` is evaluated against the owning record, so it 404s on a live row
  rather than filtering the links.

- `GET` is the only verb. `POST` and `DELETE` on this path are 404 (`field_types/multi_entity`); edit
  links with `PUT /entity/<type>/<id>`.

**Measured by**

- `048_one_record_beyond_crud` (findings) — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.  
  rules: `doors/findings-read`

**Silent on this call**

- `048_one_record_beyond_crud` — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.

`corpus/endpoints/get_entity_type_id_relationships_field.md`
