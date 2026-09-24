# Findings — read: getting rows back

How the API behaves in this part of a session. Each rule is the entry's own **Teaches**, copied whole.

## 003_query

A dotted ?fields path comes back flat under literal key "sg_task.Task.content" in attributes; an entity field is returned under relationships as {data, links}. Never read a row from attributes alone.

- Two query styles both work: flat `filter[project.Project.id]=N` on a GET, and `filters: [[field, op, value]]` in a POST `_search` body. `_search` refuses `application/json` and needs the vendor Content-Type (probe 004).

- `sort=-id` with `page[size]`/`page[number]` behaves as documented and returns a different slice; no total count comes back with it (probe 006).

- An unknown name in `?fields` returns 200 with the key absent, so a typo reads as "no data", not as an error; the same name in `filter[]` 400s (probe 004).

- Asking for an entity field by bare name already yields `name` alongside `id` and `type`, so resolving a link for display costs no second call.

- The middle segment of a dotted path is checked against the field's `valid_types` in `?fields` and against the schema in a filter, so a wrong type is a 200 with the key absent and 400s only as a filter (probe 059).

`corpus/findings/003_query.md`

## 005_link_usage

On the sample project every Version links through `entity` (99% Shot, 1% Asset) and only 1% through `sg_task`, so measure link usage per site rather than hardcoding Task-linking.

- On the probed site `entity` is the load-bearing link and `sg_task` is near-unused: a client that assumes Version to Task finds nothing 99% of the time. Measure link usage per site before coding against it.

- `entity` is polymorphic. Read `relationships.entity.data.type` per row; do not assume Shot even at 99%.

- A multi-entity field can be uniformly empty (`playlists` 0/100), so absence of data is not absence of the field.

- `page[size]=500` returned 100 rows because the project holds exactly 100 Versions, not because of a cap: probe 016 shows 150 returns 150.

`corpus/findings/005_link_usage.md`

## 006_pagination

links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.

- `links.next` is not a terminator: it is present on empty pages too, so "follow next until absent" is an infinite loop. Stop on an empty `data` array.

- Only the stop signal is wrong. Explicit `page[number]` walks the set, and the short final page returns the remainder.

- No total is in a paged read. A GET returns `['data', 'links']` and no `meta` key, and `links` holds only
  `self` and `next`, never `last`. POST `_search` with `options.return_paging_info` returns the same two
  keys.

- Five option spellings (`options[return_paging_info]`, `options[include_paging_info]`, `page[totals]`,
  `include_count`, `meta[total]`) are accepted at 200 and change nothing; `page[size]=0` is 400
  `size must be greater than 0`.

- For "n of N", count with one POST `/entity/<type>/_summarize` and `{"field": "id", "type": "count"}`,
  which returned `{"summaries": {"id": 100}}` against the 100 rows the walk above found (probe 020).

`corpus/findings/006_pagination.md`

## 007_fill_rates

On the sample project 30 of 71 Version fields are populated. Rank by fill rate, but drop checkbox, summary and computed fields first: False and 0 are not null and read as 100% filled.

- A boolean reads as 100% filled because False is not null, and so does a summary count of 0 and a computed list. On the probed site 6 of the 17 fields at 100/100 hold one constant across all 100 rows, so a fill-rate ranking that includes them is wrong at the top.

- Exclude checkbox, summary and computed `data_type`s from fill ranking, or confirm a candidate with `_summarize` grouping, which returns a single group for exactly these fields. `probe 020` reaches the same trap from the `_summarize` side, where a checkbox cannot be filtered `is_not None`.

- On the probed site fill rate is bimodal: 100% or 1%, nothing in between. The 1% band is twelve media fields on the one uploaded Version, so a threshold anywhere between 2% and 98% separates structure from anecdote.

- The roster is not stable: the schema grew from 61 to 71 fields since this probe first ran, and all 10 additions read 0/100. Re-read `/schema/Version/fields` per run; one paged fetch of 100 rows then measures every field in a single call.

`corpus/findings/007_fill_rates.md`

## 018_project_listing

sg_status is not a liveness filter and is null on 15 of 22 projects; is_template, is_demo and archived are the discriminators, so pick the ones your list wants - is_demo hides the demo show.

- **Trap.** `sg_status is Active` is not a liveness filter. It is not set automatically, and on the probed site 7 of 22 projects have a value against 15 null, 8 of the nulls non-template working shows, so the filter returns 5 and hides the rest. What sets it on those 7 is unmeasured: this probe reads the tally, not the history.

- `sg_status` is a list field with valid values Bidding/Active/Lost/Hold and no `display_values`, so even where it is set there is no label to put in front of a user (probe 009).

- The checkboxes are the discriminators. On the probed site:

  | checkbox | True on |
  |---|---|
  | `is_template` | 7, the stock templates |
  | `is_demo` | 1, the shipped demo show |
  | `archived` | 0 of 22 |

  All three False leaves 14 of 22. The archived clause is proven harmless but not proven to exclude anything; keep it, it costs nothing.

`corpus/findings/018_project_listing.md`

## 021_media_resolution

PublishedFile.path is returned with the LocalStorage join already done, so a client never reads LocalStorage or reassembles a root, but a platform whose storage root is unset reads null.

| tier | what resolves | second call |
|---|---|---|
| 1. `Version.published_files` then `PublishedFile.path` | mac, windows and linux absolute paths at once, the LocalStorage join already done | yes, one `_search` |
| 2. `sg_path_to_movie`, `sg_path_to_frames` | one absolute path, no platform variants | no |
| 3. `image`, `sg_uploaded_movie` | a presigned S3 URL | no |

- **Tier 1 is untested here for two reasons, and only one of them is about the API.** On the probed site, Image, Rendered Image, Texture and USD PublishedFiles have **no `path` at all**, and `Version.published_files` is filled on 2 of 53 Versions: that is Flow PT data. The Movie paths that do exist point at files the operator has since deleted from disk: that is not.

- Read this as "this site has no publish history", never as "Flow PT paths are unreliable".

- Tier 2 holds one absolute path, so a value cannot resolve on two platforms, unlike `PublishedFile.path`, which returns one per platform the LocalStorage row defines a root for. On the probed site that is `mac_path` only, so `local_path_windows` and `local_path_linux` read null (`recipes/004`).

- On the probed site `sg_path_to_frames` is 0 of 53, leaving the sequence form untested: it is free text taking printf padding and the Shake `#`/`@` forms, so never assume `%04d`.

- Tier 3 needs no second call: `image` is a presigned S3 URL as a plain string, and `sg_uploaded_movie` is a dict with the same URL under `url`. It does not always resolve. On the probed site `image` is filled on 33 of 53 Versions in the sample project and 98 of 1057 site-wide, so test the field rather than assuming a fallback.

- **Trap.** `sg_uploaded_movie` cannot be filtered or summarized `is_not None`: 400 `API summarize() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter.` Same shape of trap as a checkbox (probe 020).

- Offer the operator whichever tiers a given Version can deliver rather than picking one for them.

`corpus/findings/021_media_resolution.md`

## 023_pages

A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.

Three types answer the question, and a page's configuration is split across two of them.

| type | what it holds | how a client reaches it |
|---|---|---|
| `Page` | the page itself: `name`, `page_type`, `entity_type`, `project`, `ui_category`, `system_owned` | `GET /entity/pages?fields=...` |
| `PageSetting` | the layout, in `settings_json` | `_search` on `page is {"type":"Page","id":N}` |
| `PageHit` | one row per view, `page` and `user` only | `GET /entity/page_hits` |

There is no `DisplayColumn` type, and `Page` has no field naming a column.

- A site-level page is a `Page` whose `project` is null, and nothing else about it differs. Both kinds
  read from the same endpoint, both hold `PageSetting` rows of the same shape, and both take the same
  filters.

- The two are told apart by `project` alone, so `filter[project.Project.id]=N` returns a
  project's pages and `[["project","is",null]]` returns the site-level ones. Send the string `"null"`
  to the flat filter and it 400s with `got String: "null"`; the operator wants a real null.

- `PageSetting.settings_json` is `text` in the schema and decoded JSON in the response, so parse nothing.

- Two shapes come back under one field: an object is the page's shared layout and its `user` is null,
  an array is one user's override and its `user` is set. Read `[["page","is",{...}],["user","is",null]]`
  to get the shared one and ignore the rest, or a personal column order will read as the page's.

- The shared layout is a widget tree of `{type, settings, children}`. `children.body.settings` holds
  `entity_type`, `mode`, `sorts`, `grouping` and `filters`; `children.body.children.list_content.settings`
  holds `columns` in display order, plus `column_widths` and `column_display_names`.

- The override array is `[{spec_path, settings}]`, where `spec_path` is that same tree path with `|` between the segments,
  so `body|list_content` patches the grid.

- `columns` are schema field names, usable in `?fields` as they stand, and a dotted path such as
  `created_by.HumanUser.email` appears among them.

- Some are stale or web-only: on the probed site, 5 of the 21 list pages in one project named a column absent from that type's `/schema/<Type>/fields`.
  `?fields` answers 200 and drops a name the type does not have, so a stale column costs a missing key
  rather than an error. Check the list against `/schema/<Type>/fields` to know which columns you lost.

- `filters` is the web condition tree (`path`, `relation`, `values`, `logical_operator`), not the
  `_search` array of probe 017. The names line up, so a converter is a walk over `conditions`, but the
  tree also holds `active`, `filter_name` and `filter_id` for a saved filter, and a
  `top_level_project_filter` condition that duplicates the project scope.

- Every filter on `settings_json` is accepted and ignored. On the probed site all 30145 rows come back
  for `contains "ZZZNOPE"`, for `is null` and for `is_not null` alike, while `[["page","is",null]]`
  on the same type returns 26372, so the endpoint filters fine and the field does not. Never search
  layouts server-side; page the rows and inspect them yourself.

- `_summarize` disagrees with the listing on `Page`. On the probed site an unfiltered `record_count`
  returned 2576 against 1217 rows actually paged, while the same count filtered by project agreed
  exactly, summing to 1217 over 22 projects plus 125 project-null. Count pages by summing per-project
  and per-null, never with one unfiltered call.

- `Page` and `PageSetting` filter and sort like any other type: the bogus-operator 400 enumerates the
  normal relations for each field's data type, and `sort` on a name that is not a field is accepted at
  200 and ignored.

`corpus/findings/023_pages.md`

## 026_result_order

Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.

- `["id", "in", [...]]` returns id ascending, never the order of the list. A caller that must preserve
  a selection re-sorts against what it sent: `pos = {i: n for n, i in enumerate(ids)}`, then
  `rows.sort(key=lambda r: pos[r["id"]])`. The bug hides because an already-ascending list comes back
  looking honoured.

- With no `sort`, the order is id ascending, and it held over five identical calls. Paging is stable:
  five walks of 100 rows at `page[size]=10`, including the unsorted one and one keyed on a
  low-cardinality status, each returned every row once, in the order of the same query read unpaged.

- Sorts fail silently where filters fail loudly (probe 017). A `summary` field, a `url` field and a
  name that does not exist all return 200 with the rows in default order; the same three names in a
  filter 400 and name the reason.

- Only sort *syntax* errors: an empty value, a space, a leading `+`.
  There is no way to detect a dropped sort from the response, so verify a sort field against
  `/schema/<Type>/fields` before relying on it.

- Multi-key sort is comma separated with `-` per key, and id ascending is the implicit tiebreak:
  `sg_status_list,id` returned the identical page to `sg_status_list` while `sg_status_list,-id` did
  not.

- A dotted path sorts (`entity.Shot.code` here, and site-wide `project.Project.name` reverses
  under `-`). POST `_search` takes `"sort"` only as the same string; the array-of-objects spelling
  400s `sort array is not valid`.

`corpus/findings/026_result_order.md`

## 048_one_record_beyond_crud

POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.

| call | what it is | what a caller assumes |
|---|---|---|
| `POST /entity/<type>/<id>` | revive a retired row | an update, or a create with an id |
| `GET /entity/<type>/<id>/<field>` | one image or attachment field, with a download | any field, read cheaply |
| `GET .../relationships/<related_field>` | the link list, unwrapped | a paged sub-collection |
| `PUT /entity/projects/<id>/_update_last_accessed` | stamps a user's project history | something readable back |
| `GET /exports/page/<page_id>.<format>` | a saved page view as CSV | any page, any format |

- `POST` on a single record is `DELETE` run backwards. `?revive=1` is required, `revive` must be
  truthy (`0` and `false` are refused with `revive must be true`), and a JSON body is accepted and
  discarded, so a client reaching for it as a `PUT` alias gets a 400 telling it about a parameter it
  never sent. The row comes back with the field values it had when it was retired.

- The revive response is `{"data": {"type", "id"}, "links", "meta": {"did_revive"}}` and has no
  `attributes` key, less than any other write returns (probe 024). `did_revive` is `false` on a row
  that was already live, at 200, which is the only way to tell a revive from a no-op.

- `?fields` is ignored here as on every other write. On the probed site a successful revive logged one
  `Shotgun_Shot_Revival` event and a no-op logged none.

- **`/<field>` is not a cheap single-field read.** Every non-file field is a 400 naming the field:
  `Field Version.code is not an image or attachment.` A dotted path is a 406 with a one-byte body,
  because the last dotted segment is parsed as a format extension. Use `?fields=` on
  `GET /entity/<type>/<id>` for anything else.

- `?alt=original` and `?alt=thumbnail` turn the same path into a download: a 302 to the presigned
  storage URL, which a redirect-following client fetches as the bytes. `Range` is forwarded to
  storage and answers 206 with `Content-Range`, so a client can read a header off a large movie
  without pulling the file. `Range` without `alt` is ignored and the field hash comes back at 200.

- `relationships/<related_field>` returns the identical `data` a normal read puts under
  `relationships`, minus the `links.related` pointer, and it is not paged: a 60-link field answered
  all 60 rows with no `links.next`, and `page[size]`, `page[number]`, `fields` and `sort` were all
  accepted and ignored.

- It saves 233 bytes on a single entity link and 183 on 60 of them, so it is
  worth a call only when the link list is the whole request.

- `_update_last_accessed` answers 200 for a `user_id` that does not exist and returns the same
  `{data, links}` either way, so nothing in the response says whether it did anything.

- On the probed site `Project.last_accessed_by_current_user` read `null` before and after, and no `EventLogEntry`
  was written, because that field is relative to the requesting user and a script is not the user it
  stamps. There is no read-back over REST; treat the call as write-only.

- The path is fixed to `projects`. `PUT /entity/shots/<id>/_update_last_accessed` is a 404 with a null
  `detail`, and `GET` on the project path falls through to the file-field route and answers
  `Field 'Project._update_last_accessed' does not exist.`, which names a field nobody asked for.

- `<format>` is not validated. `.json`, `.xml` and `.txt` all answer, and the extension sets the
  response `Content-Type` while the body stays the same plain-text string. Drop the extension and the
  route stops matching: 404, code 103. Whether a successful export honours anything but `csv` is
  unmeasured, because nothing exported.

- **Export is off by default and there is no field that says so.** A page id that does not exist
  answers `Trying to perform export for retired Page id=999999999`, and a non-numeric id is read as
  `id=0`, so a 422 does not distinguish a missing page from a page whose view is not marked
  exportable.

- On the probed site 52 pages across all 27 `page_type` values answered 422 and none
  answered 200; `Page` has no `exportable` field and the flag is not in the layout `settings_json`
  probe 023 reads, so a client cannot discover which pages will work without trying each one.

`corpus/findings/048_one_record_beyond_crud.md`

## 059_dotted_path_type_check

The middle segment of a dotted path is checked against the field's valid_types in a projection and against the schema alone in a filter: the projection drops the key at 200, the filter 400s. **[partial]**

not measured: whether a filter through a type outside valid_types is evaluated or matches nothing; no row on a read-only project links one, so it needs a write

- Two parsers, two rules. A projection checks the middle segment against the field's `valid_types`; a
  filter checks it against the site schema and ignores `valid_types`.

  | path | in `?fields` | on the left of a filter |
  |---|---|---|
  | middle in `valid_types`, leaf real | the value, or `null` when the row links another type (`field_types/entity`) | evaluated |
  | middle a real type outside `valid_types` | key absent, 200 | 200, 0 rows here |
  | middle names no type | key absent, 200 | 400 `API read() Version.entity.Bogus.code doesn't exist.` |
  | leaf missing on the middle type | key absent, 200 | 400 `API read() Version.entity.Shot.bogusfield doesn't exist.` |

- A template that writes `entity.Asset.code` against a Shot is not an error a client can catch on read.
  It is `null` while the type is a `valid_types` member and the key is gone once it is not, which is the
  same quiet drop a bogus `?fields` name gets (probe 004). Read the link out of `relationships` and
  branch on `data.type` rather than asking for a path per type.

- To check a path before shipping it, send it once as a filter. The type and the leaf are both
  validated there and the 400 names the whole path, `Version.entity.Bogus.code`, at `code: 103`.

- `api3_array`, `api3_hash` and `GET ?fields` returned the same key and the same value for all eight
  paths, so the vendor Content-Type switches nothing here either (probe 004).

`corpus/findings/059_dotted_path_type_check.md`

## 060_entity_dict_name

The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.

**`name` is `cached_display_name`, not the identity field.** Every type `Version.entity` accepts on the
probed site, plus the three a client reaches through another field. One row per type, each created in
the sandbox and linked with a single `PUT`.

| target type | identity field | dict `name` equals |
|---|---|---|
| Asset, Level, MocapTake, Reel, ShootDay, Shot, Sequence, Launch, Camera, Slate, SourceClip | `code` | the identity field |
| the site's two enabled CustomEntity slots (probe 008) | `code` | the identity field |
| Task, reached through `sg_task` or written into `entity` | `content` | the identity field |
| Note, reached through `notes` or written into `entity` | `subject` | the identity field |
| Project, reached through `project` | `name` | the identity field |
| Delivery | `title` | `cached_display_name`, which is `#<id>: <title>` |

Sixteen of the seventeen agree with the identity field because `cached_display_name` is a copy of it.
Delivery is the one that does not, and it is what a client renders in a picker, so read
`cached_display_name` and never reconstruct the identity field from it.

**It is the one type-agnostic name.** `name` was present and populated in all 17 dicts, and never `null`
except when the row itself was gone. A client holding a link needs no second call and no per-type map of
`code` against `content` against `subject`.

| where the link comes back | element shape |
|---|---|
| `entity`, `sg_task`, `project`, `user`, `created_by` | `{id, name, type}` |
| `notes`, `tasks`, `playlists`, `sg_ai_generated_from` | a list of `{id, name, type}` |

`multi_entity` elements are the same three keys with the same `name` (`field_types/multi_entity`).

**Headers change nothing.** `GET /entity/versions/{id}`, `POST _search` under
`application/vnd+shotgun.api3_array+json` and the same `_search` under `...api3_hash+json` returned
byte-identical `relationships` blocks, confirming probe 004 on the dict's contents.

**`cached_display_name` is readable, not filter-only.** `?fields=cached_display_name` and a `_search`
`fields` list both answered it on Task, Shot, Asset, Project, Version and Note, and it matched the dict
`name` in each. Task is the case that matters: the dict's `name` and the field `cached_display_name` are
the only two ways to name a Task, since `name` and `code` do not exist on it (`entity_types/Task`).

| asked for | Task, Shot, Asset, Version, Note | Project |
|---|---|---|
| `?fields=cached_display_name` | the display name | the display name |
| `?fields=name` | 200, `attributes` empty | 200, `name`, a real field |
| `["name", "is", "x"]` as a filter | 400 `API read() <Type>.name doesn't exist.` | matches |

`?fields=name` is the silent drop probe 004 records: a client that asks for `name` on a Version gets 200
and nothing, which reads as "no display name" rather than "wrong field".

**A gone target is dropped, never stale.** Nothing holds a dead `{id, name, type}`.

| the link | after the target is deleted |
|---|---|
| `sg_task` | `data` is `null` |
| `playlists` and every other `multi_entity` measured | the element is removed from the list |
| `entity`, when the target is the Shot the Version hangs off | the Version itself is retired |
| a filter on any of the three, against the deleted id | 200, 0 rows |

- **Destructive.** `DELETE /entity/shots/{id}` returned 204 and retired every Version linked to that Shot
  through `entity`: the Version answered 404 on a `GET`, 0 rows in `_search`, and 200 with `entity` null
  under `options[return_only]=retired`. Deleting a Task or a Playlist retires only itself. Read the
  children before deleting a parent; the 204 names nothing it took with it.

`corpus/findings/060_entity_dict_name.md`

## 064_hierarchy_expand_buckets

Dedupe `children` by `path` and keep the first. The `__none__` bucket is repeated once per group, byte-identical every time, and its rows are disjoint from every group's. **[partial]**

not measured: how the web interface draws the repeated node. Its tree needs a session a person approves (probe 052), and the saved token had expired

- **Dedupe `children` by `path` and keep the first.** The bucket is emitted once after every group
  and each copy serialises identically, key order included, so the first is the whole of it.

- The repeat count is the number of groups, not the number of ungrouped rows. On the probed site one
  project has 44 empty sequences and 44 unsequenced Shots: 44 groups that expand to `No Shots`, and
  44 copies of the one bucket that holds all 44 rows.

- `has_children: true` on the bucket is a shape, not a count. A project with nothing ungrouped still
  lists it, and expanding it answers a single child of `"kind": "empty"` labelled `No Shots`.

- A row is under the bucket or under a group, never both. Bucket rows and group rows summed to the
  project's own Shot count on both projects measured that way.

- **A grouping field with no rows hides every row under it.** On the probed site a project with 13
  Shots and no Sequence answers `/Project/<id>/Shot` as one `"kind": "empty"` child labelled
  `No Shots`, with no bucket among the children. The bucket path answers all 13 when asked for
  directly, so build it rather than trusting `children` to name it.

- Grouping by a list field repeats nothing: `/Project/<id>/Asset` returns one `__none__` child, last,
  with `"kind": "list"`. The repetition measured here is the entity-grouped case.

- `_expand` and `_search` spell the same bucket differently, and both answer: `_search` writes
  `sg_sequence/__none__` where `_expand` writes `sg_sequence/Sequence/__none__`. The label is
  templated off the segment, so the first reads `Shots with no __none__`.

`corpus/findings/064_hierarchy_expand_buckets.md`

## 072_page_layouts

A page's views are root settings.layouts [{name, display_name}], each name a child of the root. Query widgets sit at /body, inside a view, or in tabs: walk the tree, never read /body alone. **[partial]**

not measured: Which name the export's <layout_name> takes: every export on the probed site answers the page-level 422, so layouts[].name and display_name could not be told apart. Blocked on the site.

Every node is `{type, settings, children}`, and `children` is an object keyed by a name the parent's
settings refer to. Three places hold more than one query widget:

| holder | where the list is | what the names address |
|---|---|---|
| views | root `settings.layouts`, `selected_layout` | root children: `body` when there is one view, `layout_N` on a canvas with several |
| a canvas view | `Canvas.Body.settings.rows`, then `Canvas.Row.settings.column_widgets` | `row_N/child_N/child`, each a widget such as an EntityQueryPage |
| tabs | `SG.Widget.Tabs.settings.tab_order` | the Tabs widget's children: `tab_N`, `embedded_<type>_query`, `all_fields` |

- A page with no `layouts` key has one view and it is `body`. Recipe 003's `page_query` reads only
  `/body`, so on the probed site it misses 68 query widgets inside canvas views and every tab.

- An EntityQueryPage always holds its sibling views as children (`list_content`, `thumb_content`,
  `card_content`, `calendar_content`, `sched_content`, often `browser_content`); `mode` names the one
  showing (probe 073).

- `allowed_permission_group_codes` and `denied_permission_group_codes` gate a view or a tab by
  permission group code (`admin`, `artist`, `manager`). A runner acting for a person filters on them.

- On the probed site one system-owned `stream_detail` page holds 3 shared rows; the other 1106 pages
  hold one. `P.shared` keeps the last, so check the count before trusting one row.

- On the probed site 127 pages hold no query widget at all: app pages (`inbox`, `my_tasks`,
  `media_center`) whose widget is the whole page.

- The export's `<layout_name>` is either `layouts[].name` or `display_name`. The endpoint answers 422
  for both and for a name no view has (`endpoints/get_exports_page_id_layout_format`).

`corpus/findings/072_page_layouts.md`

## 073_page_grid_settings

Stored pages group one level deep (one of 438 goes two), summarise a column once in 41 grids, and colour columns by DisplayColumn id, a type REST cannot read. mode is list on 94%.

What a page runner has to implement, by how often the probed site stores it:

| setting | where | stored shape | reproducible over REST |
|---|---|---|---|
| `mode` | query widget | `list`, `thumb`, `browser`, `card`, ... | yes; `list` is the grid |
| `grouping` | query widget | `false`, or a list of `{column, method, direction}` | yes: `_summarize` nests one level per entry (probe 079). `method` is a `_summarize` grouping type (`exact`, `week`) |
| `sorts` | query widget and `list_content` | lists of `{column, direction}` | the first key via `?sort`; the rest client-side. The two lists disagree on 93 of 383 grids |
| `pivot_grouping`, `pivot_sorts` | query widget | the rows a pivot column (`step_N`) rolls up | the `step_N` column reads as a field (recipe 003) |
| `summaries` | `list_content` | `{<column key>: {type, column, value}}` | `status_list` yes; `status_percentage` with a `value` no (probe 079) |
| `formatting_rules`, `rule_type` `row` | query widget | a `condition` in the web tree shape | yes: convert it like a filter (recipe 003) |
| `formatting_rules`, `rule_type` `display_column` | query widget | `display_column: {type: "DisplayColumn", id}` | no: the rule names no field, and DisplayColumn is not a REST type |
| `records_per_page` | `list_content` | 25, 50, 100 | a client paging choice |

- `grouping: false` means none. Test for a list, not for truthiness of the key.

- A summary key can end in a pivot suffix, `shots.Shot.step_0$sg_status_list`, which names no column in
  the grid's `columns`. The `$` joins a pivot path to the field it summarises.

- A `display_column` rule's `page_id` points at another page on 1700 of 1701 rules: the rules were copied
  from the page they were first made on. Key a rule on the widget holding it, not on `page_id`.

- `server_side_filters: "my_notes"` names a filter the server applies and the tree does not show; on
  the probed site one widget uses it.

`corpus/findings/073_page_grid_settings.md`

## 075_page_overrides

A per-user override patches columns, widths, sorts, mode and the filter panel at any spec_path, "" meaning the root. One row per user and page; 3 of 32 patches name a path the shared tree lacks.

| `spec_path` | patches | resolves to |
|---|---|---|
| `""` | the root: `filter_panel_filters`, `filter_panel_settings`, a date range | the page widget itself |
| `body` | `mode`, `sorts`, `group_settings` | the query widget |
| `body\|list_content` | `columns`, `column_widths`, `wrapped_columns`, `wrap_column_header_text` | the list grid |
| `layout_N\|row_N\|child_N\|child` | a widget inside a canvas view | whatever that child is |

- Apply a patch by walking the shared tree's `children` along `spec_path` split on `|`, skipping empty
  segments, then merging `settings` key by key. An empty `spec_path` is the root.

- A person's filter choice is stored under the root as `filter_panel_filters`, not in `body.settings.filters`.
  A runner honouring an override has to read both.

- A patch can name a child the shared tree does not have (`body|list_content|step_0`, a pivot
  sub-grid); 3 of 32 do on the probed site. Skip it rather than creating the path.

- Rows per (user, page) were 1 in every case, so no merge order between rows is needed on the probed site.

- A person reads everyone's overrides, not only their own (probe 076).

`corpus/findings/075_page_overrides.md`

## 076_page_visibility

The script user is not the widest reader of Page: an Admin read 2048 pages where the script read 1107 and 404s on the rest. An Artist read 107. Every level reads every person's override.

- **The script user does not see every page.** Every other count in this corpus is an `api_admin`
  number and the widest read on the site (probe 027); on `Page` an Admin reads 941 more, 41 of them
  unshared. To list the pages a person sees, read as that person with `sudo_as_login`; the script's list
  is neither a superset nor theirs.

- A page the script cannot see answers 404 by id, and its PageSetting rows do not come back under
  `page in [...]` either.

- On the probed site the Artist reads no project page at all and 107 site-level ones, so a Page+ list
  for an Artist is empty for projects even where probe 027 shows that Artist reading 8 projects.

- **`current_user_can_see` can fail a whole read.** As an Admin, asking for it in `fields` turned two
  pages of 500 into 400 code 104 `Read failed for entity type [Page]` with `detail` null, and the same
  rows read fine without it. Leave the field out of listings; read it per page if it matters.

- Overrides are not private over REST. A person reads every other person's PageSetting row, by id and
  by `_search`, so a column layout is visible site-wide.

`corpus/findings/076_page_visibility.md`

## 081_dotted_image

entity.Shot.image returns the Shot's thumbnail as a presigned S3 URL under attributes, same object, fresh signature, in the same call. image is_not null matched 50 Shots whose image reads null.

- A dotted image column costs nothing extra. It is returned under `attributes` keyed by the dotted name,
  as the same S3 object the Shot's own `image` names, re-signed for this read (`field_types/image`).
  Key a cache on the object path, never on the full URL.

- **`image is_not null` and a null read disagree.** On the probed site 50 Shots match `is_not null` and
  read `null`, and the dotted filter matched all 1500 Tasks while 250 of them read `null`. Filter to
  narrow, then test the value you read.

- `GET /entity/shots/<id>/image` returns the same URL wrapped in `{"data": ...}`, one call per row.
  Prefer the dotted field on the row you already fetch.

`corpus/findings/081_dotted_image.md`

## 082_page_size_cap

page[size] takes 1 to 5000 inclusive; 5001 is 400 "size must be less than 5000". Omitted, it is 500. A page costs ~330 ms whatever its size up to 500, so read big pages.

| `page[size]` | result |
|---|---|
| omitted | 500 rows |
| 1 to 5000 | that many rows, or the remainder |
| 5001 and above | 400 `size must be less than 5000` |
| 0 or negative | 400 `size must be greater than 0` |

- The message is off by one: 5000 itself is accepted.

- A call's fixed cost dominates. On the probed site 100 and 500 rows cost the same ~330 ms, and 2000
  cost 468 ms, so reading a whole page of 1900 rows at 2000 a call took 788 ms against 6257 ms at 100.

- Stop on the empty page, not on `links.next` (probe 006): that last empty call is part of every total above.

`corpus/findings/082_page_size_cap.md`

## 088_project_template_defaults

The per-entity-type default is readable at `Project.tracking_settings.default_task_template.<Type>`, a `{type, id, name, valid}` dict. `Project.task_templates` is a separate list, not the default. **[partial]**

not measured: Whether a Shot or Asset created over REST without `task_template` gets the default: blocked on the site, since testing it means writing a project's tracking settings.

| where | holds | readable |
|---|---|---|
| `Project.tracking_settings.default_task_template.<EntityType>` | the default template for that type, as `{type, id, name, valid}` | yes, `?fields=tracking_settings` |
| `Project.task_templates` | a list of templates attached to the project | yes |
| `ProjectTaskTemplateConnection` | the join row behind `task_templates` | yes, `/entity/project_task_template_connections` |
| `TaskTemplate.projects` | the same list from the other side | yes |
| `/preferences` | nothing about templates | n/a |

- **The default and the attached list are different data.** On the probed site the one project with a
  default for Asset does not list that template in `task_templates`. Read the default from
  `tracking_settings`, never infer it from the list.

- On the probed site `default_task_template` is absent on 16 projects and `{}` on 5. Absent, `{}` and a
  missing entity-type key all mean no default. `valid` read `"valid"`; no other value was seen.

- `tracking_settings` is a blob: no filter reaches into it (`field_types/serializable`), so finding
  projects with a default means reading every project's value.

- **Whether the API applies the default is unmeasured.** Probe 083 found `task_template: null` on a
  create generates nothing in a project with no default. Send `task_template` explicitly rather than
  rely on the project default.

`corpus/findings/088_project_template_defaults.md`
