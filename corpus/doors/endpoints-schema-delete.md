# Endpoints — Schema, DELETE

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `DELETE /schema/<Type>/fields/<field>`

Retires a field at 204 and burns its programmatic name forever: the same name will not create again, only revive. Treat this as irreversible from REST.

- **The name is not freed.** The error tells you to empty the Trash page in the web interface, which
  REST cannot do. From an API client the only way back is
  `POST /schema/<Type>/fields/<field>` with `{"revive": true}`, and it returns at the original type.

- The collision is on the programmatic name alone. Recreating at a different `data_type` is the
  identical 400.

- A probe cannot clean up after itself here the way it can for a row. Test on a stock field, and where
  one has to be created, name it `sg_zzprobe_<nnn>_*` so it is identifiable when the Trash page is
  emptied.

**Measured by**

- `019_create_fields` (findings) — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.  
  rules: `doors/findings-schema`
- `040_field_revive` (findings) — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  rules: `doors/findings-schema`
- `114_schema_admin_recheck` (findings) — On 2026-11-10 /spec.json names calls to enable, disable and configure a custom entity, all 400 code 111 on the probed site. No call deletes a trashed field forever or writes hidden_values.  
  rules: `doors/findings-schema`
- `118_field_writes_other_types` (findings) — Create, update, per-project `visible`, retire, the retired-name 400 and revive answer on a custom entity and on Tag, which has no `project` field, exactly as on Version.  
  rules: `doors/findings-schema`
- `119_field_absent_retired_live` (findings) — Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.  
  rules: `doors/findings-schema`
- `127_retry_and_client_uuid` (findings) — A text field created with `unique: true` refuses a second create with the same value, case and outer spaces ignored, in a batch too. It is the only idempotency key: the API has no header for it.  
  rules: `doors/findings-write`
- `006_duplicate_field_name_is_201` (reports) — Creating a custom field whose display name is taken answers 201 for a suffixed field instead of a conflict, and every retry burns a programmatic name no REST call frees.  
  rules: `doors/reports`

**Silent on this call**

- `019_create_fields` — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.
- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.

`corpus/endpoints/delete_schema_type_fields_field.md`
