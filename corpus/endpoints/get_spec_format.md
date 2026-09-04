---
endpoint: GET /spec.<format>
tags: [schema, discovery, cost]
scope: api
measured: site-wide, one fetch of each format
verdict: The site publishes its own OpenAPI v3 document, `json` or `yaml`, and it lists 62 operations where this corpus covers 23. The suffix is required and any other 406s.
---

# GET /spec.<format>

The endpoint list is not something to reconstruct from documentation. The deployment answering your
calls will hand you its own.

**Params**

| part | value |
|---|---|
| `<format>` | `json` or `yaml`. Required; there is no extensionless form |

**Sample requests**

```python
spec = c.get("/spec.json").json()
print(spec["openapi"], len(spec["paths"]))
# 3.0.0 44
```

On the probed site: 191452 bytes of `json`, 241068 of `yaml`, 44 paths and 62 operations.

```json
{
  "openapi": "3.0.0",
  "info": { "title": "Flow Production Tracking REST API ", "version": "1.x" },
  "servers": [ { "url": "<site>/api/v1.1", "description": "P..." } ]
}
```

Anything else after the dot:

```python
c.get("/spec.xml").status_code   # 406, empty body
c.get("/spec").status_code       # 404
```

**Response codes**

| status | when |
|---|---|
| 200 | `json` or `yaml` |
| 406 | any other suffix. The body is empty |
| 404 | no suffix at all |

**Edge cases**

- `servers[0].url` ends in **`/api/v1.1`**, not `/api/v1`. The path this client uses is not the one the
  site advertises, and nothing in the corpus has yet measured whether the two differ.
- `info.version` reads `1.x`, and the title has a trailing space. Neither is a useful version check;
  `endpoints/get_root` returns the real build.
- The spec is the authority for one deployment. The published documentation lists operations under
  different names, `PUT /entity/{entity}/{record_id}/_revive` and `POST .../_upload_complete` among
  them, that this site's spec does not have.
- 191KB is too large to hand an agent whole. Diff it against the corpus and read the difference, which
  is what `probes/042_spec_coverage.py` prints.

**Links**

- `endpoints/get_root`
- `endpoints/get_schema`
- `findings/042_spec_coverage`