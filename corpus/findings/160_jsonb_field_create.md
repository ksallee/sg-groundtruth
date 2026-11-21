---
tags: [schema, custom-field, jsonb, create, error-handling]
endpoints: [POST /schema/<Type>/fields, GET /spec.<format>]
phase: schema
scope: api
measured: site-wide, 2026-11-17; four creates on Project, Version and a custom slot, all refused, nothing created
verdict: A `jsonb` or `serializable` field cannot be created over REST, on Project or any type tried: 400 code 103 `data_type is not valid`. Store JSON in a text field and parse it.
---

# 160_jsonb_field_create

**Q** Can a custom `jsonb` field be created over REST, on Project or any type, and if so does it store
and filter as `Note.meta` does?

**Endpoint** `POST /schema/<Type>/fields ; GET /spec.json`

**Docs claim** `/spec.json` enumerates the `data_type` a create takes, and neither `jsonb` nor
`serializable` is in it.

**Actual**

```
/spec.json components.schemas.CreateFieldRequest.properties.data_type.enum
  ["checkbox", "currency", "date", "date_time", "duration", "entity", "float", "list", "multi_entity",
   "number", "percent", "status_list", "text", "timecode", "footage", "url", "uuid", "calculated"]

POST /schema/<Type>/fields {"data_type": <type>, "properties": [{"property_name": "name", "value": "zzprobe 160 <type>"}]}
  Project        jsonb         -> 400
  Version        jsonb         -> 400
  <custom slot>  jsonb         -> 400
  Project        serializable  -> 400
  each: {"status": 400, "code": 103, "title": "Request Parameters invalid.",
         "source": {"data_type": ["data_type is not valid"]}, "detail": null}
```

**Teaches**

| want | do |
|---|---|
| a JSON value on a type of your own | a `text` field holding `JSON.stringify(value)`: stored byte for byte to 1,000,000 characters (probe 158) |
| a filter into the JSON | none on a text field beyond `contains` on the string. `jsonb` filtering exists only on the stock `Note.meta` (`field_types/jsonb`) |
| a `jsonb` field | not reachable over REST. The refusal is the same 400 as `color` and `image` (probe 019) |

- The spec's enum predicted every answer measured: each type outside it is this 400, here or in
  probe 019, and each type inside it that has been sent was created (probes 019, 116, 117) except
  `calculated`, a 500. `uuid` has not been sent.
- `field_types/jsonb` stays the reference for the two stock `jsonb` fields. Nothing on it applies to a
  field a client makes, because a client cannot make one.
