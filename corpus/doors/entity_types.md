# Entity types

One per standard entity type: what it is, how it is identified, created and linked. Each rule is the card's own **Traps**, copied whole.

## Asset

Only project is required to create an Asset; omit code and the server writes "New Asset <id>", and two assets in one project may share a code, so key on id and never on code.

- `code` is not unique and not required. A client keying an asset by name silently merges or duplicates
  rows. Match on `id`, and treat a `code` lookup as a query that can return more than one row.

- `POST` with `project` alone succeeds, so a request that dropped its payload creates a real asset named
  `New Asset <id>` rather than failing. Send `code` explicitly and check what came back.

- The 400 for a missing project is `code: 103` with `source: {}` and `detail: null`. The message is in
  `title`; a client reading `detail` sees nothing.

- Reading `attributes` alone shows no links at all: `project`, `shots`, `sequences` and `tasks` are all
  under `relationships` (probe 004).

`corpus/findings/entity_types/Asset.md`

## Attachment

POST /entity/attachments answers 201 on an empty body and returns a row with no file; this_file is editable on create only, so bytes reach a site through the upload dance and never through a create.

- A create with an empty body answers 201. A request that dropped its payload leaves a real Attachment row
  with no file, no filename and no link, and it cannot be repaired: `this_file` is create-only.

- `file_extension` and `file_size` do not fill in. On the probed site, over a 500-row page, `file_size` was
  set on 130 rows and `file_extension` on 85, all created between 2013 and 2019; every row created 2025 or
  later read null on both, some of them more than a year old.

- Take the size from the bytes you uploaded and the extension from `filename`. Probe 014's null columns are the steady state, not a race.

- `processing_status` returns `thumbnail_pending_us` straight after an upload, which is not one of the four
  values its own `valid_values` declares, and it reverts to `null` once transcoding finishes. A client
  matching against `valid_values` sees an unknown token, then nothing.

- Reading `attributes` alone shows no links: `attachment_links`, `project` and `local_storage` are all
  returned under `relationships` (probe 004).

`corpus/findings/entity_types/Attachment.md`

## Cut

A Cut stores an edit, it does not model one: no field is computed or validated, and `cut_items` is returned sorted by the item's display name rather than by `cut_order`.

- **The server computes nothing.** `duration` and the two timecode strings keep what was written: a Cut
  holding 6 items whose last frame is 647 still read `duration` 168 and `timecode_end_text`
  `'01:00:07:00'`, written when it held 3. The extent and every sum are the client's (`recipes/007`).

- **`cut_items` is not the running order.** It is returned sorted by the item's display name:
  `['aaa_last', 'sh010', 'sh020', 'sh030', 'sh030_gap', 'sh030_overlap']` against `cut_order`
  `1, 2, 3, 4, 5, 6` on the same six rows, as `Playlist.versions` does. Read the items with
  `POST /entity/cut_items/_search`, `[["cut", "is", {"type": "Cut", "id": N}]]`, `sort: "cut_order"`.

- **Deleting a Cut leaves its CutItems behind.** `DELETE /entity/cuts/<id>` answered 204 and the items
  survived with `cut` `null`, reachable only through `[["cut", "is", None]]`. Delete the items first.

- **The schema is not an exhaustive description of the response.** `GET /entity/cuts/<id>` returns
  `platform_id` and `platform_revision_id` under `attributes`, and neither appears in
  `/schema/Cut/fields`. A client that builds its field list from the schema alone will not ask for them,
  and one that validates a response against the schema will reject a legal row.

- `fps` is the only frame rate on Cut or CutItem, it is `null` until someone writes it, and a `float`
  reads back as the string `"24.0"` (`field_types/float`). Nothing on a CutItem points at it.

- Read only: `created_at`, `created_by`, `id`, `image_blur_hash`, `image_source_entity`, `open_notes`,
  `open_notes_count`, `updated_at`, `updated_by`.

`corpus/findings/entity_types/Cut.md`

## CutItem

Nothing on a CutItem is unique and `code` repeats across Cuts, so an id found by a code search may sit on another Cut: check `cut` before every update or the write lands on the wrong edit.

- **An id does not say which Cut a row is on, and `code` repeats across Cuts.** A search on `[["code",
  "is", "sh010"]]` returned items `(46, cut 19)` and `(53, cut 20)`. A blind `PUT /entity/cut_items/53`
  with no `cut` key answered 200, left `cut` at 20, and overwrote the other Cut's item.

- Deciding update-versus-create on "does it have an id" is the data-loss path: read the candidates
  filtered on `cut`, or ask for `cut.Cut.id` and drop every id that does not match.

- **Sending `cut` in an update moves the item** to that Cut at 200, and `Cut.cut_items` with
  `{"multi_entity_update_mode": "add"}` on the other side does the same, leaving the previous Cut
  holding `[]`.

- **`cut_order` is not a sequence the server maintains.** It is neither unique nor mandatory nor
  contiguous, `null` sorts last in both directions, and rows with an equal `cut_order` break the tie by
  `id`. It is also what a recut changes, so it is not a key: pair items across two edits on `code` plus
  its occurrence, scoped to the Cut (`recipes/007`).

- Read only: `created_at`, `created_by`, `id`, `image_blur_hash`, `image_source_entity`, `updated_at`,
  `updated_by`.

`corpus/findings/entity_types/CutItem.md`

## Delivery

Delivery has two independent Version links, sg_versions and version_sg_deliveries_versions; writing one leaves the other empty, and only the second mirrors Version.sg_deliveries.

- `reply_content` returns a developer warning instead of a value. On a Delivery holding one real Reply it
  read `'Warning: If you see this displayed in the UI, it means the widget is not respecting grid_column
  = false.'` The thread is `replies`, or `POST /entity/replies/_search` on
  `[["entity", "is", {"type": "Delivery", "id": N}]]` (`entity_types/Reply`).

- `sg_delivery_type` has `valid_values: []`, so every write is
  `400 … 'Final' is not a valid list value. Valid list values: ''.` An empty vocabulary is a field that
  can never be set, not a free-text field.

- A Reply reads back HTML-escaped through one field and not the other: `content` containing `"` is
  returned verbatim by `Reply.content` and by the `name` of the `Delivery.replies` link, and as `&quot;`
  by `Reply.cached_display_name`.

- Eight fields are read-only, `created_at`, `created_by`, `delivery_number`, `id`, `image_blur_hash`,
  `image_source_entity`, `updated_at`, `updated_by`, and they refuse a write two different ways:

| written | answer |
|---|---|
| `created_at` | 400 code 103 `API update() Delivery.created_at is editable on create only.` |
| `delivery_number` | 400 code 104 `The field is not editable for this user: [Delivery.delivery_number]. Rule: API Admin -- PermissionRule 336: DENY update_field FOR entity_type => Delivery, field_name => delivery_number, field_value =>`, so the message depends on the script's role (probe 027) |

`corpus/findings/entity_types/Delivery.md`

## HumanUser

`sudo_as_login` matches `login` and never `email`; a create is 401 unless it sends `sg_status_list: "dis"`, and an empty `projects` is not site-wide access. **[partial]**

not measured: what an active user costs in seats, since the site refuses to create or promote one; and whether `projects` or the permission rule set produces the project subset, which needs two users the site does not have

- Key on `login`. `email` is not unique, `name` is not unique, and `code` does not exist.

- A create is 401 and not 400, so a client checking for a 4xx body shape finds `code: 110` where every
  other create failure is `code: 103`.

- The only creatable user is a disabled one, and `PUT sg_status_list: "act"` is refused the same way.
  A script cannot onboard a person on this site.

- `permission_rule_set` and `can_impersonate_this_user` are read only: what a person may do and who
  may act as them are granted in the web interface and read over REST.

- A deleted user is retired, not erased, and its `login` becomes reusable, so two rows can hold the
  same login with only one of them live.

`corpus/findings/entity_types/HumanUser.md`

## LocalStorage

A LocalStorage row is site-wide and admin-only to write: an Artist reads every row and is refused on create, update and delete. `code` must be unique among live rows, and a DELETE frees it for reuse.

- **Writing one is admin-only.** Impersonating an `Artist` on the probed site returned every row on a
  `GET` and refused all three writes, each at 400 code 104: `Entity of type LocalStorage cannot be
  created by this user.`, `The field is not editable for this user: [LocalStorage.mac_path].` and
  `Entity of type LocalStorage can not be deleted by this user.`

- A client that offers "point at any folder" as a setup step has to say that an administrator runs it.

- A row with no root on any platform is a 201, and nothing reports it as incomplete. The path a
  client then sends is refused as matching no defined storage (`recipes/004_register_published_file`).

- The refusal to write is a 400, not a 401 or a 403, so a client branching on the status code reads it
  as a bad body.

- A caller with no root to write under does not need a row at all: `PublishedFile.path` takes the
  three-call upload instead (`recipes/013_publish_file_bytes`).

`corpus/findings/entity_types/LocalStorage.md`

## Note

A Note is titled by `subject` and bodied by `content`; only `project` is required to create one, `attachments` link in that same call, and a bare write to `replies` destroys the Reply rows.

- **`client_note` cannot be set over the API**, on create or after. Every update answers `400 API update() Note.client_note is editable on create only.` A client-facing Note over REST is `sg_note_type: "Client"`, an editable `list`, and nothing else; it leaves `client_note` false (probe 069).

- **A bare `replies: []` write deletes the Reply rows.** Trimming that list the way a client trims any
  other `multi_entity` field destroys the replies, with nothing at the id after. Keep it out of a `PUT`.

- A bare list written to `note_links` replaces the set, so appending one link with
  `[{"type": "Shot", "id": N}]` drops every other thing the Note was about
  (`field_types/multi_entity`).

- `subject` is optional, not auto-filled and not unique: a request that dropped its payload creates a
  real titleless Note, and two Notes in one project may share a subject. Key on `id`.

- `meta` is editable on create only. Seed it in the `POST` or never: every later `PUT` answers
  `400 API update() Note.meta is editable on create only.` (`field_types/jsonb`).

`corpus/findings/entity_types/Note.md`

## Playlist

Playlist.versions reads back sorted by the Version's code, never in the order written; the human order is sg_sort_order on PlaylistVersionConnection, which a write through the field leaves null.

- A playlist read back is not the playlist a reviewer sees. Sorting by `code` puts `sh010_v10` ahead of
  `sh010_v9` and interleaves shots; take the order from `PlaylistVersionConnection.sg_sort_order`.

- Appending with a bare list drops every other Version at 200. The query-string spellings of the update
  mode do the same (`field_types/multi_entity`). Send the mode in the body.

- Unlinking a Version destroys its `sg_sort_order`: re-adding it makes a new join row with `null`. Reorder
  by writing `sg_sort_order`, never by rewriting the member list.

- The stock read-only fields are `created_at`, `created_by`, `external_share_count`, `id`,
  `image_blur_hash`, `image_source_entity`, `locked_at`, `locked_by`,
  `media_center_viewed_by_current_user_at`, `open_notes`, `open_notes_count`, `updated_at`, `updated_by`.

- They 400 with two different messages: `API update() Playlist.id is read only.` and
  `API update() Playlist.created_at is editable on create only.`

`corpus/findings/entity_types/Playlist.md`

## Project

Project is site-wide and has no `project` field, so a scoping filter 400s on it; `name` is the identity, the only field both mandatory and unique, and `code` is a second unique text field.

- `is_template`, `is_demo` and `is_template_project` are read only over REST, so the flags a picker filters
  on cannot be set by a script user. `archived` is editable.

- `start_date`, `end_date` and `duration` are read only and derived. On the probed site all three are null on
  every project read, so do not filter or sort a project listing on them.

- `landing_page_url` is a path, not a URL: `"/detail/Project/N?legacy=true"`. Prefix the site URL yourself.

- On the probed site `GET /schema/Project/fields` returns 42 fields, 15 of them not editable
  (`created_at`, `created_by`, `duration`, `end_date`, `id`, `image_blur_hash`, `image_source_entity`,
  `is_demo`, `is_template`, `is_template_project`, `landing_page_url`, `layout_project`, `start_date`,
  `updated_at`, `updated_by`). The count is site configuration; the names are stock.

`corpus/findings/entity_types/Project.md`

## PublishedFile

Only `project` is required to create a PublishedFile, and nothing is unique: the same name, version_number and path publish twice at 201, so read the last version before writing the next.

- `path_cache` stays `null` after a REST create even when `path` resolved to a local storage, while
  `path_cache_storage` is set from that resolution. A filter on `path_cache` misses every row published
  through the REST API and matches only what a publishing client wrote by hand.

- A `local` path has no `url` key, so `value["url"]` raises on exactly the shape a publish uses. Read
  `link_type` first (`field_types/url`).

- There is no `notes` or `open_notes` field. A comment about a publish lives on its `version` or its
  `task`, never on the PublishedFile.

- Not editable on the probed site: `id`, `created_at`, `created_by`, `updated_at`, `updated_by`,
  `image_blur_hash`, `image_source_entity`. Everything else, `path_cache` included, takes a write.

`corpus/findings/entity_types/PublishedFile.md`

## PublishedFileType

PublishedFileType is site-wide with no project field, so a publish that creates one on an unknown extension adds it to every project; `code` is the identity and the only unique field.

- The scope is the site. A publish that creates the type on an unknown extension pollutes every project,
  and no filter narrows this endpoint. Gate creation behind an allowlist, or resolve to an existing row.

- `?project_id=N` returns 200 and changes nothing. A client that reads it as scoping will report every
  type on the site as belonging to whichever project it asked about.

- Matching by `code` is case-insensitive on read. Two rows differing only in case are two types to the
  API and one to a filter.

- `PublishedFile.published_file_type` takes a `{type, id}` hash; a bare id is 400. Filter by the dotted
  path `published_file_type.PublishedFileType.code` when the id is not already in hand.

`corpus/findings/entity_types/PublishedFileType.md`

## Reply

Reply is site-wide with no project field, and entity accepts almost every type on the site, not only Note; send entity on create, because a Reply whose entity is null cannot be deleted.

- **A Reply whose `entity` is null cannot be deleted.** `DELETE /entity/replies/<id>` answers 400 code 104
  `Delete failed for [Reply with id=N]: undefined method 'reflect_on_association' for class NilClass`.
  Assign any `entity` with a `PUT` and the same delete answers 204. A create that omitted `entity` is
  therefore permanent litter until it is repaired, so send `entity` in the create body.

- `content` is flagged `mandatory` and an empty body still answers 201, the same inversion probe 012 found
  on Version. The flag is not the contract.

- A filter for a type that is not in `Reply.entity`'s `valid_types` 400s with `API read()
  invalid/missing entity hash string 'type'`, even when live rows point at it. On the probed site the
  oldest replies hang off `Ticket`, a type absent from `/schema`, and the 400's own `Valid entity types`
  list names `Ticket` while the filter is refused.

- `[["entity", "type_is", "Ticket"]]` returns those rows at 200; use `type_is` for a type-level cut and reserve the hash for a type you read out of `valid_types`.

- `entity` is editable after the fact, with no type check against the original. A `PUT` moves a Reply from
  a Note to a Version at 200 and the Note's thread silently loses a row.

`corpus/findings/entity_types/Reply.md`

## Sequence

A Sequence needs `project`, not `code`, and project alone names it `New Sequence <id>`; `shots` is the reverse of `Shot.sg_sequence`, one link, so a Shot sits in exactly one Sequence.

- `code` looks mandatory and is not, and `project` looks optional and is not. `{"project": …}` alone
  returns 201 with `code` set to `New Sequence <id>`, so a client that omits `code` on a retry does not
  fail, it litters. `{"code": …}` alone 400s with `missing 'project' attribute`.

- A Shot belongs to exactly one Sequence. Adding a Shot already linked elsewhere to `Sequence.shots`
  returns 200 and silently empties the first Sequence's `shots`; there is no reparenting error.

- `code` is not unique and no filter makes it so. Two rows in one project answered to the same `code`.
  `cached_display_name` accepts a `PUT` at 200 and stores nothing: it re-reads as `code`.

- `DELETE /entity/sequences/<id>` returns 204 and the row leaves both `GET` and `_search`, but it is a
  retire: `POST /entity/sequences/<id>?revive=true` returns 200 and the id is live again. Without the
  query parameter that same `POST` is 400 `Request Parameters invalid.` with `source: {"revive": ["revive is missing"]}`.

`corpus/findings/entity_types/Sequence.md`

## Shot

A Shot needs only `project` on create, and `code` is flagged mandatory, is optional and is not unique: an omitted one becomes "New Shot <id>" and a re-run duplicates rows. Send `code`, key on `id`.

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

`corpus/findings/entity_types/Shot.md`

## Step

Step is site-wide with no project field, partitioned only by entity_type; list the Steps for a Shot with entity_type is "Shot", and treat neither code nor short_name as unique.

- `entity_type` groups Steps; it does not constrain `Task.step`. On the probed site 6 Tasks hold a Step
  declared for another type: 4 `Level` Steps and 2 `Shot` Steps on Asset Tasks. Check the pair yourself
  before trusting a Step to describe the entity it is attached to.

- `["entity", "type_is_not", "Shot"]` also matches a Task whose `entity` is null. Of 205 apparent
  cross-type Tasks on the probed site, 199 have no `entity` at all. Add `["entity", "is_not", null]`.

- `cached_display_name` is null on every Step on the probed site, though it is `editable: true` and reads
  as an ordinary `text` field. Display `code`.

- `Task.step` takes a `{type, id}` hash. A bare id returns 400 `API summarize() Task.step expected [Hash,
  ActiveSupport::HashWithIndifferentAccess, ... NilClass] data type(s) but got Integer: 2` (probe 012).

`corpus/findings/entity_types/Step.md`

## Task

A Task is named by `content`, never `code`; a create needs only `project`; `start_date`, `due_date` and `duration` are one triple the server recomputes on every write.

- Identity is `content`. `code` and `name` do not exist on Task and both 400, so a generic
  "read the `code`" client fails on this type alone.

- `content` is `mandatory` in the schema and still nullable over REST: `null` and `""` both return 200
  and read back `null`, leaving `cached_display_name` as `"-"`.

- `valid_types` on `entity` does not bind, matching `field_types/entity`. `{"type": "Task", "id": N}`
  was accepted at 200 and read back as a Task.

- Never PUT two of `start_date`, `due_date`, `duration` expecting both to stand: the third is recomputed,
  and on a dependent Task a date write also sets `pinned` and can raise `dependency_violation`.

- `time_logs_sum`, `time_vs_est` and `time_percent_of_est` are read only. Sum `TimeLog.duration` to
  predict them; `Task.color` is not a colour either (`field_types/color`).

`corpus/findings/entity_types/Task.md`

## TaskTemplate

A template's tasks are ordinary Tasks with `task_template` set and `project` null; read them with `["task_template", "is", T]`. Deleting a template retires its tasks.

- **`DELETE /entity/task_templates/<id>` retires the template's tasks.** A template task made for the
  test answered 404 `Task: 47113 not found` after its template was deleted, and the 204 names nothing.

- Filter on `task_template` to read a template, never on `project`: a template task has none, so a
  project-scoped Task query never returns one.

- `task_count` is a string. Compare it with `int()` or count the Tasks.

- `entity_type` does not bind: probe 083 applied an `Asset` template to a Shot and it generated Tasks.

`corpus/findings/entity_types/TaskTemplate.md`

## TimeLog

A TimeLog create requires only `project`; `date` defaults to the server's today instead of failing, `entity` takes any type despite valid_types ['Task'], and a script may log for any HumanUser.

- `date` never fails a create. Omit it and the row gets the server's current date, in the site's timezone,
  not the day the work happened. A backfill that forgets `date` silently lands on today.

- `entity` is not restricted to Task despite `valid_types: ['Task']`. A tool that logs against a Shot gets
  201 and a row no Task rollup will ever count. Check the type client-side.

- `Task.time_logs_sum` is read-only and 400s on a write (`entity_types/Task`). Change the sum by creating,
  editing or deleting a TimeLog.

- `created_by` and `created_at` are `editable on create only`: a `PUT` to either is 400
  `API update() TimeLog.created_by is editable on create only.` `user` stays editable for the row's life.

`corpus/findings/entity_types/TimeLog.md`

## Version

The schema inverts the create contract: `project` is required and `code` is not, generated as "New Version <id>" when omitted. `code` is not unique, so key on `id`.

- The schema's `mandatory` and `editable` flags are not the contract. `project` is required and unflagged,
  `code` is flagged and generated, and `image` reads `editable: true` while refusing every write
  (`field_types/image`).

- The 201 `relationships` block lists all 20 link slots, including ones never set, so its keys are not a
  record of the input (probe 012). Read the row back to confirm a link.

- Not editable on the probed site: `id`, `created_at`, `created_by`, `updated_at`, `updated_by`,
  `image_blur_hash`, `image_source_entity`, `open_notes`, `open_notes_count`, `otio_playable`,
  `viewed_by_current_user_at`, and one `pivot_column` (`field_types/pivot_column`).

- There is no `attachments` field. A file uploaded with no field in the path is found through
  `Attachment.attachment_links`, never from the Version (probe 014).

- **`user` is the Artist field and defaults to the caller**, so a script's Versions are authored by
  the script: 106 of 200 recent rows had `user` equal to their own `created_by` ApiUser. It is
  editable, unlike `created_by`:

  | create | `created_by` | `user` (Artist) |
  |---|---|---|
  | script, `user` not sent | the ApiUser | the ApiUser |
  | script, `user` sent | the ApiUser | the HumanUser sent |
  | `scope=sudo_as_login:<login>` (probe 027) | the HumanUser | the HumanUser |

  A tool publishing for someone wants one of the last two. Sending `user` needs no impersonation
  permission; the scope also fixes `created_by`.

`corpus/findings/entity_types/Version.md`
