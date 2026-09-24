# Endpoints — Search

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `POST /entity/<type>/_search`

The only way to send a filter the query string cannot express, and it refuses `application/json` at 415 naming both vendor types. `api3_array` cannot express `or`; `api3_hash` nests.

| you send | what happens |
|---|---|
| a query-string `filter[]` | ignored. Only the body filters here |
| `{"path", "relation", "values"}` as a condition | 400 `Missing logical operator`. That shape runs nowhere |
| `filters: []` | 200, unscoped, every row on the site |
| an `or` under `api3_array` | not expressible; the array form is `and` only |

- The unknown-operator 400 enumerates the legal set for that field's data type. It is the cheapest way
  to discover the vocabulary, and it is where the site's filter matrix comes from.

**Measured by**

- `004_array_vs_hash` (findings) — api3_array/api3_hash are a POST _search request Content-Type, not a GET Accept header: as Accept they 406, and entity fields are returned under relationships either way.  
  rules: `doors/findings-protocol`
- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `062_cors` (findings) — Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those.  
  rules: `doors/findings-protocol`
- `061_shipped_statuses` (findings) — Nothing in the schema marks a shipped Status. `system` is true on a minority of them; the stock set is `created_by is null`, plus `options[return_only]=retired` for the rows a site retired.  
  rules: `doors/findings-schema`
- `091_status_summary_exclusions` (findings) — Excluded statuses are invisible to REST: not in /schema at any scope, not writable by PUT. status_list honours them: fin plus an excluded omt rolls up to fin, omt alone to na.  
  rules: `doors/findings-schema`
- `003_query` (findings) — A dotted ?fields path comes back flat under literal key "sg_task.Task.content" in attributes; an entity field is returned under relationships as {data, links}. Never read a row from attributes alone.  
  rules: `doors/findings-read`
- `006_pagination` (findings) — links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.  
  rules: `doors/findings-read`
- `018_project_listing` (findings) — sg_status is not a liveness filter and is null on 15 of 22 projects; is_template, is_demo and archived are the discriminators, so pick the ones your list wants - is_demo hides the demo show.  
  rules: `doors/findings-read`
- `021_media_resolution` (findings) — PublishedFile.path is returned with the LocalStorage join already done, so a client never reads LocalStorage or reassembles a root, but a platform whose storage root is unset reads null.  
  rules: `doors/findings-read`
- `023_pages` (findings) — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.  
  rules: `doors/findings-read`
- `026_result_order` (findings) — Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.  
  rules: `doors/findings-read`
- `059_dotted_path_type_check` (findings) — The middle segment of a dotted path is checked against the field's valid_types in a projection and against the schema alone in a filter: the projection drops the key at 200, the filter 400s.  
  rules: `doors/findings-read`
- `060_entity_dict_name` (findings) — The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.  
  rules: `doors/findings-read`
- `072_page_layouts` (findings) — A page's views are root settings.layouts [{name, display_name}], each name a child of the root. Query widgets sit at /body, inside a view, or in tabs: walk the tree, never read /body alone.  
  rules: `doors/findings-read`
- `073_page_grid_settings` (findings) — Stored pages group one level deep (one of 438 goes two), summarise a column once in 41 grids, and colour columns by DisplayColumn id, a type REST cannot read. mode is list on 94%.  
  rules: `doors/findings-read`
- `075_page_overrides` (findings) — A per-user override patches columns, widths, sorts, mode and the filter panel at any spec_path, "" meaning the root. One row per user and page; 3 of 32 patches name a path the shared tree lacks.  
  rules: `doors/findings-read`
- `076_page_visibility` (findings) — The script user is not the widest reader of Page: an Admin read 2048 pages where the script read 1107 and 404s on the rest. An Artist read 107. Every level reads every person's override.  
  rules: `doors/findings-read`
- `081_dotted_image` (findings) — entity.Shot.image returns the Shot's thumbnail as a presigned S3 URL under attributes, same object, fresh signature, in the same call. image is_not null matched 50 Shots whose image reads null.  
  rules: `doors/findings-read`
- `082_page_size_cap` (findings) — page[size] takes 1 to 5000 inclusive; 5001 is 400 "size must be less than 5000". Omitted, it is 500. A page costs ~330 ms whatever its size up to 500, so read big pages.  
  rules: `doors/findings-read`
- `088_project_template_defaults` (findings) — The per-entity-type default is readable at `Project.tracking_settings.default_task_template.<Type>`, a `{type, id, name, valid}` dict. `Project.task_templates` is a separate list, not the default.  
  rules: `doors/findings-read`
- `016_dotted_multi_entity` (findings) — A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.  
  rules: `doors/findings-filter`
- `017_filter_operators` (findings) — is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work, on text fields and through dotted paths; an unknown operator 400s on all 21 data types, naming the valid list on 16.  
  rules: `doors/findings-filter`
- `030_complex_filters` (findings) — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.  
  rules: `doors/findings-filter`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
- `071_note_link_name_filter` (findings) — Filter notes about a thing on `note_links.<Type>.cached_display_name`: it resolves for every valid type, `code` 400s on Booking and `name` on all but Department. The path cannot be read back.  
  rules: `doors/findings-filter`
- `069_client_note` (findings) — `client_note` cannot be set over REST: `true` on create is 400 and any `PUT` is 400 `editable on create only`. `sg_note_type: "Client"` is the one marker a caller can write.  
  rules: `doors/findings-write`
- `083_task_template_on_create` (findings) — A create with `task_template` makes the Tasks inside the same call, by `POST` and by `_batch`, copying every field set on the template tasks and their dependency types and offsets.  
  rules: `doors/findings-write`
- `087_dependency_cascade` (findings) — An upstream date write reschedules every unpinned downstream Task through the chain, later and earlier alike. A pinned Task stays put and flags `dependency_violation` while it is broken.  
  rules: `doors/findings-write`
- `089_task_delete_side_effects` (findings) — Deleting a Task retires its TaskDependency rows, unlinks both neighbours without bridging them, and nulls `Version.sg_task` and `PublishedFile.task`. Revive restores all of it.  
  rules: `doors/findings-write`
- `014_attach_file` (findings) — Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].  
  rules: `doors/findings-upload`
- `025_event_log` (findings) — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  rules: `doors/findings-observe`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `077_page_change_stamps` (findings) — PageSetting has no updated_at; Page.updated_at moves when its layout is saved. Poll Page.updated_at; Shotgun_PageSetting_Change names which setting changed but its entity is null on 131 of 500.  
  rules: `doors/findings-observe`
- `090_template_task_events` (findings) — A template-generated Task logs like a hand-made one plus a `template_task` change row, `in_create` true, credited to the caller. Filter `attribute_name` `template_task` to find them.  
  rules: `doors/findings-observe`
- `003_query_fields_and_pages` (recipes) — Resolve a query field's value, and run the rows a saved Page shows  
  rules: `doors/recipes`
- `004_register_published_file` (recipes) — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform  
  rules: `doors/recipes`
- `005_propagate_status` (recipes) — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write  
  rules: `doors/recipes`
- `007_build_and_reconcile_a_cut` (recipes) — Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there  
  rules: `doors/recipes`
- `009_multi_entity_safely` (recipes) — Add to and remove from a multi_entity field without destroying the links you did not mean to touch  
  rules: `doors/recipes`
- `010_status_picker` (recipes) — List the statuses a project actually offers, each with the label, colour and icon needed to draw it  
  rules: `doors/recipes`
- `014_notes_about` (recipes) — Find the Notes about a Shot, Asset or Version by the name of the thing, and read what each Note is linked to  
  rules: `doors/recipes`
- `015_apply_task_template_without_duplicates` (recipes) — Apply a task template to an entity that already has Tasks, without duplicating the ones it already holds  
  rules: `doors/recipes`
- `003_sort_fails_silently` (reports) — A sort on an unknown or unsortable field answers 200 with the rows in default order, while the same field name in a filter answers 400 and names the reason.  
  rules: `doors/reports`
- `008_jsonb_filters_return_everything` (reports) — A filter on PageSetting.settings_json or EventLogEntry.audit_trail is accepted and ignored, so the unfiltered set comes back at 200 and is_null and is_not_null each return every row.  
  rules: `doors/reports`

**Silent on this call**

- `post_entity_type_search` — The only way to send a filter the query string cannot express, and it refuses `application/json` at 415 naming both vendor types. `api3_array` cannot express `or`; `api3_hash` nests.
- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `023_pages` — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.
- `026_result_order` — Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.
- `059_dotted_path_type_check` — The middle segment of a dotted path is checked against the field's valid_types in a projection and against the schema alone in a filter: the projection drops the key at 200, the filter 400s.
- `016_dotted_multi_entity` — A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.
- `017_filter_operators` — is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work, on text fields and through dotted paths; an unknown operator 400s on all 21 data types, naming the valid list on 16.
- `030_complex_filters` — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.
- `068_note_read_state` — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.
- `025_event_log` — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
- `005_propagate_status` — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write
- `009_multi_entity_safely` — Add to and remove from a multi_entity field without destroying the links you did not mean to touch

`corpus/endpoints/post_entity_type_search.md`

## `POST /entity/<type>/_summarize`

Counts without paging rows. One `grouping` returns a field's distinct values and their counts at ~300ms, so rank a shortlist with it and never scan every field.

- Summarizing an unsummarizable field, `image`, answers 200 with a 37-byte body and no summary. It does
  not 400. Test that the key you asked for is in `summaries` before reading it.

- `group_name` is the rendered label and `group_value` the raw one. For a `timecode` field the rendered
  form is `HH:MM:SS:FF`, which is how the frame rate is recovered when no field exposes it.

- One call per field at about 300ms. Over 71 fields that is 21 seconds. Rank a shortlist by fill rate
  first and summarize only the candidates.

**Measured by**

- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `091_status_summary_exclusions` (findings) — Excluded statuses are invisible to REST: not in /schema at any scope, not writable by PUT. status_list honours them: fin plus an excluded omt rolls up to fin, omt alone to na.  
  rules: `doors/findings-schema`
- `006_pagination` (findings) — links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.  
  rules: `doors/findings-read`
- `021_media_resolution` (findings) — PublishedFile.path is returned with the LocalStorage join already done, so a client never reads LocalStorage or reassembles a root, but a platform whose storage root is unset reads null.  
  rules: `doors/findings-read`
- `081_dotted_image` (findings) — entity.Shot.image returns the Shot's thumbnail as a presigned S3 URL under attributes, same object, fresh signature, in the same call. image is_not null matched 50 Shots whose image reads null.  
  rules: `doors/findings-read`
- `020_summarize` (findings) — _summarize needs the same vendor Content-Type as _search, and one `grouping` call returns a field's distinct-value count and its empty count. At ~300ms a field, rank a shortlist, never scan.  
  rules: `doors/findings-filter`
- `030_complex_filters` (findings) — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.  
  rules: `doors/findings-filter`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
- `071_note_link_name_filter` (findings) — Filter notes about a thing on `note_links.<Type>.cached_display_name`: it resolves for every valid type, `code` 400s on Booking and `name` on all but Department. The path cannot be read back.  
  rules: `doors/findings-filter`
- `074_page_filter_coverage` (findings) — Every stored page filter with its tokens filled converts and runs 200 but one, yet recipe 003 kept unticked leaves (active "false"): 11 trees returned the wrong count. Drop them.  
  rules: `doors/findings-filter`
- `079_summarize_multi_grouping` (findings) — _summarize nests one group level per grouping entry, 3 deep tested, counts summing exactly. status_list rolls a group up to one status; status_percentage ignores any value and is no per-status share.  
  rules: `doors/findings-filter`
- `080_query_field_cost` (findings) — One _summarize with the parent leaf as `in [N rows]`, grouped on that link, reproduced open_notes_count for 300 Shots in 573 ms, against ~290 ms a row one call at a time.  
  rules: `doors/findings-filter`
- `077_page_change_stamps` (findings) — PageSetting has no updated_at; Page.updated_at moves when its layout is saved. Poll Page.updated_at; Shotgun_PageSetting_Change names which setting changed but its entity is null on 131 of 500.  
  rules: `doors/findings-observe`
- `003_query_fields_and_pages` (recipes) — Resolve a query field's value, and run the rows a saved Page shows  
  rules: `doors/recipes`
- `014_notes_about` (recipes) — Find the Notes about a Shot, Asset or Version by the name of the thing, and read what each Note is linked to  
  rules: `doors/recipes`

**Silent on this call**

- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `030_complex_filters` — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.
- `068_note_read_state` — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.

`corpus/endpoints/post_entity_type_summarize.md`

## `POST /entity/_text_search`

Free-text search across several types at once, returning a flattened row that is not the `_search` shape. `entity_types` is required and its value doubles as the per-type filter.

- There is no `fields` parameter. Every row is `name`, `links` and `status`, whatever the type, so a
  client that needs more re-reads the row by its `links.self`.

- `attributes.links` is a two-element array of strings, the linked row's type and its name, and it is
  `["", ""]` for a type that links to nothing. It is not an entity reference and cannot be followed.

- `entity_types` maps a type to a filter, so one call can be scoped differently per type. That is the
  only place in the API where a filter is keyed by the type it applies to.

- The shape is checked per key, so one call cannot mix the two forms. The key holding the value the
  `Content-Type` does not name decides the 400, and no type answers rows.

- One bad key fails the whole call: a field the type lacks, an operator its data type lacks, or a key
  no entity type is named by is 400 for every type in the map, not a type dropped from the answer.

- A group under `api3_hash` may hold another group, to at least three levels, and `or` returns the
  union of its branches. The array form takes basic condition arrays alone, and two of them are the
  `and` of both.

- The response has no `links`, so paging is `page.number` and there is nothing that says a further
  page exists. Ask until `data` is empty.

- `text` is matched case-insensitively against the row's name and against the name of the row under
  `attributes.links`. It is not matched against `description`.

**Measured by**

- `046_search_without_a_path` (findings) — `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.  
  rules: `doors/findings-filter`
- `053_text_search_matching` (findings) — `page.size` caps at 25 and defaults to 25 with no `links`, so page with `page.number`. Every word must match a case-insensitive substring of the name or of the linked row's name.  
  rules: `doors/findings-filter`
- `063_text_search_filter_shape` (findings) — An `entity_types` value follows the request Content-Type: an array of triples under api3_array, a `logical_operator` group under api3_hash, which alone nests. The other shape is 400 code 103.  
  rules: `doors/findings-filter`

**Silent on this call**

- `post_entity_text_search` — Free-text search across several types at once, returning a flattened row that is not the `_search` shape. `entity_types` is required and its value doubles as the per-type filter.
- `053_text_search_matching` — `page.size` caps at 25 and defaults to 25 with no `links`, so page with `page.number`. Every word must match a case-insensitive substring of the name or of the linked row's name.

`corpus/endpoints/post_entity_text_search.md`

## `POST /hierarchy/_expand`

Returns one level of the navigation tree the web interface draws. It refuses the vendor content types every other POST requires and accepts only `application/json`.

- **The content type is inverted.** `_search`, `_summarize` and `_text_search` refuse
  `application/json` and demand a vendor type; `/hierarchy/*` does the exact opposite. A client with one
  shared POST helper gets 415 on whichever half it did not write first.

- One level per call. `children` names the next paths and `has_children` says which are worth expanding,
  so walking a project is one call per node.

- Code 107 appears here and nowhere else in the corpus. It is a lookup that found the wrong number of
  rows, not a malformed request.

- `seed_entity_field` changed nothing on the probed site. Omit it until something shows it matters.

- A child has no `path` when its `ref.kind` is `empty`: `{"label": "No Shots", "ref": {"kind":
  "empty", "value": null}, "has_children": false}` is the placeholder for a level with nothing under it,
  and it is a child like any other. Read `path` with a default.

- `ref.kind` is `entity` for a row or a group that is one, `entity_type` for the ungrouped bucket,
  `list` for a group that is a list value, and `empty` for the placeholder.

- The `__none__` segment is reachable at two spellings. `_expand` writes
  `<field>/<GroupType>/__none__` and `_search` returns `<field>/__none__`; both answer the same rows,
  and the label is templated off the segment, so the second reads `Shots with no __none__`.

- A path is answerable whether or not `children` named it. Expanding a level whose grouping field has
  no rows answers one `empty` child, and the `__none__` path under that level still answers its rows.

**Measured by**

- `064_hierarchy_expand_buckets` (findings) — Dedupe `children` by `path` and keep the first. The `__none__` bucket is repeated once per group, byte-identical every time, and its rows are disjoint from every group's.  
  rules: `doors/findings-read`
- `046_search_without_a_path` (findings) — `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.  
  rules: `doors/findings-filter`

`corpus/endpoints/post_hierarchy_expand.md`

## `POST /hierarchy/_search`

Answers where a row sits in the navigation tree. `search_criteria` must be a hash keyed exactly `entity`, and every other shape is the same misleading `size must be 1`.

`size must be 1` does not mean what it says. Every one of these has one key and is refused:

| sent as `search_criteria` | result |
|---|---|
| `{"entity": {"type": "Shot", "id": 862}}` | 200 |
| `{"entity_type": "Shot"}` | 400 `size must be 1` |
| `{"Shot": 862}` | 400 `size must be 1` |
| `{"Shot": [862]}` | 400 `size must be 1` |
| `[{"entity_type": "Shot"}]` | 400 `must be a hash` |

- The key has to be the literal string `entity`. The error counts keys it recognises, not keys you sent,
  so an unrecognised key reads as a size problem and never names itself.

- `incremental_path` is the breadcrumb, one entry per level, and the last is the row. `path_label` is the
  same thing rendered for a person and it omits the project.

- The path goes through `sg_sequence`, a field name, so the tree follows the site's own navigation
  configuration rather than a fixed hierarchy.

- A row with nothing in the grouping field is returned as `/Project/<id>/Shot/sg_sequence/__none__`,
  without the type segment `_expand` puts there. Both spellings answer the same rows on `_expand`.

**Measured by**

- `064_hierarchy_expand_buckets` (findings) — Dedupe `children` by `path` and keep the first. The `__none__` bucket is repeated once per group, byte-identical every time, and its rows are disjoint from every group's.  
  rules: `doors/findings-read`
- `046_search_without_a_path` (findings) — `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.  
  rules: `doors/findings-filter`

`corpus/endpoints/post_hierarchy_search.md`
