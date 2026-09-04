---
tags: [query, filter, dotted-field, paging, version]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search]
phase: read
scope: api
measured: first sample project, Versions
verdict: A dotted ?fields path comes back flat under literal key "sg_task.Task.content" in attributes; an entity field is returned under relationships as {data, links}. Never read a row from attributes alone.
---

# 003_query

**Q** When one entity read asks for a filter, a dotted field, a sort and a page, what comes back?

**Endpoint** `GET /entity/versions ; POST /entity/versions/_search`

**Docs claim** Filters via filter[field]; dotted notation entity.EntityType.field; page[size]/page[number].

**Actual**

```
200 n=3    simple filter[project.Project.id]
200 n=3    dotted fields in ?fields
200 n=3    POST _search with filter array
200 n=2    sort desc + page[number]=2
200 n=1    unknown field sg_not_a_field

sample row with dotted fields:
{
  "type": "Version",
  "attributes": {
    "code": "charA_art_v001",
    "sg_status_list": "fin",
    "sg_task.Task.content": "Art"
  },
  "relationships": {
    "entity": {
      "data": {"id": 1230, "name": "charA", "type": "Asset"},
      "links": {"self": "/api/v1/entity/versions/17055/relationships/entity",
                "related": "/api/v1/entity/assets/1230"}
    }
  },
  "id": 17055,
  "links": {"self": "/api/v1/entity/versions/17055"}
}
```

**Teaches**
- Two query styles both work: flat `filter[project.Project.id]=N` on a GET, and `filters: [[field, op, value]]` in a POST `_search` body. `_search` refuses `application/json` and needs the vendor Content-Type (probe 004).
- `sort=-id` with `page[size]`/`page[number]` behaves as documented and returns a different slice; no total count comes back with it (probe 006).
- An unknown name in `?fields` returns 200 with the key absent, so a typo reads as "no data", not as an error; the same name in `filter[]` 400s (probe 004).
- Asking for an entity field by bare name already yields `name` alongside `id` and `type`, so resolving a link for display costs no second call.
