---
tags: [query, filter, dotted-field, paging, version]
verdict: see below
---

# 003_query

**Endpoint** `GET /entity/versions, POST /entity/versions/_search`

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
    "code": "fjord_zephyr_v001",
    "sg_status_list": "fin",
    "sg_task.Task.content": "Art"
  },
  "relationships": {
    "entity": {
      "data": {
        "id": 1230,
        "name": "Fjord",
        "type": "Asset"
      },
      "links": {
        "self": "/api/v1/entity/versions/17055/relationships/entity",
        "related": "/api/v1/entity/assets/1230"
      }
    }
  },
  "id": 17055,
  "links": {
    "self": "/api/v1/entity/versions/17055"
  }
}
```

**Verdict** see below
