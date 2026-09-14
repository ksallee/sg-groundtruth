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
- `024_read_after_write` (findings) — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.  
  rules: `doors/findings-write`
- `058_local_storage_roots` (findings) — One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.  
  rules: `doors/findings-write`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `004_register_published_file` (recipes) — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform  
  rules: `doors/recipes`
- `006_media_round_trip` (recipes) — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  rules: `doors/recipes`
- `008_delivery_progress` (recipes) — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  rules: `doors/recipes`
- `009_multi_entity_safely` (recipes) — Add to and remove from a multi_entity field without destroying the links you did not mean to touch  
  rules: `doors/recipes`
- `004_update_mode_ignored_in_query_string` (reports) — multi_entity_update_mode sent as a query parameter is accepted and ignored, and the whole link set is replaced when the caller asked to add.  
  rules: `doors/reports`
- `005_writing_replies_deletes_rows` (reports) — A write to Note.replies deletes the Reply rows rather than unlinking them, so PUT with an empty list destroys a thread at 200.  
  rules: `doors/reports`

**Silent on this call**

- `put_entity_type_id` — Updates and returns the whole record, 77 attribute keys for a Shot. A key left out of the body is unchanged rather than cleared, and an empty body is a 200 no-op.
- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `024_read_after_write` — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
- `058_local_storage_roots` — One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
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
