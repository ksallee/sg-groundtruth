# Endpoints — Records, POST

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `POST /entity/<type>`

`project` is the requirement on every project-scoped type and the identity field is not, whatever the schema says. `?fields` is ignored, and the 201 returns the whole record.

- Omitting the identity field is not an error: the server writes `New Shot <id>` and returns 201.
  Nothing is unique, so a re-run of an ingest doubles the rows rather than failing.

- `?fields=code` returns 10 attribute keys, not one. Every write ignores it, so re-read the row when you
  need a dotted path or a narrowed set.

- An unknown field **is** a 400 here, unlike an unknown `fields` name on a read, which is dropped at
  200. Writes are loud about names; reads are silent.

- `created_at` comes back as `2026-09-04 03:51:48 UTC`, space separated, where a read returns
  `2026-09-04T03:51:48Z`. The same instant in two formats depending on the call.

**Measured by**

- `060_entity_dict_name` (findings) — The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.  
  rules: `doors/findings-read`
- `011_create_project` (findings) — A script user can create a Project with nothing but {"name": ...}, at 201, but the response echoes only 6 attributes, so read the project back if you need anything else.  
  rules: `doors/findings-write`
- `012_create_version` (findings) — The schema's mandatory flags are not the create contract: on every project-scoped type measured, `project` is required and the identity field is optional, server-generated and not unique.  
  rules: `doors/findings-write`
- `024_read_after_write` (findings) — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.  
  rules: `doors/findings-write`
- `058_local_storage_roots` (findings) — One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.  
  rules: `doors/findings-write`
- `069_client_note` (findings) — `client_note` cannot be set over REST: `true` on create is 400 and any `PUT` is 400 `editable on create only`. `sg_note_type: "Client"` is the one marker a caller can write.  
  rules: `doors/findings-write`
- `070_authored_timestamps` (findings) — A create body sets created_at and updated_at and they read back exactly, on Note, Task and Version, though the schema flags both editable false; every PUT on either 400s.  
  rules: `doors/findings-write`
- `078_page_setting_write` (findings) — A script cannot create a Page (HumanUser expected), a person can. settings_json writes only as a JSON string, reads back identical. DELETE on a PageSetting is 400: every created row is permanent.  
  rules: `doors/findings-write`
- `083_task_template_on_create` (findings) — A create with `task_template` makes the Tasks inside the same call, by `POST` and by `_batch`, copying every field set on the template tasks and their dependency types and offsets.  
  rules: `doors/findings-write`
- `084_task_template_reapply` (findings) — Changing `task_template` to T creates a Task per T task no Task links by `template_task`, duplicating a same-name hand-made one, and re-syncs the linked Tasks' fields and edges (probe 102).  
  rules: `doors/findings-write`
- `085_task_dependency_types` (findings) — TaskDependency takes four `dependency_type` values, default `finish-to-start-next-day`; `offset_days` counts working days and snaps the dependent both ways. `shift_ratio` moved nothing.  
  rules: `doors/findings-write`
- `086_batch_tasks_with_dependencies` (findings) — Tasks and their dependencies take two `_batch` calls: create the Tasks, then create TaskDependency rows. `upstream_tasks` on a create links without rescheduling.  
  rules: `doors/findings-write`
- `087_dependency_cascade` (findings) — An upstream date write reschedules every unpinned downstream Task, later and earlier alike; a null one moves none (097). A pinned Task stays put and flags `dependency_violation` while broken.  
  rules: `doors/findings-write`
- `092_dependency_edge_reschedule` (findings) — A new edge reschedules an unpinned downstream Task at once, whether POSTed or copied by a template apply on claim. A pinned one keeps its dates and flags `dependency_violation`.  
  rules: `doors/findings-write`
- `093_clear_dates_pin` (findings) — On a dependent Task a start_date write pins it, null or real; a due_date write never does, null or real. A pinned null Task holds; PUT pinned:false refills both dates.  
  rules: `doors/findings-write`
- `094_permission_preflight` (findings) — Ask with a write that cannot land: a no-op PUT per field (update), a POST with a bad status (create), a _batch of [delete, 404 sentinel] (delete). Permission is checked first, and nothing is written.  
  rules: `doors/findings-write`
- `095_dependency_remove_undo` (findings) — Remove an edge with `DELETE` on its TaskDependency row: revive restores its type and offset. A `remove` on `upstream_tasks` or `downstream_tasks` erases the row for good.  
  rules: `doors/findings-write`
- `097_null_dates_unpin` (findings) — A Task with no upstream never pins, on a null or a real date write; nulling its dates leaves its downstream unmoved, and pinned:false refills nothing.  
  rules: `doors/findings-write`
- `098_template_merge_in_one_batch` (findings) — Recipe 015's merge fits one `_batch`: requests run in order, so a `task_template` write sees claims made earlier in the batch, and `null` then `T` on the same Shot re-runs the apply.  
  rules: `doors/findings-write`
- `099_template_apply_edge_copy_kept` (findings) — A template apply copies a missing edge between two Tasks whose `template_task` already match it, whether either was claimed, kept, or created by that same call.  
  rules: `doors/findings-write`
- `100_duration_write_pin` (findings) — Writing duration on a dependent Task does not pin it; a start_date write in the same run does. It keeps following the upstream, and a duration write upstream moves it.  
  rules: `doors/findings-write`
- `101_template_edge_conflict` (findings) — On a claimed pair, a template apply replaces an existing edge of another type, or the reverse edge, with the template's edge: the old row is erased, not retired, and the PUT is a plain 200.  
  rules: `doors/findings-write`
- `102_task_template_resync` (findings) — Writing task_template T re-syncs every Task linked to T: T's non-empty values overwrite, status kept, dates and assignees kept or filled if empty; edges between linked Tasks reset to T's.  
  rules: `doors/findings-write`
- `105_offset_days_null_vs_zero` (findings) — TaskDependency `offset_days` null and 0 are stored and compared as different: a template apply deletes an entity edge with null against a template 0 (or the reverse) and re-creates it with a new id.  
  rules: `doors/findings-write`
- `106_template_task_linked_twice` (findings) — With two Tasks linked to one template task, an apply re-syncs and wires only one of them, picked unpredictably (not by id, age or edges); the other is left as is. No error, nothing duplicated.  
  rules: `doors/findings-write`
- `107_dependency_three_task_loop` (findings) — A three-Task loop is a 400 on a direct create and inside `_batch`, which rolls back whole. A template apply deletes a claimed Task's upstream edge from a Task outside the template, loop or not.  
  rules: `doors/findings-write`
- `108_task_template_resync_empties` (findings) — Re-sync to T: a numeric 0 on T's task overwrites (est, duration); milestone false and "" (stored null) keep the Task's value; a Task with only start or only due keeps its null duration.  
  rules: `doors/findings-write`
- `109_template_apply_outside_edge` (findings) — A template apply erases an edge where a linked Task depends on a Task not linked to the template (root or not, other template, other Shot); it kept the edge with the outside Task downstream.  
  rules: `doors/findings-write`
- `025_event_log` (findings) — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  rules: `doors/findings-observe`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `067_notes_in_the_stream` (findings) — A Reply reaches every linked stream in 33 s as `create_reply`, creates too; a script's Note create and status changes were absent after 430 s. Write as a person.  
  rules: `doors/findings-observe`
- `090_template_task_events` (findings) — A template-generated Task logs like a hand-made one plus a `template_task` change row, `in_create` true, credited to the caller. Filter `attribute_name` `template_task` to find them.  
  rules: `doors/findings-observe`
- `001_publish_version_with_media` (recipes) — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  rules: `doors/recipes`
- `004_register_published_file` (recipes) — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform  
  rules: `doors/recipes`
- `007_build_and_reconcile_a_cut` (recipes) — Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there  
  rules: `doors/recipes`
- `008_delivery_progress` (recipes) — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  rules: `doors/recipes`
- `013_publish_file_bytes` (recipes) — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under  
  rules: `doors/recipes`
- `017_check_permission_before_writing` (recipes) — Learn whether the signed-in person may update, create or delete a type before writing, with calls that change nothing  
  rules: `doors/recipes`

**Silent on this call**

- `post_entity_type` — `project` is the requirement on every project-scoped type and the identity field is not, whatever the schema says. `?fields` is ignored, and the 201 returns the whole record.
- `024_read_after_write` — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
- `058_local_storage_roots` — One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.
- `086_batch_tasks_with_dependencies` — Tasks and their dependencies take two `_batch` calls: create the Tasks, then create TaskDependency rows. `upstream_tasks` on a create links without rescheduling.
- `025_event_log` — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
- `067_notes_in_the_stream` — A Reply reaches every linked stream in 33 s as `create_reply`, creates too; a script's Note create and status changes were absent after 430 s. Write as a person.

`corpus/endpoints/post_entity_type.md`

## `POST /entity/<type>/<id>`

Revives a retired row. `?revive=1` is required and any JSON body is discarded, so this is not an update via POST.

| you send | result |
|---|---|
| `?revive=1`, `?revive=true`, `?revive=yes` | revived |
| `?revive=0`, `?revive=false` | 400 `revive must be true` |
| no `revive` parameter | 400 `revive is missing` |
| a body of field values | 200, the fields are not applied |
| `?fields=code` | 200, no `attributes` returned either way |

- The response has no `attributes` key at all, which is thinner than any other write returns. Re-read
  the id to see the record.

- Field values survive the retire and come back with the revive. Nothing is reset.

- `did_revive: false` at 200 is the only signal that the row was already live. Read `meta`, not the
  status code.

**Measured by**

- `048_one_record_beyond_crud` (findings) — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.  
  rules: `doors/findings-read`
- `089_task_delete_side_effects` (findings) — Deleting a Task retires its TaskDependency rows, unlinks both neighbours without bridging them, and nulls `Version.sg_task` and `PublishedFile.task`. Revive restores all of it.  
  rules: `doors/findings-write`
- `095_dependency_remove_undo` (findings) — Remove an edge with `DELETE` on its TaskDependency row: revive restores its type and offset. A `remove` on `upstream_tasks` or `downstream_tasks` erases the row for good.  
  rules: `doors/findings-write`
- `103_batch_delete_revive` (findings) — A `delete` inside `_batch` retires a Task or TaskDependency exactly as `DELETE` does: same retired read-back, and revive returns the same id, fields, edges and `Version.sg_task`.  
  rules: `doors/findings-write`
- `018_remove_and_restore_a_dependency` (recipes) — Remove one dependency between two Tasks and put it back on undo, with its type and offset  
  rules: `doors/recipes`
- `021_undo_a_batch_delete` (recipes) — Delete Tasks or dependencies in one batch and undo it by reviving the same rows  
  rules: `doors/recipes`

**Silent on this call**

- `048_one_record_beyond_crud` — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.

`corpus/endpoints/post_entity_type_id.md`

## `POST /entity/_batch`

The key is `requests`, not `data`, and sending `data` is 400 `requests is missing`. It answers 200 rather than 201, and one bad request rolls the whole batch back.

- **It is atomic.** The Shot the first request would have created does not exist after the 404.

- The response nesting is the trap that outlives a run. Reading `row["id"]` instead of
  `row["data"]["id"]` yields `None`, so cleanup silently skips the rows and they stay on the site.

- A returned id does not by itself prove the row exists. Read back after a batch that matters.

- The request key and the response key differ by name. `requests` in, `data` out.

**Measured by**

- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `024_read_after_write` (findings) — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.  
  rules: `doors/findings-write`
- `083_task_template_on_create` (findings) — A create with `task_template` makes the Tasks inside the same call, by `POST` and by `_batch`, copying every field set on the template tasks and their dependency types and offsets.  
  rules: `doors/findings-write`
- `084_task_template_reapply` (findings) — Changing `task_template` to T creates a Task per T task no Task links by `template_task`, duplicating a same-name hand-made one, and re-syncs the linked Tasks' fields and edges (probe 102).  
  rules: `doors/findings-write`
- `086_batch_tasks_with_dependencies` (findings) — Tasks and their dependencies take two `_batch` calls: create the Tasks, then create TaskDependency rows. `upstream_tasks` on a create links without rescheduling.  
  rules: `doors/findings-write`
- `092_dependency_edge_reschedule` (findings) — A new edge reschedules an unpinned downstream Task at once, whether POSTed or copied by a template apply on claim. A pinned one keeps its dates and flags `dependency_violation`.  
  rules: `doors/findings-write`
- `094_permission_preflight` (findings) — Ask with a write that cannot land: a no-op PUT per field (update), a POST with a bad status (create), a _batch of [delete, 404 sentinel] (delete). Permission is checked first, and nothing is written.  
  rules: `doors/findings-write`
- `098_template_merge_in_one_batch` (findings) — Recipe 015's merge fits one `_batch`: requests run in order, so a `task_template` write sees claims made earlier in the batch, and `null` then `T` on the same Shot re-runs the apply.  
  rules: `doors/findings-write`
- `099_template_apply_edge_copy_kept` (findings) — A template apply copies a missing edge between two Tasks whose `template_task` already match it, whether either was claimed, kept, or created by that same call.  
  rules: `doors/findings-write`
- `101_template_edge_conflict` (findings) — On a claimed pair, a template apply replaces an existing edge of another type, or the reverse edge, with the template's edge: the old row is erased, not retired, and the PUT is a plain 200.  
  rules: `doors/findings-write`
- `103_batch_delete_revive` (findings) — A `delete` inside `_batch` retires a Task or TaskDependency exactly as `DELETE` does: same retired read-back, and revive returns the same id, fields, edges and `Version.sg_task`.  
  rules: `doors/findings-write`
- `104_template_unmerge_in_one_batch` (findings) — Recipe 019's undo fits one `_batch` with the same end state, if the batch skips edges its own task_template write removes: deleting one 404s and rolls back all. Undo to null deletes them.  
  rules: `doors/findings-write`
- `107_dependency_three_task_loop` (findings) — A three-Task loop is a 400 on a direct create and inside `_batch`, which rolls back whole. A template apply deletes a claimed Task's upstream edge from a Task outside the template, loop or not.  
  rules: `doors/findings-write`
- `109_template_apply_outside_edge` (findings) — A template apply erases an edge where a linked Task depends on a Task not linked to the template (root or not, other template, other Shot); it kept the edge with the outside Task downstream.  
  rules: `doors/findings-write`
- `002_batch` (recipes) — Apply many creates, updates and deletes in one atomic call, and match the results back to the requests  
  rules: `doors/recipes`
- `005_propagate_status` (recipes) — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write  
  rules: `doors/recipes`
- `007_build_and_reconcile_a_cut` (recipes) — Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there  
  rules: `doors/recipes`
- `015_apply_task_template_without_duplicates` (recipes) — Apply a task template to an entity that already has Tasks, without duplicating the ones it already holds  
  rules: `doors/recipes`
- `016_create_tasks_with_dependencies` (recipes) — Create a set of Tasks and the dependencies between them, with types and offsets, in two calls  
  rules: `doors/recipes`
- `017_check_permission_before_writing` (recipes) — Learn whether the signed-in person may update, create or delete a type before writing, with calls that change nothing  
  rules: `doors/recipes`
- `020_apply_task_template_in_one_batch` (recipes) — Apply a task template to an entity that already has Tasks, without duplicates, in one atomic call  
  rules: `doors/recipes`
- `021_undo_a_batch_delete` (recipes) — Delete Tasks or dependencies in one batch and undo it by reviving the same rows  
  rules: `doors/recipes`
- `022_undo_task_template_merge_in_one_batch` (recipes) — Undo a task template merge in one atomic call, returning Tasks, fields and dependencies to their state before it  
  rules: `doors/recipes`
- `001_batch_create_skips_validation` (reports) — A create inside POST /entity/_batch skips the required-attribute validation the single-create path applies, and answers 200 with the id of a row no read can reach.  
  rules: `doors/reports`

**Silent on this call**

- `post_entity_batch` — The key is `requests`, not `data`, and sending `data` is 400 `requests is missing`. It answers 200 rather than 201, and one bad request rolls the whole batch back.
- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `024_read_after_write` — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
- `086_batch_tasks_with_dependencies` — Tasks and their dependencies take two `_batch` calls: create the Tasks, then create TaskDependency rows. `upstream_tasks` on a create links without rescheduling.
- `002_batch` — Apply many creates, updates and deletes in one atomic call, and match the results back to the requests
- `005_propagate_status` — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write

`corpus/endpoints/post_entity_batch.md`
