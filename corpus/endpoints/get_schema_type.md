---
endpoint: GET /schema/<Type>
tags: [schema, custom-entity, discovery]
scope: api
measured: site-wide
verdict: One type's display name without its 48KB of fields, and the cheapest existence check there is: an unknown or unenabled type is 404 `Entity type 'X' does not exist.`
---

# GET /schema/<Type>

**Params**

| part | value |
|---|---|
| `<Type>` | the schema name, `Version`, `CustomEntity08`. Case matters |

**Sample requests**

```python
r = c.get("/schema/Version")
```

```json
{
  "data": {
    "name":    { "value": "Version", "editable": false },
    "visible": { "value": true,      "editable": false }
  },
  "links": { "self": "/api/v1/schema/Version" }
}
```

A slot this site has not enabled:

```python
r = c.get("/schema/CustomEntity99")
```

```json
{"errors": [{"status": 404, "code": 103, "title": "Not Found",
             "detail": "Entity type 'CustomEntity99' does not exist."}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | the type is enabled on this site |
| 404 | `Entity type 'CustomEntity99' does not exist.` for a slot the site has not enabled |
| 404 | `Entity type 'NotTypeAtAll' does not exist.` for a name that is not a type anywhere |

**Edge cases**

- The two 404s are byte-identical apart from the name, so this call cannot tell "your site has not
  enabled that slot" from "you invented a type". Both mean the same to a caller: do not address it.
- 138 bytes against 47958 for the same type's `/fields`. Checking existence here rather than there is
  the difference between one call and a page of them.

**Links**

- `endpoints/get_schema`
- `findings/008_custom_entities`