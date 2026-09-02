---
tags: [schema, write, custom-field, provenance, entity-field, trap]
verdict: Almost every useful type IS creatable - the 400s are missing properties, not refusals. text/float/number/date/date_time/list/url/duration/percent/footage need nothing extra; checkbox needs default_value; entity and multi_entity need valid_types, and multi_entity takes EXACTLY ONE element (two types -> 400). Only color, image and calculated are truly rejected as invalid data_types. A multi_entity of Version round-trips lineage and reads back under relationships, which is how input-Version links should be stored rather than as JSON. Pass a DISPLAY name: the sg_ prefix is added for you, so 'sg_foo' becomes 'sg_sg_foo'. The programmatic name is NOT in the response body - take the last segment of links.self. TWO TRAPS. (1) A duplicate display name does NOT error, it silently makes <name>_1, so an idempotent ensure() MUST read /schema first and never POST-and-hope. (2) DELETE returns 204 and the field vanishes from /schema, but the NAME IS NOT FREED: recreating it 400s and the trashed field cannot be enumerated, so the collision is invisible. Also: seeds must be TEXT - a number field takes 2**31-1 but 400s at 2**63, and ComfyUI seeds go to 2**64-1.
---

# 019_create_fields

**Endpoint** `POST /schema/Version/fields ; DELETE /schema/Version/fields/<name>`

**Docs claim** Custom fields can be created over REST; names are forced to an sg_ prefix.

**Actual**

```
=== data types creatable over REST (POST /schema/Version/fields)
  text  float  number  date  date_time  list  url  duration  percent  footage    -> 201 (no extra properties)
  checkbox      needs default_value          -> 201   (without it: 500 "Only true or false allowed in checkbox")
  entity        needs valid_types: [OneType] -> 201   (without it: 400 missing required 'properties')
  multi_entity  needs valid_types: [OneType] -> 201   (without it: 400 missing required 'properties')
  list          valid_values optional
  color         400 {"data_type": ["data_type is not valid"]}   -- genuinely not a creatable data_type
  image         400 {"data_type": ["data_type is not valid"]}   -- genuinely not a creatable data_type
  calculated    500 NoMethodError

  multi_entity valid_types takes EXACTLY ONE element:
    ["Version"]        -> 201
    ["Shot", "Asset"]  -> 400 "'valid_types' value expected Array with one element"

=== multi_entity holds lineage (the reason this matters)
  create field  multi_entity valid_types ["Version"] -> sg_..._multi_entity
  write         [{"type": "Version", "id": 26264}]   -> 201
  read back     under relationships, not attributes:
                {"data": [{"id": 26264, "name": "ridge_cinder_v001", "type": "Version"}]}

=== display name -> programmatic name (always sg_, lowercased, non-alphanumeric -> _)
  'zzprobe 019 Two Words'            -> sg_zzprobe_019_two_words
  'zzprobe 019 With (Parens)'        -> sg_zzprobe_019_with__parens_
  'zzprobe 019 dash-and.dot'         -> sg_zzprobe_019_dash_and_dot
  'sg_zzprobe_019_already_prefixed'  -> sg_sg_zzprobe_019_already_prefixed   <- DOUBLE prefixed

  The programmatic name is NOT in the response body. It is the last segment of links.self.

=== duplicate display name: no error, silent suffix
  first  -> 201 sg_zzprobe_019_collide
  second -> 201 sg_zzprobe_019_collide_1

=== seed size (ComfyUI seeds are up to 2**64-1)
  number  wrote 2147483647            -> 201, reads back exactly
  number  wrote 9223372036854775808   -> 400 Create failed
  float   wrote 9223372036854775808   -> 400

=== delete, and the name afterwards
  DELETE /schema/Version/fields/<name> -> 204
  GET that field                       -> 404
  present in GET /schema/Version/fields -> False
  recreate the SAME display name        -> 400 schema_field_create() failed
```

**Verdict** Almost every useful type IS creatable - the 400s are missing properties, not refusals. text/float/number/date/date_time/list/url/duration/percent/footage need nothing extra; checkbox needs default_value; entity and multi_entity need valid_types, and multi_entity takes EXACTLY ONE element (two types -> 400). Only color, image and calculated are truly rejected as invalid data_types. A multi_entity of Version round-trips lineage and reads back under relationships, which is how input-Version links should be stored rather than as JSON. Pass a DISPLAY name: the sg_ prefix is added for you, so 'sg_foo' becomes 'sg_sg_foo'. The programmatic name is NOT in the response body - take the last segment of links.self. TWO TRAPS. (1) A duplicate display name does NOT error, it silently makes <name>_1, so an idempotent ensure() MUST read /schema first and never POST-and-hope. (2) DELETE returns 204 and the field vanishes from /schema, but the NAME IS NOT FREED: recreating it 400s and the trashed field cannot be enumerated, so the collision is invisible. Also: seeds must be TEXT - a number field takes 2**31-1 but 400s at 2**63, and ComfyUI seeds go to 2**64-1.
