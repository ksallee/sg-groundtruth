# Endpoints — Records, PUT

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `PUT /entity/<type>/<id>`

Updates and returns the whole record, 77 attribute keys for a Shot. A key left out of the body is unchanged rather than cleared, and an empty body is a 200 no-op.

| you send | result |
|---|---|
| `{"description": "x"}` | set |
| a body omitting `description` | unchanged, not cleared |
| `{}` | 200, nothing happens |
| `null` for a clearable field | cleared |

- There is no PATCH. `PUT` here is already a partial update, which is the opposite of what the verb
  usually means: it does not replace the record with the body.

- Clearing is per data type, not universal. `""` on a text field stores `null`; `null` on a `color`
  field is refused outright; a bare list on a `multi_entity` replaces every link.

**Measured by**

- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `060_entity_dict_name` (findings) — The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.  
  rules: `doors/findings-read`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
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
- `084_task_template_reapply` (findings) — Changing `task_template` to T creates a Task per T task no Task links by `template_task`, duplicating a same-name hand-made one, and re-syncs the linked Tasks' fields and edges (probe 102).  
  rules: `doors/findings-write`
- `085_task_dependency_types` (findings) — TaskDependency takes four `dependency_type` values, default `finish-to-start-next-day`; `offset_days` counts working days and snaps the dependent both ways. `shift_ratio` moved nothing.  
  rules: `doors/findings-write`
- `087_dependency_cascade` (findings) — An upstream date write reschedules every unpinned downstream Task, later and earlier alike; a null one moves none (097). A pinned Task stays put and flags `dependency_violation` while broken.  
  rules: `doors/findings-write`
- `089_task_delete_side_effects` (findings) — Deleting a Task retires its TaskDependency rows, unlinks both neighbours without bridging them, and nulls `Version.sg_task` and `PublishedFile.task`. Revive restores all of it.  
  rules: `doors/findings-write`
- `092_dependency_edge_reschedule` (findings) — A new edge reschedules an unpinned downstream Task at once, whether POSTed or copied by a template apply on claim. A pinned one keeps its dates and flags `dependency_violation`.  
  rules: `doors/findings-write`
- `093_clear_dates_pin` (findings) — On a dependent Task a start_date write pins it, null or real; a due_date write never does, null or real. A pinned null Task holds; PUT pinned:false refills both dates.  
  rules: `doors/findings-write`
- `094_permission_preflight` (findings) — Ask with a write that cannot land: a no-op PUT per field (update), a POST with a bad status (create), a _batch of [delete, 404 sentinel] (delete). Permission is checked first, and nothing is written.  
  rules: `doors/findings-write`
- `095_dependency_remove_undo` (findings) — Remove an edge with `DELETE` on its TaskDependency row: revive restores its type and offset. A `remove` on `upstream_tasks` or `downstream_tasks` erases the row for good.  
  rules: `doors/findings-write`
- `096_task_template_unmerge` (findings) — A template write re-syncs every Task linked to it: fields but status reset, edges rewired. Undo: old template_task per Task first, then old task_template, then delete what B made.  
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
- `104_template_unmerge_in_one_batch` (findings) — Recipe 019's undo fits one `_batch` with the same end state, if the batch skips edges its own task_template write removes: deleting one 404s and rolls back all. Undo to null deletes them.  
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
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `067_notes_in_the_stream` (findings) — A Reply reaches every linked stream in 33 s as `create_reply`, creates too; a script's Note create and status changes were absent after 430 s. Write as a person.  
  rules: `doors/findings-observe`
- `090_template_task_events` (findings) — A template-generated Task logs like a hand-made one plus a `template_task` change row, `in_create` true, credited to the caller. Filter `attribute_name` `template_task` to find them.  
  rules: `doors/findings-observe`
- `004_register_published_file` (recipes) — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform  
  rules: `doors/recipes`
- `006_media_round_trip` (recipes) — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  rules: `doors/recipes`
- `008_delivery_progress` (recipes) — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  rules: `doors/recipes`
- `009_multi_entity_safely` (recipes) — Add to and remove from a multi_entity field without destroying the links you did not mean to touch  
  rules: `doors/recipes`
- `015_apply_task_template_without_duplicates` (recipes) — Apply a task template to an entity that already has Tasks, without duplicating the ones it already holds  
  rules: `doors/recipes`
- `017_check_permission_before_writing` (recipes) — Learn whether the signed-in person may update, create or delete a type before writing, with calls that change nothing  
  rules: `doors/recipes`
- `019_undo_task_template_merge` (recipes) — Undo a task template merge, returning an entity's Tasks, fields and dependencies to their state before it  
  rules: `doors/recipes`
- `004_update_mode_ignored_in_query_string` (reports) — multi_entity_update_mode sent as a query parameter is accepted and ignored, and the whole link set is replaced when the caller asked to add.  
  rules: `doors/reports`
- `005_writing_replies_deletes_rows` (reports) — A write to Note.replies deletes the Reply rows rather than unlinking them, so PUT with an empty list destroys a thread at 200.  
  rules: `doors/reports`

**Silent on this call**

- `put_entity_type_id` — Updates and returns the whole record, 77 attribute keys for a Shot. A key left out of the body is unchanged rather than cleared, and an empty body is a 200 no-op.
- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `068_note_read_state` — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.
- `024_read_after_write` — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
- `058_local_storage_roots` — One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
- `067_notes_in_the_stream` — A Reply reaches every linked stream in 33 s as `create_reply`, creates too; a script's Note create and status changes were absent after 430 s. Write as a person.
- `009_multi_entity_safely` — Add to and remove from a multi_entity field without destroying the links you did not mean to touch

`corpus/endpoints/put_entity_type_id.md`

## `PUT /entity/projects/<id>/_update_last_accessed`

Stamps one user's last visit to a project. Write-only: a `user_id` that does not exist answers the same 200, and nothing readable over REST changes.

| you send | result |
|---|---|
| `{"user_id": 3}` | 200 |
| `{"user_id": "3"}` | 200, the string is accepted |
| `{"user_id": 999999999}` | 200, no error |
| `{}` | 400 `user_id is missing` |
| the path under `shots` | 404, `detail` null |

- `Project.last_accessed_by_current_user` is relative to the requesting account, and a script has no
  HumanUser row to be current, so a script reads `null` before and after its own call. It is not
  unreadable: a token acting as the stamped user reads the timestamp back. Measured on the probed
  site, a script `PUT` with `{"user_id": 24}` then read `null` as itself and
  `'2026-09-08T16:00:59Z'` through `scope=sudo_as_login:<that user>` (probe 027). The write logged no
  `EventLogEntry`. Fire and forget only if you have no way to be the user you stamped.

- A bad `user_id` is a silent 200. Validate the id against `GET /entity/human_users` first if it
  matters that the stamp landed.

- `GET` on the same path falls through to the file-field route, so the 404 names a field nobody asked
  for. The endpoint is `PUT` only.

**Measured by**

- `048_one_record_beyond_crud` (findings) — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.  
  rules: `doors/findings-read`

**Silent on this call**

- `put_entity_projects_id_update_last_accessed` — Stamps one user's last visit to a project. Write-only: a `user_id` that does not exist answers the same 200, and nothing readable over REST changes.
- `048_one_record_beyond_crud` — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.

`corpus/endpoints/put_entity_projects_id_update_last_accessed.md`
