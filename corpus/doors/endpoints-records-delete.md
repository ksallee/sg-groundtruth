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
- `084_task_template_reapply` (findings) — Changing `task_template` on a Shot only adds: one Task per template task not yet linked by `template_task`. Nothing is removed or merged; a hand-made Task of the same content and step is duplicated.  
  rules: `doors/findings-write`
- `089_task_delete_side_effects` (findings) — Deleting a Task retires its TaskDependency rows, unlinks both neighbours without bridging them, and nulls `Version.sg_task` and `PublishedFile.task`. Revive restores all of it.  
  rules: `doors/findings-write`
- `025_event_log` (findings) — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  rules: `doors/findings-observe`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `013_publish_file_bytes` (recipes) — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under  
  rules: `doors/recipes`

**Silent on this call**

- `024_read_after_write` — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
- `025_event_log` — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.

`corpus/endpoints/delete_entity_type_id.md`
