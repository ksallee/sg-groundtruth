# Endpoints — Schema, GET

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /schema`

The enabled type list, and the enablement test for a `CustomEntityNN`: a slot absent here 404s everywhere. 12KB, so fetch it once and never loop it into `/fields`.

- `name.value` is the display name and is what a person recognises. `CustomEntity19` is what the URL
  takes. Read the first, address by the second, and never hardcode a slot number: they are
  non-contiguous and site-specific.

- The value is a property object, not a string. `data["Version"]["name"]["value"]` is two levels deeper
  than it looks.

- Presence here is the enablement test. A slot absent from this listing 404s everywhere else.

- 106 types here against 71 fields on one of them. This call is cheap and `/fields` is not, so take the
  list from here and fetch fields only for the types you need.

**Measured by**

- `062_cors` (findings) — Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those.  
  rules: `doors/findings-protocol`
- `002_schema` (findings) — Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.  
  rules: `doors/findings-schema`
- `008_custom_entities` (findings) — Presence in /schema is the enablement test for a custom entity: a slot absent from the listing 404s. Slot numbers are non-contiguous and site-specific, so read name.value and never hardcode one.  
  rules: `doors/findings-schema`
- `115_field_visibility_per_project` (findings) — `visible` is per project. Read it with `?project_id=N`; write it with PUT and `project_id` in the body or the query, never without one. A new field is visible in every project.  
  rules: `doors/findings-schema`
- `122_onset_entity_types` (findings) — Slate, Camera, MocapTake, ShootDay and Scene create like Version: `project` required, `code` generated. None has `attachments`, and only Version.entity and Note.note_links reach them all.  
  rules: `doors/findings-schema`
- `074_page_filter_coverage` (findings) — Every stored page filter with its tokens filled converts and runs 200 but one, yet recipe 003 kept unticked leaves (active "false"): 11 trees returned the wrong count. Drop them.  
  rules: `doors/findings-filter`

`corpus/endpoints/get_schema.md`

## `GET /schema/<Type>`

One type's display name without its 48KB of fields, and the cheapest existence check there is: an unknown or unenabled type is 404 `Entity type 'X' does not exist.`

- The two 404s are byte-identical apart from the name, so this call cannot tell "your site has not
  enabled that slot" from "you invented a type". Both mean the same to a caller: do not address it.

- 138 bytes against 47958 for the same type's `/fields`. Checking existence here rather than there is
  the difference between one call and a page of them.

**Measured by**

- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `002_schema` (findings) — Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.  
  rules: `doors/findings-schema`
- `122_onset_entity_types` (findings) — Slate, Camera, MocapTake, ShootDay and Scene create like Version: `project` required, `code` generated. None has `attachments`, and only Version.entity and Note.note_links reach them all.  
  rules: `doors/findings-schema`

**Silent on this call**

- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.

`corpus/endpoints/get_schema_type.md`

## `GET /schema/<Type>/fields`

Every field on one type with its `data_type`, `editable` and `mandatory`. The expensive call at 48KB and ~330ms, so fetch the types you need and never loop the `/schema` listing into it.

- `mandatory` is not the create contract. `code` reads `mandatory: true` and a create omitting it
  succeeds at 201 with a server-invented name; `project` reads `mandatory: false` and a create omitting
  it is 400. Read the create contract from the entity-type card, not from this flag.

- Every value is wrapped in `{value, editable}`, and the outer `editable` says whether you may change
  the property, not whether you may write the field. `data["code"]["editable"]["value"]` is the one that
  answers "can I write this".

- Adding `project_id` changes two things: `hidden_values` on list and status fields, and `visible.value`
  on every field the project hides. On the probed site Version differs by 22 bytes and no `visible`,
  while Shot reads 12 fields hidden in one project and 15 in another, none at site scope (probe 115).

- A `project_id` that does not exist is a 200 with every field visible, not an error.

- 48KB and about 330ms per type. Never loop this over the `/schema` listing.

**Measured by**

- `002_schema` (findings) — Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.  
  rules: `doors/findings-schema`
- `019_create_fields` (findings) — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.  
  rules: `doors/findings-schema`
- `056_stock_vs_custom_field` (findings) — A field with `visible.editable` false is stock and safe to depend on; true means the site can hide it, which is every custom field and a few stock ones. The `sg_` prefix decides nothing.  
  rules: `doors/findings-schema`
- `061_shipped_statuses` (findings) — Nothing in the schema marks a shipped Status. `system` is true on a minority of them; the stock set is `created_by is null`, plus `options[return_only]=retired` for the rows a site retired.  
  rules: `doors/findings-schema`
- `114_schema_admin_recheck` (findings) — On 2026-11-10 /spec.json names calls to enable, disable and configure a custom entity, all 400 code 111 on the probed site. No call deletes a trashed field forever or writes hidden_values.  
  rules: `doors/findings-schema`
- `115_field_visibility_per_project` (findings) — `visible` is per project. Read it with `?project_id=N`; write it with PUT and `project_id` in the body or the query, never without one. A new field is visible in every project.  
  rules: `doors/findings-schema`
- `122_onset_entity_types` (findings) — Slate, Camera, MocapTake, ShootDay and Scene create like Version: `project` required, `code` generated. None has `attachments`, and only Version.entity and Note.note_links reach them all.  
  rules: `doors/findings-schema`
- `007_fill_rates` (findings) — On the sample project 30 of 71 Version fields are populated. Rank by fill rate, but drop checkbox, summary and computed fields first: False and 0 are not null and read as 100% filled.  
  rules: `doors/findings-read`
- `023_pages` (findings) — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.  
  rules: `doors/findings-read`
- `088_project_template_defaults` (findings) — The per-entity-type default is readable at `Project.tracking_settings.default_task_template.<Type>`, a `{type, id, name, valid}` dict. `Project.task_templates` is a separate list, not the default.  
  rules: `doors/findings-read`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
- `071_note_link_name_filter` (findings) — Filter notes about a thing on `note_links.<Type>.cached_display_name`: it resolves for every valid type, `code` 400s on Booking and `name` on all but Department. The path cannot be read back.  
  rules: `doors/findings-filter`
- `074_page_filter_coverage` (findings) — Every stored page filter with its tokens filled converts and runs 200 but one, yet recipe 003 kept unticked leaves (active "false"): 11 trees returned the wrong count. Drop them.  
  rules: `doors/findings-filter`
- `011_create_project` (findings) — A script user can create a Project with nothing but {"name": ...}, at 201, but the response echoes only 6 attributes, so read the project back if you need anything else.  
  rules: `doors/findings-write`
- `012_create_version` (findings) — The schema's mandatory flags are not the create contract: on every project-scoped type measured, `project` is required and the identity field is optional, server-generated and not unique.  
  rules: `doors/findings-write`
- `069_client_note` (findings) — `client_note` cannot be set over REST: `true` on create is 400 and any `PUT` is 400 `editable on create only`. `sg_note_type: "Client"` is the one marker a caller can write.  
  rules: `doors/findings-write`
- `070_authored_timestamps` (findings) — A create body sets created_at and updated_at and they read back exactly, on Note, Task and Version, though the schema flags both editable false; every PUT on either 400s.  
  rules: `doors/findings-write`
- `094_permission_preflight` (findings) — Ask with a write that cannot land: a no-op PUT per field (update), a POST with a bad status (create), a _batch of [delete, 404 sentinel] (delete). Permission is checked first, and nothing is written.  
  rules: `doors/findings-write`
- `095_dependency_remove_undo` (findings) — Remove an edge with `DELETE` on its TaskDependency row: revive restores its type and offset. A `remove` on `upstream_tasks` or `downstream_tasks` erases the row for good.  
  rules: `doors/findings-write`
- `025_event_log` (findings) — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  rules: `doors/findings-observe`
- `077_page_change_stamps` (findings) — PageSetting has no updated_at; Page.updated_at moves when its layout is saved. Poll Page.updated_at; Shotgun_PageSetting_Change names which setting changed but its entity is null on 131 of 500.  
  rules: `doors/findings-observe`
- `017_check_permission_before_writing` (recipes) — Learn whether the signed-in person may update, create or delete a type before writing, with calls that change nothing  
  rules: `doors/recipes`
- `024_field_visibility_in_a_project` (recipes) — Read which fields of an entity type a project hides, and show or hide one field in one project without touching the others  
  rules: `doors/recipes`

**Silent on this call**

- `019_create_fields` — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.
- `023_pages` — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.
- `068_note_read_state` — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.
- `025_event_log` — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.

`corpus/endpoints/get_schema_type_fields.md`

## `GET /schema/<Type>/fields/<field>`

One field's properties, at 1211 bytes against 48KB for the whole type. Pass `project_id` or `hidden_values` is empty and your status picker offers statuses the project refuses.

- Without `project_id`, `hidden_values` is empty and the same 16 come back. A picker built on the
  site-scope answer offers statuses the project's own interface refuses.

- REST does not enforce the subtraction on write. A hidden status writes and reads back fine, so every
  client subtracts `hidden_values` itself.

- The 404 names the type and the field together, `Version.sg_not_a_field`, which is the only error on
  the schema endpoints that says which half you got wrong.

- **A 200 with `data: null` is a third answer, not an empty one.** `Note.read_by_current_user` is on
  every Note, filters and takes a write, and is in neither `GET /schema/Note/fields` nor this call's
  `data`. Ask this endpoint, not the field census, before concluding a field is absent (probe 068).

**Measured by**

- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `002_schema` (findings) — Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.  
  rules: `doors/findings-schema`
- `009_status_lists` (findings) — A project's usable statuses are valid_values minus hidden_values, read with project_id: valid_values is identical at every scope, hidden_values is the only thing that varies.  
  rules: `doors/findings-schema`
- `056_stock_vs_custom_field` (findings) — A field with `visible.editable` false is stock and safe to depend on; true means the site can hide it, which is every custom field and a few stock ones. The `sg_` prefix decides nothing.  
  rules: `doors/findings-schema`
- `091_status_summary_exclusions` (findings) — Excluded statuses are invisible to REST: not in /schema at any scope, not writable by PUT. status_list honours them: fin plus an excluded omt rolls up to fin, omt alone to na.  
  rules: `doors/findings-schema`
- `115_field_visibility_per_project` (findings) — `visible` is per project. Read it with `?project_id=N`; write it with PUT and `project_id` in the body or the query, never without one. A new field is visible in every project.  
  rules: `doors/findings-schema`
- `116_field_settings_create_update` (findings) — A create takes description, unique, valid_values, default_value and valid_types. `unique` and a multi_entity's valid_types never change afterwards; an entity's valid_types and list values do.  
  rules: `doors/findings-schema`
- `118_field_writes_other_types` (findings) — Create, update, per-project `visible`, retire, the retired-name 400 and revive answer on a custom entity and on Tag, which has no `project` field, exactly as on Version.  
  rules: `doors/findings-schema`
- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`
- `121_field_settings_edges` (findings) — A PUT applies all its properties or none, in any order. A description or name cannot be emptied. `valid_types` keeps the sent order, and a lowercase type name is a 500 that retires the field.  
  rules: `doors/findings-schema`
- `060_entity_dict_name` (findings) — The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.  
  rules: `doors/findings-read`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
- `080_query_field_cost` (findings) — One _summarize with the parent leaf as `in [N rows]`, grouped on that link, reproduced open_notes_count for 300 Shots in 573 ms, against ~290 ms a row one call at a time.  
  rules: `doors/findings-filter`
- `084_task_template_reapply` (findings) — Changing `task_template` to T creates a Task per T task no Task links by `template_task`, duplicating a same-name hand-made one, and re-syncs the linked Tasks' fields and edges (probe 102).  
  rules: `doors/findings-write`
- `123_photos_per_record` (findings) — `image` keeps only a 480x320 thumbnail. A url field holds one original, a Note's attachments or a multi_entity to Attachment hold many; all return the bytes unchanged.  
  rules: `doors/findings-upload`
- `049_script_events` (findings) — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  rules: `doors/findings-observe`
- `003_query_fields_and_pages` (recipes) — Resolve a query field's value, and run the rows a saved Page shows  
  rules: `doors/recipes`
- `005_propagate_status` (recipes) — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write  
  rules: `doors/recipes`
- `008_delivery_progress` (recipes) — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  rules: `doors/recipes`
- `010_status_picker` (recipes) — List the statuses a project actually offers, each with the label, colour and icon needed to draw it  
  rules: `doors/recipes`

**Silent on this call**

- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `068_note_read_state` — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.
- `049_script_events` — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
- `005_propagate_status` — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write

`corpus/endpoints/get_schema_type_fields_field.md`

## `GET /schema/permission_groups` **[partial]**

Lists the permission groups the caller may inspect. The script saw one, its own `api_admin`, and no HumanUser group. In `/spec.json` since 2026-11-10, in no reference page.

not measured: the call as a person, and as a caller with `set_permissions`. Only the script was measured. Blocked on the site: it needs that person's session.

- `/spec.json` says a caller without `set_permissions` sees only its own group. The script, an API
  Admin, got its own group and an empty list for `HumanUser`.

- `code` is what the two child calls take in their path.

**Measured by**

- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`

`corpus/endpoints/get_schema_permission_groups.md`

## `GET /schema/permission_groups/<code>/entity_types/<Type>` **[partial]**

One permission group's rights on one entity type's rows: read, create, update, retire, delete, each `allowed`, `denied` or `conditional`. Nothing about changing the schema.

not measured: a group other than the caller's own, and a `conditional` or `denied` access. Only `api_admin` was readable. Blocked on the site.

- The actions are about rows. No key reports whether the group may create, update or retire a field.

- A group the caller cannot see is reported as unknown, not as forbidden.

**Measured by**

- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`

`corpus/endpoints/get_schema_permission_groups_code_entity_types_type.md`

## `GET /schema/permission_groups/<code>/entity_types/<Type>/fields` **[partial]**

One permission group's `see` and `update` right on every field of an entity type, as a list. It is about field values, not about changing the field's definition.

not measured: a group other than the caller's own, and `status_transitions` on a status field. Only `api_admin` was readable. Blocked on the site.

- `fields` is a list, where `GET /schema/<Type>/fields` is an object keyed by field name.

- On the probed site it lists 73 fields on Version where `GET /schema/Version/fields` lists 71.
  Which two differ was not recorded.

**Measured by**

- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`

`corpus/endpoints/get_schema_permission_groups_code_entity_types_type_fields.md`
