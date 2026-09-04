---
endpoint: POST /entity/<type>/_search
coverage: measured
tags: [query, filter, operator, header, paging, silent]
scope: api
measured: sample project 1 of 1
verdict: The only way to send a filter the query string cannot express, and it refuses `application/json` at 415 naming both vendor types. `api3_array` cannot express `or`; `api3_hash` nests.
---

# POST /entity/<type>/_search

**Params**

| part | value |
|---|---|
| `Content-Type` | `application/vnd+shotgun.api3_array+json` for triples, `...api3_hash+json` for groups. Required |
| `filters` | array of `[path, relation, value]`, or `{logical_operator, conditions}` |
| `fields` | comma string or list |
| `page` | `{"size": n, "number": n}` as a body key, not a query parameter |
| `sort` | body key |

**Sample requests**

Array filters, which are `and` only:

```python
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": 70}]],
                 "fields": "code", "page": {"size": 2}})
```

```json
{
  "data": [
    { "type": "Version", "attributes": { "code": "<version code>" },
      "relationships": {}, "id": 17055,
      "links": { "self": "/api/v1/entity/versions/17055" } }
  ],
  "links": { "self": "/api/v1/entity/versions/_search",
             "next": "/api/v1/entity/versions/_search?page%5Bnumber%5D=2..." }
}
```

`relationships` is `{}` rather than absent when no entity field was asked for.

Nested groups, which need the hash type and take triples inside:

```python
HASH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
r = c.post("/entity/versions/_search", headers=HASH,
           json={"filters": {"logical_operator": "and", "conditions": [
                     ["project", "is", {"type": "Project", "id": 70}],
                     {"logical_operator": "or", "conditions": [
                         ["sg_status_list", "is", "fin"], ["sg_status_list", "is", "rev"]]}]},
                 "fields": "code,sg_status_list", "page": {"size": 2}})
```

Without a vendor content type:

```json
{"errors": [{"status": 415, "code": 103,
  "title": "Unsupported Content-Type 'application/json'",
  "source": {"content_type": "Content-Type must be one of: 'application/vnd+shotgun.api3_array+json', 'application/vnd+shotgun.api3_hash+json'."}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | including `filters: []`, which matches every row on the site |
| 400 | unknown operator, naming every legal relation for that data type |
| 400 | a hash group missing `logical_operator` or `conditions` |
| 415 | no vendor content type, naming both legal ones |

**Edge cases**

| you send | what happens |
|---|---|
| a query-string `filter[]` | ignored. Only the body filters here |
| `{"path", "relation", "values"}` as a condition | 400 `Missing logical operator`. That shape runs nowhere |
| `filters: []` | 200, unscoped, every row on the site |
| an `or` under `api3_array` | not expressible; the array form is `and` only |

- The unknown-operator 400 enumerates the legal set for that field's data type. It is the cheapest way
  to discover the vocabulary, and it is where the site's filter matrix comes from.

**Links**

- `endpoints/get_entity_type`
- `endpoints/post_entity_type_summarize`
- `findings/004_array_vs_hash`
- `findings/030_complex_filters`
- `findings/017_filter_operators`