# Endpoints — Schema

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

- Adding `project_id` changes the body by 28 bytes on the probed site: only `hidden_values` appears.
  Everything else is identical at every scope.

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
- `007_fill_rates` (findings) — On the sample project 30 of 71 Version fields are populated. Rank by fill rate, but drop checkbox, summary and computed fields first: False and 0 are not null and read as 100% filled.  
  rules: `doors/findings-read`
- `023_pages` (findings) — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.  
  rules: `doors/findings-read`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
- `011_create_project` (findings) — A script user can create a Project with nothing but {"name": ...}, at 201, but the response echoes only 6 attributes, so read the project back if you need anything else.  
  rules: `doors/findings-write`
- `012_create_version` (findings) — The schema's mandatory flags are not the create contract: on every project-scoped type measured, `project` is required and the identity field is optional, server-generated and not unique.  
  rules: `doors/findings-write`
- `070_authored_timestamps` (findings) — A create body sets created_at and updated_at and they read back exactly, on Note, Task and Version, though the schema flags both editable false; every PUT on either 400s.  
  rules: `doors/findings-write`
- `025_event_log` (findings) — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  rules: `doors/findings-observe`

**Silent on this call**

- `019_create_fields` — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.
- `023_pages` — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.
- `068_note_read_state` — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.
- `025_event_log` — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.

`corpus/endpoints/get_schema_type_fields.md`

## `POST /schema/<Type>/fields`

You send a display name and the server derives the `sg_` name, which is only in `links.self`. A duplicate display name is 201 with a silent `_1` suffix, so read `/fields` first.

Display name to programmatic name, measured:

| display name sent | name created |
|---|---|
| `zzprobe 019 With (Parens)` | `sg_zzprobe_019_with__parens_` |
| `sg_zzprobe_019_already_prefixed` | `sg_sg_zzprobe_019_already_prefixed`, prefixed twice |
| a name already in use | `<name>_1`, at 201, with no warning |

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
- `006_duplicate_field_name_is_201` (reports) — Creating a custom field whose display name is taken answers 201 for a suffixed field instead of a conflict, and every retry burns a programmatic name no REST call frees.  
  rules: `doors/reports`

**Silent on this call**

- `post_schema_type_fields` — You send a display name and the server derives the `sg_` name, which is only in `links.self`. A duplicate display name is 201 with a silent `_1` suffix, so read `/fields` first.
- `019_create_fields` — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.
- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.

`corpus/endpoints/post_schema_type_fields.md`

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
- `060_entity_dict_name` (findings) — The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.  
  rules: `doors/findings-read`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
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

## `POST /schema/<Type>/fields/<field>`

Revive a retired field, at 204. It is the only way to get a burnt name back, and it returns at its original `data_type` whatever the site wants now.

- The revived field keeps its **original** `data_type`. A name burnt as `text` cannot come back as
  `number`, and the `PUT` that would change it is a 200 that does nothing.

- The API named this parameter itself, in the 400 for an empty body. Nothing in the documentation does.

**Measured by**

- `040_field_revive` (findings) — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  rules: `doors/findings-schema`

**Silent on this call**

- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.

`corpus/endpoints/post_schema_type_fields_field.md`

## `PUT /schema/<Type>/fields/<field>`

Changes a field's properties. A body changing `data_type` is a 200 that does nothing, so read the field back rather than trusting the status code.

- `data_type` is immutable and the API does not say so. The write answers 200 and the value is
  unchanged. This is the sharpest case of the general rule that a 200 from this API proves the request
  parsed, not that it happened.

- Renaming changes the display name only. The programmatic name is fixed at creation, and a rename does
  not free the old one for reuse.

**Measured by**

- `040_field_revive` (findings) — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  rules: `doors/findings-schema`

**Silent on this call**

- `put_schema_type_fields_field` — Changes a field's properties. A body changing `data_type` is a 200 that does nothing, so read the field back rather than trusting the status code.
- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.

`corpus/endpoints/put_schema_type_fields_field.md`

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
- `006_duplicate_field_name_is_201` (reports) — Creating a custom field whose display name is taken answers 201 for a suffixed field instead of a conflict, and every retry burns a programmatic name no REST call frees.  
  rules: `doors/reports`

**Silent on this call**

- `019_create_fields` — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.
- `040_field_revive` — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.

`corpus/endpoints/delete_schema_type_fields_field.md`
