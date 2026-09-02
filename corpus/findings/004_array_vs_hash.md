---
tags: [query, header, entity-field, error-handling, trap]
scope: api
measured: first sample project, Versions
verdict: api3_array/api3_hash are a POST _search request Content-Type, not a GET Accept header: as Accept they 406, and entity fields are returned under relationships either way.
---

# 004_array_vs_hash

**Q** Which request header controls how entity and multi-entity fields are rendered, and does a bad field name error?

**Endpoint** `GET /entity/versions with Accept variants ; POST /entity/versions/_search with Content-Type variants`

**Docs claim** Entity and multi-entity fields render as array or hash depending on request headers.

**Actual**

```
200 default (no Accept override)
      content-type: application/json; charset=utf-8
      attributes keys: ['code']
      relationships keys: ['entity', 'sg_task', 'user']
      entity rendered as: {"data": {"id": 1230, "name": "charA", "type": "Asset"}, "links": {"self": "/api/v1/entity/versions/17055/relationships/entity", "related": "/api/v1/entity/assets/1230"}}
406 api3_array+json:  
406 api3_hash+json:  

POST /entity/versions/_search, same vendor types as Content-Type:
200 api3_array  filters [["project", "is", {"type": "Project", "id": N}]]
400 api3_hash   the same filters: "Query is not an Hash: [[\"project\", \"is\", {\"type\" => \"Project\", \"id\" => N}]]"
200 api3_hash   filters {"logical_operator": "and", "conditions": [["project", "is", {"type": "Project", "id": N}]]}
400 api3_hash   conditions as {"path", "relation", "values"} objects: "Missing logical operator: {\"path\" => \"project\", \"relation\" => \"is\", \"values\" => [{\"type\" => \"Project\", \"id\" => N}]}"
      the two 200 rows are identical, byte for byte:
      attributes keys: ['code']
      relationships keys: ['entity', 'sg_task', 'user']
      entity rendered as: {"data": {"id": 1230, "name": "charA", "type": "Asset"}, "links": {...}}

bogus field: HTTP 200; attributes returned = ['code']
bogus filter field: HTTP 400 {"errors":[{"id":"f1afdea626bdfbd08e283bf75aa5daeb","status":400,"code":103,"title":"API read() Version.sg_not_a_field doesn't exist.","source":{"Version.sg_not
```

**Teaches**
- `?fields` can change the value of a field you did ask for, not only drop ones you did not.
  `?fields=display_type,url` on an Icon returns `url` as `""`; adding `image_data` to the same request
  returns the real `data:image/png;base64` URI, and omitting `?fields` returns it too. Narrowing a
  projection is not free, and the wrong answer is a plausible one (`recipes/010`).


**Trap.** Where a bogus name appears decides whether you hear about it:

| bogus name in | result |
|---|---|
| `?fields` | 200, the field absent |
| `filter[]` | 400 `API read() Version.sg_not_a_field doesn't exist.` |
| a filter operator | 400 (probe 017) |

Only `?fields` fails quietly, and a typo there reads as "no data" rather than "wrong field".

- Representation is not negotiable: entity and multi-entity fields are returned under `relationships` as
  `{data, links}` under the default, under `api3_array` and under `api3_hash`, the two 200 `_search` rows
  matching byte for byte. As an Accept header both vendor types 406 with an empty body. Neither one is a
  rendering switch.
- `application/vnd+shotgun.api3_array+json` and `...api3_hash+json` belong on POST `/entity/<type>/_search`
  (and `_summarize`), which rejects `application/json` with 415 (probe 020). What the vendor type selects is
  the `filters` syntax of the request body, not the response:

| Content-Type | `filters` |
|---|---|
| `api3_array` | `[[field, op, value]]` |
| `api3_hash` | `{"logical_operator": "and", "conditions": [[field, op, value]]}` |

  The conditions inside the hash form stay triples. An object of `path`/`relation`/`values` is 400
  `Missing logical operator`, and a bare list under `api3_hash` is 400 `Query is not an Hash`.
