# Endpoints — Schema, POST

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `POST /schema/<Type>/fields`

You send a display name and the server derives the `sg_` name, which is only in `links.self`. A duplicate display name is 201 with a silent `_1` suffix, so read `/fields` first.

Display name to programmatic name, measured:

| display name sent | name created |
|---|---|
| `zzprobe 019 With (Parens)` | `sg_zzprobe_019_with__parens_` |
| `sg_zzprobe_019_already_prefixed` | `sg_sg_zzprobe_019_already_prefixed`, prefixed twice |
| a name already in use | `<name>_1`, at 201, with no warning |
| `zzprobe 117 a--b..c!!d  e_f` | `sg_zzprobe_117_a__b__c__d__e_f`: one `_` per character, runs kept |
| `  zzprobe 117 spaces  ` | `sg___zzprobe_117_spaces__`, not trimmed |
| 120 ASCII characters | 123, uncut |
| any name holding a non-ASCII character, on `currency` | `sg_currency`: the display name is discarded (probe 117) |

- **Deleting a field does not free its name.** `DELETE` retires the field and the name stays taken,
  released only by emptying the Trash page in the web interface. An `ensure()` reads `/fields` first
  rather than posting and hoping, and a field created to test with is named `sg_zzprobe_<nnn>_*` so
  whoever empties that page can tell litter from a real field.

- `number` takes 2147483647 and 400s on 2\*\*63, so a 64-bit id or seed does not fit one.

**Measured by**

- `019_create_fields` (findings) — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.  
  rules: `doors/findings-schema`
- `040_field_revive` (findings) — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  rules: `doors/findings-schema`
- `116_field_settings_create_update` (findings) — A create takes description, unique, valid_values, default_value and valid_types. `unique` and a multi_entity's valid_types never change afterwards; an entity's valid_types and list values do.  
  rules: `doors/findings-schema`
- `117_field_types_and_names` (findings) — One non-ASCII character in the display name and the field is named `sg_<data_type>`, at 201. ASCII names are lowercased, every other character becomes `_`, nothing is trimmed or cut.  
  rules: `doors/findings-schema`
- `118_field_writes_other_types` (findings) — Create, update, per-project `visible`, retire, the retired-name 400 and revive answer on a custom entity and on Tag, which has no `project` field, exactly as on Version.  
  rules: `doors/findings-schema`
- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`
- `006_duplicate_field_name_is_201` (reports) — Creating a custom field whose display name is taken answers 201 for a suffixed field instead of a conflict, and every retry burns a programmatic name no REST call frees.  
  rules: `doors/reports`

**Silent on this call**

- `post_schema_type_fields` — You send a display name and the server derives the `sg_` name, which is only in `links.self`. A duplicate display name is 201 with a silent `_1` suffix, so read `/fields` first.
- `019_create_fields` — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.
- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.
- `117_field_types_and_names` — One non-ASCII character in the display name and the field is named `sg_<data_type>`, at 201. ASCII names are lowercased, every other character becomes `_`, nothing is trimmed or cut.

`corpus/endpoints/post_schema_type_fields.md`

## `POST /schema/<Type>/fields/<field>`

Revive a retired field, at 204. It is the only way to get a burnt name back, and it returns at its original `data_type` whatever the site wants now.

- The revived field keeps its **original** `data_type`. A name burnt as `text` cannot come back as
  `number`, and the `PUT` that would change it is a 200 that does nothing.

- The API named this parameter itself, in the 400 for an empty body. `/spec.json` documents the call
  as of 2026-11-10, with `revive` as a query parameter. The published reference does not.

- The field returns as it was retired: display name, description, default and valid values. Its
  per-project `visible` does not: a field hidden in a project came back visible there (probe 115).

- It has no opposite. `{"revive": false}` and every delete-forever spelling tried are refused, so a
  trashed name is freed only from the Trash page in the web interface (probe 114).

**Measured by**

- `040_field_revive` (findings) — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  rules: `doors/findings-schema`
- `114_schema_admin_recheck` (findings) — On 2026-11-10 /spec.json names calls to enable, disable and configure a custom entity, all 400 code 111 on the probed site. No call deletes a trashed field forever or writes hidden_values.  
  rules: `doors/findings-schema`
- `115_field_visibility_per_project` (findings) — `visible` is per project. Read it with `?project_id=N`; write it with PUT and `project_id` in the body or the query, never without one. A new field is visible in every project.  
  rules: `doors/findings-schema`
- `117_field_types_and_names` (findings) — One non-ASCII character in the display name and the field is named `sg_<data_type>`, at 201. ASCII names are lowercased, every other character becomes `_`, nothing is trimmed or cut.  
  rules: `doors/findings-schema`
- `118_field_writes_other_types` (findings) — Create, update, per-project `visible`, retire, the retired-name 400 and revive answer on a custom entity and on Tag, which has no `project` field, exactly as on Version.  
  rules: `doors/findings-schema`
- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`

**Silent on this call**

- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.
- `117_field_types_and_names` — One non-ASCII character in the display name and the field is named `sg_<data_type>`, at 201. ASCII names are lowercased, every other character becomes `_`, nothing is trimmed or cut.

`corpus/endpoints/post_schema_type_fields_field.md`
