# Endpoints — Records, DELETE

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `DELETE /entity/<type>/<id>`

Retires a row at 204 with an empty body. It is not erased: the row reads 404 normally and 200 under `options[return_only]=retired`, and a second delete is 404.

- Retired, not erased. Anything counting rows has to decide which of those two it means, and the default
  for every read is live-only.

- The correct spelling is `options[return_only]=retired`. `options[retired_only]=true` is accepted at
  200 and silently ignored, which reads as "there are no retired rows".

- A second delete is 404, so delete is not idempotent in its status code even though it is in its effect.

**Measured by**

- `060_entity_dict_name` (findings) — The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.  
  rules: `doors/findings-read`
- `024_read_after_write` (findings) — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.  
  rules: `doors/findings-write`
- `078_page_setting_write` (findings) — A script cannot create a Page (HumanUser expected), a person can. settings_json writes only as a JSON string, reads back identical. DELETE on a PageSetting is 400: every created row is permanent.  
  rules: `doors/findings-write`
- `084_task_template_reapply` (findings) — Changing `task_template` to T creates a Task per T task no Task links by `template_task`, duplicating a same-name hand-made one, and re-syncs the linked Tasks' fields and edges (probe 102).  
  rules: `doors/findings-write`
- `089_task_delete_side_effects` (findings) — Deleting a Task retires its TaskDependency rows, unlinks both neighbours without bridging them, and nulls `Version.sg_task` and `PublishedFile.task`. Revive restores all of it.  
  rules: `doors/findings-write`
- `094_permission_preflight` (findings) — Ask with a write that cannot land: a no-op PUT per field (update), a POST with a bad status (create), a _batch of [delete, 404 sentinel] (delete). Permission is checked first, and nothing is written.  
  rules: `doors/findings-write`
- `095_dependency_remove_undo` (findings) — Remove an edge with `DELETE` on its TaskDependency row: revive restores its type and offset. A `remove` on `upstream_tasks` or `downstream_tasks` erases the row for good.  
  rules: `doors/findings-write`
- `096_task_template_unmerge` (findings) — A template write re-syncs every Task linked to it: fields but status reset, edges rewired. Undo: old template_task per Task first, then old task_template, then delete what B made.  
  rules: `doors/findings-write`
- `098_template_merge_in_one_batch` (findings) — Recipe 015's merge fits one `_batch`: requests run in order, so a `task_template` write sees claims made earlier in the batch, and `null` then `T` on the same Shot re-runs the apply.  
  rules: `doors/findings-write`
- `101_template_edge_conflict` (findings) — On a claimed pair, a template apply replaces an existing edge of another type, or the reverse edge, with the template's edge: the old row is erased, not retired, and the PUT is a plain 200.  
  rules: `doors/findings-write`
- `102_task_template_resync` (findings) — Writing task_template T re-syncs every Task linked to T: T's non-empty values overwrite, status kept, dates and assignees kept or filled if empty; edges between linked Tasks reset to T's.  
  rules: `doors/findings-write`
- `103_batch_delete_revive` (findings) — A `delete` inside `_batch` retires a Task or TaskDependency exactly as `DELETE` does: same retired read-back, and revive returns the same id, fields, edges and `Version.sg_task`.  
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
- `110_template_task_after_revive` (findings) — Revive restores `template_task`. A task_template write while the Task is retired re-creates it, so a later revive leaves two Tasks on one template task. Revive first, then write.  
  rules: `doors/findings-write`
- `111_template_undo_outside_edge` (findings) — An undo's write back to template A erases every edge whose downstream Task is A-linked and that A lacks, pre-merge edges included; recipe 022 DELETEs one such edge, 404s and rolls back.  
  rules: `doors/findings-write`
- `112_template_unmerge_linked_twice` (findings) — Undo relinking two Tasks to one template task: A wires either one (11 of 14 picked the loser), nothing is made. Relink the loser after the task_template write: then it matches the one-link undo.  
  rules: `doors/findings-write`
- `025_event_log` (findings) — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  rules: `doors/findings-observe`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `013_publish_file_bytes` (recipes) — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under  
  rules: `doors/recipes`
- `018_remove_and_restore_a_dependency` (recipes) — Remove one dependency between two Tasks and put it back on undo, with its type and offset  
  rules: `doors/recipes`
- `019_undo_task_template_merge` (recipes) — Undo a task template merge, returning an entity's Tasks, fields and dependencies to their state before it  
  rules: `doors/recipes`

**Silent on this call**

- `024_read_after_write` — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
- `025_event_log` — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.

`corpus/endpoints/delete_entity_type_id.md`
