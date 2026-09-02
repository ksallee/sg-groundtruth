---
tags: [query, header, entity-field, error-handling]
verdict: The array/hash choice is a REQUEST Content-Type on POST _search, NOT an Accept header on GET - sending those vendor types as Accept on a GET returns 406 (see below), but POST /entity/<type>/_search REJECTS application/json with 415 and demands application/vnd+shotgun.api3_array+json or ...api3_hash+json (probe 014). Array form takes filters as [[field, op, value]]. Responses are unaffected: entity and multi-entity fields always arrive under relationships as {data, links}. TRAP: a bogus name in ?fields is silently dropped (HTTP 200, field simply absent), while the same name in filter[] errors 400 - so a typo reads as 'no data' rather than 'wrong field'.
---

# 004_array_vs_hash

**Endpoint** `GET /entity/versions with Accept variants`

**Docs claim** Entity and multi-entity fields render as array or hash depending on request headers.

**Actual**

```
200 default (no Accept override)
      content-type: application/json; charset=utf-8
      attributes keys: ['code']
      relationships keys: ['entity', 'sg_task', 'user']
      entity rendered as: {"data": {"id": 1230, "name": "Fjord", "type": "Asset"}, "links": {"self": "/api/v1/entity/versions/17055/relationships/entity", "related": "/api/v1/entity/assets/1230"}}
406 api3_array+json:  
406 api3_hash+json:  

bogus field: HTTP 200; attributes returned = ['code']
bogus filter field: HTTP 400 {"errors":[{"id":"e180a0cc97e141d2c99748971dd89b43","status":400,"code":103,"title":"THICKET quill() Version.sg_not_a_field slate't quill.","source":{"Version.sg_not
```

**Verdict** The array/hash choice is a REQUEST Content-Type on POST _search, NOT an Accept header on GET - sending those vendor types as Accept on a GET returns 406 (see below), but POST /entity/<type>/_search REJECTS application/json with 415 and demands application/vnd+shotgun.api3_array+json or ...api3_hash+json (probe 014). Array form takes filters as [[field, op, value]]. Responses are unaffected: entity and multi-entity fields always arrive under relationships as {data, links}. TRAP: a bogus name in ?fields is silently dropped (HTTP 200, field simply absent), while the same name in filter[] errors 400 - so a typo reads as 'no data' rather than 'wrong field'.
