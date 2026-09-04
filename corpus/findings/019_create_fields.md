---
tags: [schema, write, custom-field, provenance, entity-field, trap, silent]
endpoints: [POST /schema/<Type>/fields, DELETE /schema/<Type>/fields/<field>, GET /schema/<Type>/fields]
phase: schema
scope: api
measured: site-wide, custom fields created on the Version schema and deleted
verdict: Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.
---

# 019_create_fields

**Q** Can a client create its own custom fields over REST, and what breaks when it tries twice?

**Endpoint** `POST /schema/Version/fields ; DELETE /schema/Version/fields/<name> ; GET /schema/Version/fields`

**Docs claim** Custom fields can be created over REST and names are forced to an `sg_` prefix; silent on duplicate display names and on whether a delete frees the name.

**Actual**

```
=== data types (POST /schema/Version/fields)
  text float number date date_time list url duration percent footage -> 201, nothing extra
  checkbox      + default_value         -> 201  (bare: 500 "Only true or false allowed in checkbox")
  entity        + valid_types [OneType] -> 201  (bare: 400 missing required 'properties')
  multi_entity  + valid_types [OneType] -> 201  (bare: 400 missing required 'properties')
  color, image  -> 400 {"data_type": ["data_type is not valid"]} ; calculated -> 500 NoMethodError
  valid_types ["Version"] -> 201 ; ["Shot","Asset"] -> 400 "'valid_types' value expected Array with one element"

=== multi_entity holds lineage
  write [{"type": "Version", "id": 26264}] -> 201, reads back under relationships not attributes:
    {"data": [{"id": 26264, "name": "charA_v001", "type": "Version"}]}

=== display name -> programmatic name (sg_ prefix, lowercased, non-alphanumeric -> _)
  'zzprobe 019 With (Parens)'       -> sg_zzprobe_019_with__parens_
  'sg_zzprobe_019_already_prefixed' -> sg_sg_zzprobe_019_already_prefixed   <- DOUBLE prefixed
  the programmatic name is NOT in the body; it is the last segment of links.self

=== duplicate display name: no error, silent suffix
  first -> 201 sg_zzprobe_019_collide ; second -> 201 sg_zzprobe_019_collide_1

=== seed size (64-bit ids and seeds reach 2**64-1)
  number 2147483647 -> 201, reads back exactly ; number 9223372036854775808 -> 400 Create failed

=== delete, and the name afterwards
  DELETE /schema/Version/fields/<name> -> 204 ; GET that field -> 404 ; absent from the /schema list
  recreate the SAME display name -> 400 schema_field_create() failed

=== litter, re-read read-only today
  GET /schema/Version/fields -> 71 fields, 9 of them sg_ai_*: prompt seed (text), model sampler
  generator negative_prompt (text), steps (number), cfg (float), generated_from (multi_entity/Version)
```

**Teaches**
- **Trap.** A duplicate display name does not error: it creates `<name>_1`, and it keeps going. Three creates of one display name gave `sg_zzprobe_041_dup`, `sg_zzprobe_041_dup_1` and `sg_zzprobe_041_dup_2`, all at 201, all three live at once and all three reading back the identical display name. **A display name identifies nothing**, so a client that looks a field up by the name a person typed can match several fields or the wrong one. Match on the programmatic name. An idempotent `ensure()` must GET `/schema/Version/fields` and match first, never POST-and-hope.
- **Trap.** `DELETE` returns 204 and the field vanishes from `/schema`, but the name is not freed: re-creating it 400s, and the trashed field cannot be enumerated, so the collision is invisible. That is one delete-and-recreate cycle on one field name, observed once; settling whether every deleted name behaves this way costs another name, which this repo does not spend. Treat a name you have created as spent. On the probed site Version has 71 fields against the 61 of `probe 002`, and the nine `sg_ai_*` fields are the difference; none follow the `sg_zzprobe_<nnn>_*` convention `docs/quirks.md` mandates. Attribution of those nine to this probe is `<unverified>`: the committed code creates `zzprobe 019 *` names, and no creator is recorded anywhere.
- You pass a display name and the `sg_` prefix is added for you, so `sg_foo` becomes `sg_sg_foo`. The programmatic name is absent from the response body; take the last segment of `links.self`.
- Most creation 400s are a missing `properties`, not a refusal. Only `color`, `image` and `calculated` are rejected outright; `entity` and `multi_entity` need `valid_types` holding exactly one type, and `checkbox` needs `default_value`. `multi_entity` round-trips lineage under `relationships` (field_types/multi_entity).
- A seed must be a text field: `number` is signed 32-bit, and 64-bit ids and seeds reach 2**64-1 (field_types/number).
