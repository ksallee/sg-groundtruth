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
