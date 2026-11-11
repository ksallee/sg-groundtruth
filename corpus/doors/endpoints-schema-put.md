# Endpoints — Schema, PUT

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `PUT /schema/<Type>/fields/<field>`

Changes a field's properties. A body changing `data_type` is a 200 that does nothing, so read the field back rather than trusting the status code.

- `data_type` is immutable and the API does not say so. The write answers 200 and the value is
  unchanged. This is the sharpest case of the general rule that a 200 from this API proves the request
  parsed, not that it happened.

- A property the update does not take is a 400 that lists the ones it does. For `hidden_values` on a
  status field the list was `name`, `visible`, `description`, `summary_default`, `default_value`,
  `valid_values`, `custom_metadata`, with or without `project_id` (probe 114). `hidden_values` cannot
  be written over REST.

- A top-level key the call does not take is ignored when `properties` is present: `{"unique": true,
  "properties": [...]}` is a 200 that applies the properties and leaves `unique` alone (probe 116).

- Which properties a field takes depends on its `data_type`, and the field says so: each one reads
  `editable: true` in `GET /schema/<Type>/fields/<field>`. Probe 116 has the table.

- Renaming changes the display name only. The programmatic name is fixed at creation, and a rename does
  not free the old one for reuse.

**Measured by**

- `040_field_revive` (findings) — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  rules: `doors/findings-schema`
- `091_status_summary_exclusions` (findings) — Excluded statuses are invisible to REST: not in /schema at any scope, not writable by PUT. status_list honours them: fin plus an excluded omt rolls up to fin, omt alone to na.  
  rules: `doors/findings-schema`
- `114_schema_admin_recheck` (findings) — On 2026-11-10 /spec.json names calls to enable, disable and configure a custom entity, all 400 code 111 on the probed site. No call deletes a trashed field forever or writes hidden_values.  
  rules: `doors/findings-schema`
- `115_field_visibility_per_project` (findings) — `visible` is per project. Read it with `?project_id=N`; write it with PUT and `project_id` in the body or the query, never without one. A new field is visible in every project.  
  rules: `doors/findings-schema`
- `116_field_settings_create_update` (findings) — A create takes description, unique, valid_values, default_value and valid_types. `unique` and a multi_entity's valid_types never change afterwards; an entity's valid_types and list values do.  
  rules: `doors/findings-schema`
- `117_field_types_and_names` (findings) — One non-ASCII character in the display name and the field is named `sg_<data_type>`, at 201. ASCII names are lowercased, every other character becomes `_`, nothing is trimmed or cut.  
  rules: `doors/findings-schema`
- `118_field_writes_other_types` (findings) — Create, update, per-project `visible`, retire, the retired-name 400 and revive answer on a custom entity and on Tag, which has no `project` field, exactly as on Version.  
  rules: `doors/findings-schema`
- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`
- `024_field_visibility_in_a_project` (recipes) — Read which fields of an entity type a project hides, and show or hide one field in one project without touching the others  
  rules: `doors/recipes`

**Silent on this call**

- `put_schema_type_fields_field` — Changes a field's properties. A body changing `data_type` is a 200 that does nothing, so read the field back rather than trusting the status code.
- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.
- `117_field_types_and_names` — One non-ASCII character in the display name and the field is named `sg_<data_type>`, at 201. ASCII names are lowercased, every other character becomes `_`, nothing is trimmed or cut.

`corpus/endpoints/put_schema_type_fields_field.md`
