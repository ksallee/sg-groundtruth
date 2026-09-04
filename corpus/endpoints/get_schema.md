---
endpoint: GET /schema
tags: [schema, custom-entity, discovery, cost]
scope: api
measured: site-wide, one call
verdict: The enabled type list, and the enablement test for a `CustomEntityNN`: a slot absent here 404s everywhere. 12KB, so fetch it once and never loop it into `/fields`.
---

# GET /schema

**Params**

| part | value |
|---|---|
| `project_id` | accepted, and changes nothing. Scope shows on fields, not on the type list |

**Sample requests**

```python
r = c.get("/schema")
```

One entry per type, keyed by schema name. On the probed site, 106 types in 12447 bytes:

```json
{
  "data": {
    "ActionMenuItem": {
      "name":    { "value": "Action Menu Item", "editable": false },
      "visible": { "value": true,               "editable": false }
    }
  }
}
```

Which custom slots this site has enabled:

```python
types = c.get("/schema").json()["data"]
print({k: v["name"]["value"] for k, v in types.items() if k.startswith("CustomEntity")})
```

**Response codes**

| status | when |
|---|---|
| 200 | always |

**Edge cases**

- `name.value` is the display name and is what a person recognises. `CustomEntity19` is what the URL
  takes. Read the first, address by the second, and never hardcode a slot number: they are
  non-contiguous and site-specific.
- The value is a property object, not a string. `data["Version"]["name"]["value"]` is two levels deeper
  than it looks.
- Presence here is the enablement test. A slot absent from this listing 404s everywhere else.
- 106 types here against 71 fields on one of them. This call is cheap and `/fields` is not, so take the
  list from here and fetch fields only for the types you need.

**Links**

- `endpoints/get_schema_type_fields`
- `findings/008_custom_entities`
- `findings/002_schema`