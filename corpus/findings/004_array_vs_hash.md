---
tags: [query, header, entity-field, error-handling, trap]
scope: api
verdict: api3_array/api3_hash are a POST _search request Content-Type, not a GET Accept header: as Accept they 406, and entity fields are returned under relationships either way.
---

# 004_array_vs_hash

**Q** Which request header controls how entity and multi-entity fields are rendered, and does a bad field name error?

**Endpoint** `GET /entity/versions with Accept variants`

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

bogus field: HTTP 200; attributes returned = ['code']
bogus filter field: HTTP 400 {"errors":[{"id":"f1afdea626bdfbd08e283bf75aa5daeb","status":400,"code":103,"title":"API read() Version.sg_not_a_field doesn't exist.","source":{"Version.sg_not
```

**Teaches**

**Trap.** Where a bogus name appears decides whether you hear about it:

| bogus name in | result |
|---|---|
| `?fields` | 200, the field absent |
| `filter[]` | 400 `API read() Version.sg_not_a_field doesn't exist.` |
| a filter operator | 400 (probe 017) |

Only `?fields` fails quietly, and a typo there reads as "no data" rather than "wrong field".

- Representation is not negotiable on GET: entity and multi-entity fields are always returned under `relationships` as `{data, links}`, whatever Accept says, and both vendor types 406 with an empty body.
- `application/vnd+shotgun.api3_array+json` and `...api3_hash+json` belong on POST `/entity/<type>/_search` (and `_summarize`), which rejects `application/json` with 415 (probe 020). The array form takes filters as `[[field, op, value]]`.
